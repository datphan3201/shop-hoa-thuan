from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

MAINTENANCE_MESSAGE = "Shop Hoà Thuận đang được bảo trì. Vui lòng thử lại sau."
logger = logging.getLogger("shop.service")


class OperationBusyError(RuntimeError):
    pass


class MaintenanceTimeoutError(RuntimeError):
    pass


def _paths() -> tuple[Path, Path, Path]:
    config = Path(settings.RUNTIME_PATHS.config)
    writes = config / "active-writes"
    return config / "server.lock", config / "maintenance.json", writes


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _read_owner(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass
class FileLease:
    path: Path
    operation: str
    operation_id: str
    acquired: bool = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "pid": os.getpid(),
                "operation": self.operation,
                "operation_id": self.operation_id,
                "started_at": time.time(),
            },
            ensure_ascii=False,
        )
        for _ in range(2):
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                owner = _read_owner(self.path)
                if _alive(_pid(owner.get("pid", 0))):
                    raise OperationBusyError(
                        f"{self.operation} đang được một process khác thực hiện."
                    ) from None
                stale = self.path.with_name(f"{self.path.name}.stale-{uuid.uuid4().hex}")
                try:
                    self.path.replace(stale)
                except FileNotFoundError:
                    continue
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
            self.acquired = True
            logger.info("Đã lấy lock operation=%s id=%s", self.operation, self.operation_id)
            return
        raise OperationBusyError(f"Không thể lấy khóa {self.operation}.")

    def release(self) -> None:
        if not self.acquired:
            return
        owner = _read_owner(self.path)
        if (
            owner.get("operation_id") == self.operation_id
            and _pid(owner.get("pid", 0)) == os.getpid()
        ):
            self.path.unlink(missing_ok=True)
        self.acquired = False
        logger.info("Đã giải phóng lock operation=%s id=%s", self.operation, self.operation_id)


def server_lease() -> FileLease:
    server_lock, _, _ = _paths()
    return FileLease(server_lock, "server", uuid.uuid4().hex)


def maintenance_state() -> dict[str, object] | None:
    _, state_path, _ = _paths()
    state = _read_owner(state_path)
    if not state:
        return None
    if _alive(_pid(state.get("pid", 0))):
        return {
            key: state[key] for key in ("operation", "operation_id", "started_at") if key in state
        }
    state_path.unlink(missing_ok=True)
    return None


@dataclass
class ActiveWrite:
    path: Path
    operation_id: str

    def close(self) -> None:
        self.path.unlink(missing_ok=True)


def begin_write(operation: str) -> ActiveWrite:
    _, state_path, writes = _paths()
    if maintenance_state() is not None:
        raise OperationBusyError(MAINTENANCE_MESSAGE)
    writes.mkdir(parents=True, exist_ok=True)
    operation_id = uuid.uuid4().hex
    marker = writes / f"{operation_id}.json"
    marker.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "operation": operation,
                "operation_id": operation_id,
                "started_at": time.time(),
            }
        ),
        encoding="utf-8",
    )
    if state_path.exists():
        marker.unlink(missing_ok=True)
        raise OperationBusyError(MAINTENANCE_MESSAGE)
    return ActiveWrite(marker, operation_id)


def _active_writes() -> list[Path]:
    _, _, writes = _paths()
    if not writes.exists():
        return []
    active: list[Path] = []
    for marker in writes.glob("*.json"):
        if _alive(_pid(_read_owner(marker).get("pid", 0))):
            active.append(marker)
        else:
            marker.unlink(missing_ok=True)
    return active


@contextmanager
def maintenance_operation(operation: str, *, timeout_seconds: float = 20.0) -> Iterator[str]:
    _, state_path, _ = _paths()
    lease = FileLease(state_path, operation, uuid.uuid4().hex)
    lease.acquire()
    deadline = time.monotonic() + timeout_seconds
    try:
        while _active_writes():
            if time.monotonic() >= deadline:
                raise MaintenanceTimeoutError("Hết thời gian chờ các thao tác ghi hoàn tất.")
            time.sleep(0.05)
        yield lease.operation_id
    finally:
        lease.release()

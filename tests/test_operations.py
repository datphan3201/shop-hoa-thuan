from __future__ import annotations

import json
import os
from contextlib import AbstractContextManager
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.test import Client, override_settings

from apps.core.operations import (
    MAINTENANCE_MESSAGE,
    FileLease,
    OperationBusyError,
    begin_write,
    maintenance_operation,
    maintenance_state,
)
from shop_hoa_thuan.runtime import RuntimePaths


def _hold_lease(path: str, ready: Any, release: Any, result: Any) -> None:
    lease = FileLease(Path(path), "server", "child")
    try:
        lease.acquire()
        result.put(True)
        ready.set()
        release.wait(3)
    except OperationBusyError:
        result.put(False)
    finally:
        lease.release()


@pytest.fixture
def runtime_settings(tmp_path: Path) -> AbstractContextManager[object]:
    return override_settings(RUNTIME_PATHS=RuntimePaths(tmp_path))


def test_second_instance_is_rejected_and_release_allows_next_instance(
    runtime_settings: AbstractContextManager[object],
) -> None:
    with runtime_settings:
        first = FileLease(Path(settings.RUNTIME_PATHS.config) / "server.lock", "server", "first")
        first.acquire()
        second = FileLease(first.path, "server", "second")
        with pytest.raises(OperationBusyError):
            second.acquire()
        first.release()
        second.acquire()
        second.release()


def test_stale_lock_is_replaced_but_live_owner_lock_is_preserved(
    runtime_settings: AbstractContextManager[object],
) -> None:
    with runtime_settings:
        path = Path(settings.RUNTIME_PATHS.config) / "server.lock"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"pid": 999_999_999, "operation_id": "old"}), encoding="utf-8")
        lease = FileLease(path, "server", "new")
        lease.acquire()
        assert json.loads(path.read_text(encoding="utf-8"))["operation_id"] == "new"
        lease.release()
        path.write_text(json.dumps({"pid": os.getpid(), "operation_id": "live"}), encoding="utf-8")
        with pytest.raises(OperationBusyError):
            FileLease(path, "server", "other").acquire()


def test_two_real_processes_cannot_hold_same_single_instance_lease(tmp_path: Path) -> None:
    path = tmp_path / "config" / "server.lock"
    ready, release, result = Event(), Event(), Queue()  # type: ignore[var-annotated]
    first = Process(target=_hold_lease, args=(str(path), ready, release, result))
    first.start()
    assert ready.wait(3)
    second = Process(target=_hold_lease, args=(str(path), Event(), Event(), result))
    second.start()
    second.join(3)
    release.set()
    first.join(3)
    assert sorted([result.get(timeout=1), result.get(timeout=1)]) == [False, True]


@pytest.mark.django_db
def test_maintenance_blocks_new_writes_but_allows_reads(
    runtime_settings: AbstractContextManager[object], client: Client
) -> None:
    with runtime_settings, maintenance_operation("backup"):
        response = client.post("/login/", {"username": "x", "password": "x"})
        health = client.get("/health/")
    assert response.status_code == 503
    assert response.content.decode() == MAINTENANCE_MESSAGE
    assert health.status_code == 503
    assert health.json()["status"] == "maintenance"
    assert maintenance_state() is None


def test_maintenance_waits_for_write_then_releases(
    runtime_settings: AbstractContextManager[object],
) -> None:
    with runtime_settings:
        active = begin_write("sale")
        with pytest.raises(Exception, match="Hết thời gian"):
            with maintenance_operation("backup", timeout_seconds=0):
                pass
        active.close()
        with maintenance_operation("backup") as operation_id:
            assert operation_id
        assert maintenance_state() is None

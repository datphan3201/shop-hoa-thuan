from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import secrets
import shutil
import socket
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def database(self) -> Path:
        return self.data / "db.sqlite3"

    @property
    def media(self) -> Path:
        return self.data / "media"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def rollback(self) -> Path:
        return self.root / "rollback"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def secret(self) -> Path:
        return self.config / "django-secret-key"


def runtime_paths() -> RuntimePaths:
    configured = os.getenv("SHOP_DATA_DIR")
    if configured:
        root = Path(configured).expanduser().resolve()
    elif os.name == "nt" and os.getenv("PROGRAMDATA"):
        root = Path(os.environ["PROGRAMDATA"]) / "Shop Hoa Thuan"
    else:
        root = Path(__file__).resolve().parent.parent / ".data"
    return RuntimePaths(root=root)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sqlite_integrity_ok(path: Path) -> bool:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as database:
        row = database.execute("PRAGMA integrity_check").fetchone()
    return bool(row and row[0] == "ok")


def migrate_legacy_layout(paths: RuntimePaths | None = None) -> bool:
    """Copy the pre-Phase-7 layout once, retaining the source as a safe fallback."""
    paths = paths or runtime_paths()
    legacy_database = paths.root / "shop-hoa-thuan.sqlite3"
    if not legacy_database.exists() or paths.database.exists():
        return False
    paths.data.mkdir(parents=True, exist_ok=True)
    if not _sqlite_integrity_ok(legacy_database):
        raise RuntimeError("Database cũ không vượt qua kiểm tra toàn vẹn.")
    shutil.copy2(legacy_database, paths.database)
    if _sha256(legacy_database) != _sha256(paths.database) or not _sqlite_integrity_ok(
        paths.database
    ):
        paths.database.unlink(missing_ok=True)
        raise RuntimeError("Không thể sao chép database cũ an toàn.")
    legacy_media = paths.root / "media"
    if legacy_media.exists() and not paths.media.exists():
        shutil.copytree(legacy_media, paths.media)
    legacy_secret = paths.root / ".secret-key"
    if legacy_secret.exists() and not paths.secret.exists():
        paths.config.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_secret, paths.secret)
    return True


def ensure_runtime_layout(*, migrate_legacy: bool = False) -> RuntimePaths:
    paths = runtime_paths()
    for directory in (
        paths.data,
        paths.media,
        paths.backups,
        paths.rollback,
        paths.logs,
        paths.config,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if migrate_legacy:
        migrate_legacy_layout(paths)
    return paths


def ensure_runtime_secret() -> str:
    """Load or atomically create the machine-local Django secret."""
    paths = ensure_runtime_layout()
    try:
        return paths.secret.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        secret = secrets.token_urlsafe(64)
        try:
            descriptor = os.open(paths.secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return paths.secret.read_text(encoding="utf-8").strip()
        with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(secret)
        return secret


def production_allowed_hosts() -> list[str]:
    configured = os.getenv("DJANGO_ALLOWED_HOSTS", "")
    if configured:
        hosts = [host.strip() for host in configured.split(",") if host.strip()]
        if "*" in hosts:
            raise RuntimeError("DJANGO_ALLOWED_HOSTS không được dùng '*' ở production.")
        for host in hosts:
            candidate = host.strip("[]")
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host):
                    raise RuntimeError("DJANGO_ALLOWED_HOSTS chứa hostname không hợp lệ.") from None
        return hosts
    hostname = socket.gethostname().strip()
    return [
        host for host in ("localhost", "127.0.0.1", "[::1]", "shophoathuan.local", hostname) if host
    ]


def runtime_data_dir() -> Path:
    """Compatibility alias for callers that need the root of operational data."""
    return runtime_paths().root

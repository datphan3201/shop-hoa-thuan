from __future__ import annotations

import json
import logging
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import connection

from shop_hoa_thuan.version import application_version

BACKUP_FORMAT_VERSION = 1
logger = logging.getLogger("shop.backup")


class BackupError(Exception):
    """Raised when a backup cannot be created or validated."""


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: datetime
    size: int


def create_backup() -> BackupInfo:
    """Create a transactionally consistent SQLite and media backup."""
    backup_root = Path(settings.BACKUP_ROOT)
    media_root = Path(settings.MEDIA_ROOT)
    connection.ensure_connection()
    source_database = connection.connection
    if not isinstance(source_database, sqlite3.Connection):
        raise BackupError("Không thể mở cơ sở dữ liệu SQLite để sao lưu.")

    backup_root.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC)
    timestamp = created_at.strftime("%Y%m%d-%H%M%S-%f")
    final_path = backup_root / f"shop-hoa-thuan-{timestamp}.zip"

    with tempfile.TemporaryDirectory(dir=backup_root) as temporary_directory:
        temporary_path = Path(temporary_directory)
        database_snapshot = temporary_path / "database.sqlite3"
        archive_temporary = temporary_path / "backup.zip"

        destination_database = sqlite3.connect(database_snapshot)
        try:
            source_database.backup(destination_database)
            integrity_result = destination_database.execute("PRAGMA integrity_check").fetchone()
            if not integrity_result or integrity_result[0] != "ok":
                raise BackupError("Bản sao cơ sở dữ liệu không vượt qua kiểm tra toàn vẹn.")
        finally:
            destination_database.close()

        manifest = {
            "application": "Shop Hoà Thuận",
            "format_version": BACKUP_FORMAT_VERSION,
            "application_version": application_version(),
            "created_at_utc": created_at.isoformat(),
            "includes": ["database", "media"],
        }

        with zipfile.ZipFile(
            archive_temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.write(database_snapshot, "database.sqlite3")
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            if media_root.exists():
                for media_file in sorted(path for path in media_root.rglob("*") if path.is_file()):
                    archive.write(media_file, Path("media") / media_file.relative_to(media_root))

        validate_backup(archive_temporary)
        archive_temporary.replace(final_path)

    backup = BackupInfo(path=final_path, created_at=created_at, size=final_path.stat().st_size)
    logger.info("Đã tạo backup file=%s size=%s", backup.path.name, backup.size)
    return backup


def validate_backup(backup_path: Path) -> dict[str, object]:
    """Validate archive structure without extracting untrusted paths."""
    try:
        with zipfile.ZipFile(backup_path, mode="r") as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names or "database.sqlite3" not in names:
                raise BackupError("File sao lưu thiếu database hoặc manifest.")
            if archive.testzip() is not None:
                raise BackupError("File sao lưu bị hỏng.")

            for member in names:
                member_path = Path(member)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise BackupError("File sao lưu chứa đường dẫn không an toàn.")
                if member not in {"manifest.json", "database.sqlite3"} and not member.startswith(
                    "media/"
                ):
                    raise BackupError("File sao lưu chứa dữ liệu không được hỗ trợ.")

            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict):
                raise BackupError("Manifest của file sao lưu không hợp lệ.")
            if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
                raise BackupError("Phiên bản file sao lưu chưa được hỗ trợ.")
            return manifest
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise BackupError("Không thể đọc file sao lưu.") from error


def list_backups() -> list[BackupInfo]:
    backup_root = Path(settings.BACKUP_ROOT)
    if not backup_root.exists():
        return []

    backups = []
    for backup_path in backup_root.glob("shop-hoa-thuan-*.zip"):
        modified = datetime.fromtimestamp(backup_path.stat().st_mtime, tz=UTC)
        backups.append(
            BackupInfo(path=backup_path, created_at=modified, size=backup_path.stat().st_size)
        )
    return sorted(backups, key=lambda backup: backup.created_at, reverse=True)

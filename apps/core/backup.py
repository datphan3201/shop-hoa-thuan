from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.models import Sum

from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.sales.models import Sale
from shop_hoa_thuan.version import application_version

BACKUP_FORMAT_VERSION = 1
logger = logging.getLogger("shop.backup")
restore_logger = logging.getLogger("shop.restore")


class BackupError(Exception):
    """Raised when a backup cannot be created or validated."""


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: datetime
    size: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _media_inventory(media_root: Path) -> tuple[list[dict[str, object]], str]:
    digest = hashlib.sha256()
    inventory: list[dict[str, object]] = []
    if not media_root.exists():
        return inventory, digest.hexdigest()
    for media_file in sorted(path for path in media_root.rglob("*") if path.is_file()):
        relative = media_file.relative_to(media_root).as_posix()
        checksum = _sha256(media_file)
        size = media_file.stat().st_size
        inventory.append({"path": relative, "size": size, "sha256": checksum})
        digest.update(f"{relative}\0{size}\0{checksum}\n".encode())
    return inventory, digest.hexdigest()


def _record_counts() -> dict[str, int]:
    completed_sales = Sale.objects.filter(status=Sale.Status.COMPLETED)
    return {
        "categories": Category.objects.count(),
        "products": Product.objects.count(),
        "variants": ProductVariant.objects.count(),
        "inventory_movements": InventoryMovement.objects.count(),
        "sales": Sale.objects.count(),
        "completed_sales": completed_sales.count(),
        "total_inventory": int(
            ProductVariant.objects.aggregate(total=Sum("quantity"))["total"] or 0
        ),
        "completed_revenue": int(completed_sales.aggregate(total=Sum("final_total"))["total"] or 0),
    }


def _schema_version() -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT app, name FROM django_migrations "
            "WHERE app IN ('core', 'catalog', 'sales') ORDER BY app, id DESC"
        )
        rows = cursor.fetchall()
    latest: dict[str, str] = {}
    for app, name in rows:
        latest.setdefault(str(app), str(name))
    return ";".join(f"{app}:{latest[app]}" for app in sorted(latest))


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

        database_checksum = _sha256(database_snapshot)
        media_inventory, media_checksum = _media_inventory(media_root)
        manifest = {
            "application": "Shop Hoà Thuận",
            "format_version": BACKUP_FORMAT_VERSION,
            "application_version": application_version(),
            "schema_version": _schema_version(),
            "created_at_utc": created_at.isoformat(),
            "timezone": "Asia/Ho_Chi_Minh",
            "includes": ["database", "media"],
            "database": {
                "filename": "db.sqlite3",
                "sha256": database_checksum,
                "record_counts": _record_counts(),
            },
            "media": {
                "sha256": media_checksum,
                "files": media_inventory,
            },
        }

        with zipfile.ZipFile(
            archive_temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.write(database_snapshot, "db.sqlite3")
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
            database_name = "db.sqlite3" if "db.sqlite3" in names else "database.sqlite3"
            if "manifest.json" not in names or database_name not in names:
                raise BackupError("File sao lưu thiếu database hoặc manifest.")
            if archive.testzip() is not None:
                raise BackupError("File sao lưu bị hỏng.")

            for member in names:
                member_path = Path(member)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise BackupError("File sao lưu chứa đường dẫn không an toàn.")
                if member not in {
                    "manifest.json",
                    "db.sqlite3",
                    "database.sqlite3",
                } and not member.startswith("media/"):
                    raise BackupError("File sao lưu chứa dữ liệu không được hỗ trợ.")

            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict):
                raise BackupError("Manifest của file sao lưu không hợp lệ.")
            if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
                raise BackupError("Phiên bản file sao lưu chưa được hỗ trợ.")
            database_metadata = manifest.get("database")
            if isinstance(database_metadata, dict) and database_metadata.get("sha256"):
                with tempfile.NamedTemporaryFile() as database_file:
                    database_file.write(archive.read(database_name))
                    database_file.flush()
                    if _sha256(Path(database_file.name)) != database_metadata["sha256"]:
                        raise BackupError("Checksum database trong file sao lưu không khớp.")
                    with sqlite3.connect(
                        f"file:{database_file.name}?mode=ro", uri=True
                    ) as database:
                        result = database.execute("PRAGMA integrity_check").fetchone()
                    if not result or result[0] != "ok":
                        raise BackupError("Database trong file sao lưu không toàn vẹn.")
            return manifest
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise BackupError("Không thể đọc file sao lưu.") from error


def _write_zip_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, target: Path) -> None:
    if member.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member, "r") as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination)


def _extract_backup(backup_path: Path, staging: Path) -> tuple[Path, Path]:
    manifest = validate_backup(backup_path)
    database_name = "db.sqlite3"
    with zipfile.ZipFile(backup_path, mode="r") as archive:
        if database_name not in archive.namelist():
            database_name = "database.sqlite3"
        database_path = staging / database_name
        _write_zip_member(archive, archive.getinfo(database_name), database_path)
        media_path = staging / "media"
        for member in archive.infolist():
            if member.filename.startswith("media/"):
                relative = Path(member.filename).relative_to("media")
                _write_zip_member(archive, member, media_path / relative)
    if not manifest:
        raise BackupError("Manifest của file sao lưu không hợp lệ.")
    with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as database:
        result = database.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise BackupError("Database khôi phục không vượt qua kiểm tra toàn vẹn.")
    media_metadata = manifest.get("media")
    if isinstance(media_metadata, dict) and media_metadata.get("sha256"):
        _, media_checksum = _media_inventory(media_path)
        if media_checksum != media_metadata["sha256"]:
            raise BackupError("Checksum media trong file sao lưu không khớp.")
    return database_path, media_path


def restore_backup(backup_path: Path) -> BackupInfo:
    """Restore a validated archive, preserving a verified pre-restore backup."""
    runtime_paths = settings.RUNTIME_PATHS
    database_path = Path(str(settings.DATABASES["default"]["NAME"]))
    media_root = Path(settings.MEDIA_ROOT)
    rollback_root = Path(runtime_paths.rollback)
    backup_root = Path(settings.BACKUP_ROOT)
    backup_root.mkdir(parents=True, exist_ok=True)
    rollback_root.mkdir(parents=True, exist_ok=True)
    current_backup = create_backup()
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    staging_root = Path(tempfile.mkdtemp(prefix="restore-", dir=backup_root))
    old_database = rollback_root / f"db-{timestamp}.sqlite3"
    old_media = rollback_root / f"media-{timestamp}"
    try:
        staged_database, staged_media = _extract_backup(backup_path, staging_root)
        connection.close()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        if database_path.exists():
            os.replace(database_path, old_database)
        if media_root.exists():
            os.replace(media_root, old_media)
        os.replace(staged_database, database_path)
        if staged_media.exists():
            os.replace(staged_media, media_root)
        else:
            media_root.mkdir(parents=True, exist_ok=True)
        restore_logger.info(
            "Đã khôi phục backup=%s pre_restore_backup=%s",
            backup_path.name,
            current_backup.path.name,
        )
        return current_backup
    except Exception as error:
        connection.close()
        database_path.unlink(missing_ok=True)
        if old_database.exists():
            os.replace(old_database, database_path)
        if media_root.exists():
            shutil.rmtree(media_root)
        if old_media.exists():
            os.replace(old_media, media_root)
        restore_logger.exception("Khôi phục backup thất bại backup=%s", backup_path.name)
        raise BackupError("Khôi phục thất bại; dữ liệu hiện tại đã được giữ lại.") from error
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


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

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from django.test import override_settings

from apps.catalog.models import Category
from apps.core.backup import create_backup, list_backups, validate_backup


@pytest.mark.django_db(transaction=True)
def test_backup_contains_consistent_database_media_and_manifest(tmp_path: Path) -> None:
    backup_root = tmp_path / "backups"
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "sample.txt").write_text("ảnh mẫu", encoding="utf-8")
    Category.objects.create(name="Áo thun")

    with override_settings(BACKUP_ROOT=backup_root, MEDIA_ROOT=media_root):
        backup = create_backup()
        manifest = validate_backup(backup.path)
        backups = list_backups()

    assert manifest["application"] == "Shop Hoà Thuận"
    assert manifest["format_version"] == 1
    assert backup.path.exists()
    assert backups[0].path == backup.path

    with zipfile.ZipFile(backup.path) as archive:
        assert set(archive.namelist()) == {
            "database.sqlite3",
            "manifest.json",
            "media/sample.txt",
        }
        stored_manifest = json.loads(archive.read("manifest.json"))
        assert stored_manifest["format_version"] == 1

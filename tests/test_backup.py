from __future__ import annotations

import json
import sqlite3
import time
import zipfile
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from apps.catalog.models import Category
from apps.core.backup import create_backup, list_backups, restore_backup, validate_backup
from apps.core.security import UNLOCKED_UNTIL_KEY
from shop_hoa_thuan.version import application_version


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
    assert manifest["application_version"] == application_version()
    assert backup.path.exists()
    assert backups[0].path == backup.path

    with zipfile.ZipFile(backup.path) as archive:
        assert set(archive.namelist()) == {
            "db.sqlite3",
            "manifest.json",
            "media/sample.txt",
        }
        stored_manifest = json.loads(archive.read("manifest.json"))
    assert stored_manifest["format_version"] == 1
    assert stored_manifest["database"]["filename"] == "db.sqlite3"
    assert stored_manifest["database"]["record_counts"]["categories"] == 1
    assert stored_manifest["media"]["files"][0]["path"] == "sample.txt"


@pytest.mark.django_db(transaction=True)
def test_restore_replaces_database_and_media_after_validation(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime" / "data" / "db.sqlite3"
    backup_root = tmp_path / "backups"
    media_root = tmp_path / "media"
    media_root.mkdir()
    original_media = media_root / "original.txt"
    original_media.write_text("original", encoding="utf-8")
    databases = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_path,
            "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
        }
    }
    with override_settings(BACKUP_ROOT=backup_root, MEDIA_ROOT=media_root, DATABASES=databases):
        call_command("migrate", verbosity=0)
        Category.objects.create(name="Bản gốc")
        backup = create_backup()
        Category.objects.create(name="Không nên còn")
        (media_root / "new.txt").write_text("new", encoding="utf-8")

        restore_backup(backup.path)
        with sqlite3.connect(database_path) as database:
            assert database.execute("SELECT name FROM catalog_category").fetchall() == [
                ("Bản gốc",)
            ]
        assert original_media.read_text(encoding="utf-8") == "original"
        assert not (media_root / "new.txt").exists()


@pytest.mark.django_db(transaction=True)
def test_backup_request_idempotency_creates_one_archive(client: Client, tmp_path: Path) -> None:
    session = client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()
    backup_root = tmp_path / "backups"
    media_root = tmp_path / "media"
    headers = {"Idempotency-Key": "backup-001"}

    with override_settings(BACKUP_ROOT=backup_root, MEDIA_ROOT=media_root):
        first = client.post(reverse("backup-create"), headers=headers)
        replay = client.post(reverse("backup-create"), headers=headers)

    assert first.status_code == 302
    assert replay.status_code == 302
    assert len(list(backup_root.glob("*.zip"))) == 1

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse

from apps.catalog.models import Category
from apps.core.backup import create_backup, list_backups, validate_backup
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
            "database.sqlite3",
            "manifest.json",
            "media/sample.txt",
        }
        stored_manifest = json.loads(archive.read("manifest.json"))
        assert stored_manifest["format_version"] == 1


@pytest.mark.django_db(transaction=True)
def test_backup_request_idempotency_creates_one_archive(client: Client, tmp_path: Path) -> None:
    owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(owner)
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

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.core.update import UpdateError, stage_update_package, validate_update_package
from scripts.build_update_package import build_package
from shop_hoa_thuan.runtime import RuntimePaths
from shop_hoa_thuan.update_runner import _configure_firewall, perform_update
from shop_hoa_thuan.version import application_version

CURRENT_VERSION = application_version()
TARGET_VERSION = "1.2.0"


def _package(path: Path, *, target: str = TARGET_VERSION, checksum: str | None = None) -> None:
    payload = b"new application"
    manifest = {
        "current_version": CURRENT_VERSION,
        "target_version": target,
        "schema_version": "core:0004",
        "files": [
            {
                "path": "application/application.txt",
                "sha256": checksum or hashlib.sha256(payload).hexdigest(),
            }
        ],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("update-manifest.json", json.dumps(manifest))
        archive.writestr("application/application.txt", payload)


def test_update_package_validates_and_stages_files(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    _package(package)

    manifest = validate_update_package(package, CURRENT_VERSION)
    stage = tmp_path / "stage"
    staged = stage_update_package(package, stage, CURRENT_VERSION)

    assert manifest.target_version == TARGET_VERSION
    assert staged.files == (("application/application.txt", manifest.files[0][1]),)
    assert (stage / "application/application.txt").read_bytes() == b"new application"


def test_update_staging_failure_cleans_partial_directory(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    _package(package)
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(FileExistsError):
        stage_update_package(package, stage, CURRENT_VERSION)

    assert (stage / "old.txt").exists()


def test_update_package_builder_uses_application_prefix_and_atomic_output(tmp_path: Path) -> None:
    source = tmp_path / "application"
    source.mkdir()
    (source / "ShopHoaThuanServer.exe").write_bytes(b"server")
    package = tmp_path / "release" / "update.zip"

    build_package(source, package, CURRENT_VERSION, TARGET_VERSION)
    manifest = validate_update_package(package, CURRENT_VERSION)

    assert manifest.target_version == TARGET_VERSION
    assert manifest.files[0][0] == "application/ShopHoaThuanServer.exe"


@pytest.mark.django_db(transaction=True)
def test_update_replaces_complete_tree_and_releases_maintenance(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    runner = b"migration runner"
    manifest = {
        "format_version": 1,
        "current_version": CURRENT_VERSION,
        "target_version": TARGET_VERSION,
        "schema_version": "core:0004",
        "files": [
            {"path": "application/new.txt", "sha256": hashlib.sha256(b"new").hexdigest()},
            {
                "path": "application/ShopHoaThuanMigration/ShopHoaThuanMigration.exe",
                "sha256": hashlib.sha256(runner).hexdigest(),
            },
        ],
    }
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("update-manifest.json", json.dumps(manifest))
        archive.writestr("application/new.txt", b"new")
        archive.writestr("application/ShopHoaThuanMigration/ShopHoaThuanMigration.exe", runner)

    app_root = tmp_path / "app"
    app_root.mkdir()
    (app_root / "old.txt").write_text("old", encoding="utf-8")
    runtime = RuntimePaths(tmp_path / "runtime")
    with (
        override_settings(RUNTIME_PATHS=runtime, BACKUP_ROOT=tmp_path / "backups"),
        patch("shop_hoa_thuan.update_runner.subprocess.run") as run,
        patch("shop_hoa_thuan.update_runner._wait_service_health"),
    ):
        run.return_value.returncode = 0
        assert perform_update(package, app_root) == TARGET_VERSION

    assert (app_root / "new.txt").read_text(encoding="utf-8") == "new"
    assert not (app_root / "old.txt").exists()


@pytest.mark.parametrize(
    ("target", "current", "message"),
    [(CURRENT_VERSION, CURRENT_VERSION, "downgrade"), ("0.9.0", CURRENT_VERSION, "downgrade")],
)
def test_update_rejects_downgrade_or_same_version(
    tmp_path: Path, target: str, current: str, message: str
) -> None:
    package = tmp_path / "update.zip"
    _package(package, target=target)

    with pytest.raises(UpdateError, match=message):
        validate_update_package(package, current)


def test_update_rejects_checksum_mismatch(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    _package(package, checksum="0" * 64)

    with pytest.raises(UpdateError, match="Checksum"):
        validate_update_package(package, CURRENT_VERSION)


def test_windows_update_configures_firewall_from_new_application_tree(tmp_path: Path) -> None:
    app_root = tmp_path / "application"
    app_root.mkdir()
    (app_root / "configure_firewall.ps1").write_text("param()", encoding="utf-8")
    (app_root / "ShopHoaThuanServer.exe").write_bytes(b"server")

    with (
        patch("shop_hoa_thuan.update_runner.os.name", "nt"),
        patch("shop_hoa_thuan.update_runner.subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        _configure_firewall(app_root)

    command = run.call_args.args[0]
    assert command[:5] == [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
    ]
    assert command[command.index("-Action") + 1] == "Install"
    assert command[command.index("-ProgramPath") + 1].endswith("ShopHoaThuanServer.exe")

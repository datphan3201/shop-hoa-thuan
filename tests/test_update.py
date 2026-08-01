from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from apps.core.update import UpdateError, stage_update_package, validate_update_package
from scripts.build_update_package import build_package


def _package(path: Path, *, target: str = "1.1.0", checksum: str | None = None) -> None:
    payload = b"new application"
    manifest = {
        "current_version": "1.0.0",
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

    manifest = validate_update_package(package, "1.0.0")
    stage = tmp_path / "stage"
    staged = stage_update_package(package, stage, "1.0.0")

    assert manifest.target_version == "1.1.0"
    assert staged.files == (("application/application.txt", manifest.files[0][1]),)
    assert (stage / "application/application.txt").read_bytes() == b"new application"


def test_update_staging_failure_cleans_partial_directory(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    _package(package)
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(FileExistsError):
        stage_update_package(package, stage, "1.0.0")

    assert (stage / "old.txt").exists()


def test_update_package_builder_uses_application_prefix_and_atomic_output(tmp_path: Path) -> None:
    source = tmp_path / "application"
    source.mkdir()
    (source / "ShopHoaThuanServer.exe").write_bytes(b"server")
    package = tmp_path / "release" / "update.zip"

    build_package(source, package, "1.0.0", "1.1.0")
    manifest = validate_update_package(package, "1.0.0")

    assert manifest.target_version == "1.1.0"
    assert manifest.files[0][0] == "application/ShopHoaThuanServer.exe"


@pytest.mark.parametrize(
    ("target", "current", "message"),
    [("1.0.0", "1.0.0", "downgrade"), ("0.9.0", "1.0.0", "downgrade")],
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
        validate_update_package(package, "1.0.0")

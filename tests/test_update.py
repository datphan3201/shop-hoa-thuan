from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from apps.core.update import UpdateError, stage_update_package, validate_update_package


def _package(path: Path, *, target: str = "1.1.0", checksum: str | None = None) -> None:
    payload = b"new application"
    manifest = {
        "current_version": "1.0.0",
        "target_version": target,
        "schema_version": "core:0004",
        "files": [
            {"path": "application.txt", "sha256": checksum or hashlib.sha256(payload).hexdigest()}
        ],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("update-manifest.json", json.dumps(manifest))
        archive.writestr("application.txt", payload)


def test_update_package_validates_and_stages_files(tmp_path: Path) -> None:
    package = tmp_path / "update.zip"
    _package(package)

    manifest = validate_update_package(package, "1.0.0")
    stage = tmp_path / "stage"
    staged = stage_update_package(package, stage, "1.0.0")

    assert manifest.target_version == "1.1.0"
    assert staged.files == (("application.txt", manifest.files[0][1]),)
    assert (stage / "application.txt").read_bytes() == b"new application"


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

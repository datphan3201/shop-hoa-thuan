"""Validation and staging primitives for local Windows update packages."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


class UpdateError(Exception):
    """Raised when an update package is unsafe or incompatible."""


@dataclass(frozen=True)
class UpdateManifest:
    current_version: str
    target_version: str
    files: tuple[tuple[str, str], ...]
    schema_version: str


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise UpdateError("Version update không đúng Semantic Versioning.")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _member_is_safe(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts and name == path.as_posix()


def validate_update_package(package_path: Path, current_version: str) -> UpdateManifest:
    try:
        with zipfile.ZipFile(package_path, mode="r") as archive:
            if archive.testzip() is not None:
                raise UpdateError("Gói update bị hỏng.")
            names = archive.namelist()
            if "update-manifest.json" not in names:
                raise UpdateError("Gói update thiếu manifest.")
            if any(not _member_is_safe(name) for name in names):
                raise UpdateError("Gói update chứa đường dẫn không an toàn.")
            raw_manifest = json.loads(archive.read("update-manifest.json"))
            if not isinstance(raw_manifest, dict):
                raise UpdateError("Manifest update không hợp lệ.")
            target_version = str(raw_manifest.get("target_version", ""))
            package_current = str(raw_manifest.get("current_version", ""))
            schema_version = str(raw_manifest.get("schema_version", ""))
            _version_tuple(current_version)
            if package_current != current_version:
                raise UpdateError("Gói update không dành cho version hiện tại.")
            if _version_tuple(target_version) <= _version_tuple(current_version):
                raise UpdateError("Không cho downgrade hoặc cài lại cùng version ngoài ý muốn.")
            raw_files = raw_manifest.get("files", [])
            if not isinstance(raw_files, list):
                raise UpdateError("Danh sách file update không hợp lệ.")
            files: list[tuple[str, str]] = []
            for entry in raw_files:
                if not isinstance(entry, dict):
                    raise UpdateError("Manifest update có file không hợp lệ.")
                name = str(entry.get("path", ""))
                checksum = str(entry.get("sha256", ""))
                if not name or name not in names or not _member_is_safe(name):
                    raise UpdateError("Manifest update trỏ tới file không an toàn.")
                if not checksum or len(checksum) != 64:
                    raise UpdateError("Manifest update thiếu checksum SHA-256.")
                with archive.open(name, "r") as source:
                    digest = hashlib.sha256(source.read()).hexdigest()
                if digest != checksum:
                    raise UpdateError(f"Checksum không khớp: {name}.")
                files.append((name, checksum))
            return UpdateManifest(
                current_version=package_current,
                target_version=target_version,
                files=tuple(files),
                schema_version=schema_version,
            )
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise UpdateError("Không thể đọc gói update.") from error


def stage_update_package(
    package_path: Path, staging_root: Path, current_version: str
) -> UpdateManifest:
    manifest = validate_update_package(package_path, current_version)
    staging_root.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(package_path, mode="r") as archive:
            for name, _ in manifest.files:
                destination = staging_root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name, "r") as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
        return manifest
    except Exception as error:
        shutil.rmtree(staging_root, ignore_errors=True)
        if isinstance(error, UpdateError):
            raise
        raise UpdateError("Không thể stage gói update.") from error


def temporary_update_stage(package_path: Path, current_version: str) -> tuple[Path, UpdateManifest]:
    stage = Path(tempfile.mkdtemp(prefix="update-stage-"))
    try:
        manifest = stage_update_package(package_path, stage / "application", current_version)
        return stage, manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

"""Build a checksummed local update package from a frozen application directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
import zipfile
from pathlib import Path


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"Invalid semantic version: {value}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_package(
    source_root: Path, output: Path, current_version: str, target_version: str
) -> None:
    _version_tuple(current_version)
    if _version_tuple(target_version) <= _version_tuple(current_version):
        raise ValueError("Target version must be newer than current version")
    if not source_root.is_dir():
        raise ValueError(f"Application directory does not exist: {source_root}")

    files: list[tuple[Path, str]] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = Path("application") / path.relative_to(source_root)
        files.append((path, relative.as_posix()))
    if not files:
        raise ValueError("Application directory is empty")

    manifest = {
        "format_version": 1,
        "current_version": current_version,
        "target_version": target_version,
        "schema_version": "declared-by-release-process",
        "files": [{"path": name, "sha256": _sha256(path)} for path, name in files],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("update-manifest.json", json.dumps(manifest, indent=2))
            for path, name in files:
                archive.write(path, name)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--current-version")
    args = parser.parse_args()
    if args.current_version:
        current_version = args.current_version
    else:
        project_file = Path(__file__).parents[1] / "pyproject.toml"
        with project_file.open("rb") as source:
            current_version = str(tomllib.load(source)["project"]["version"])
    build_package(args.source_root, args.output, current_version, args.target_version)
    print(f"Update package created: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

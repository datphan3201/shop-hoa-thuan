from __future__ import annotations

import tomllib
from pathlib import Path

VERSION_SOURCE = Path(__file__).resolve().parent.parent / "pyproject.toml"


def application_version() -> str:
    """Read the sole authored version from project metadata."""
    with VERSION_SOURCE.open("rb") as source:
        metadata = tomllib.load(source)
    return str(metadata["project"]["version"])

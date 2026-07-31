from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def application_version() -> str:
    try:
        return version("shop-hoa-thuan")
    except PackageNotFoundError:
        return "0.1.0-dev"

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from django.test import override_settings

from shop_hoa_thuan.runtime import RuntimePaths


@pytest.fixture(autouse=True)
def isolate_runtime_paths(tmp_path: Path) -> Iterator[None]:
    """Never let tests contend with a developer/server runtime data directory."""
    with override_settings(RUNTIME_PATHS=RuntimePaths(tmp_path / "runtime")):
        yield

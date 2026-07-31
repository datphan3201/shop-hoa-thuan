from __future__ import annotations

import sqlite3
from pathlib import Path

from shop_hoa_thuan.runtime import ensure_runtime_layout, migrate_legacy_layout, runtime_paths


def test_runtime_uses_production_like_tree_in_development(
    monkeypatch: object, tmp_path: Path
) -> None:
    monkeypatch.setenv("SHOP_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]

    paths = ensure_runtime_layout()

    assert paths == runtime_paths()
    assert paths.database == tmp_path / "data" / "db.sqlite3"
    assert all(
        path.exists()
        for path in (
            paths.data,
            paths.media,
            paths.backups,
            paths.rollback,
            paths.logs,
            paths.config,
        )
    )


def test_legacy_database_is_copied_and_verified_before_source_is_retained(
    monkeypatch: object, tmp_path: Path
) -> None:
    monkeypatch.setenv("SHOP_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    legacy_database = tmp_path / "shop-hoa-thuan.sqlite3"
    with sqlite3.connect(legacy_database) as database:
        database.execute("CREATE TABLE sample (value TEXT)")
        database.execute("INSERT INTO sample VALUES ('ok')")

    paths = ensure_runtime_layout()
    assert migrate_legacy_layout(paths) is True
    assert legacy_database.exists()
    with sqlite3.connect(paths.database) as database:
        assert database.execute("SELECT value FROM sample").fetchone() == ("ok",)
    assert migrate_legacy_layout(paths) is False

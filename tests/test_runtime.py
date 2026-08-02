from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    migrate_legacy_layout,
    production_allowed_hosts,
    runtime_paths,
)


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


def test_default_production_hosts_include_discovered_lan_ip(monkeypatch: object) -> None:
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)  # type: ignore[attr-defined]
    with patch("shop_hoa_thuan.runtime.lan_ipv4_addresses", return_value=["192.168.1.10"]):
        hosts = production_allowed_hosts()

    assert "localhost" in hosts
    assert "127.0.0.1" in hosts
    assert "192.168.1.10" in hosts


def test_default_production_hosts_skip_invalid_discovered_windows_hostname(
    monkeypatch: object,
) -> None:
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)  # type: ignore[attr-defined]
    with (
        patch("shop_hoa_thuan.runtime.socket.gethostname", return_value="SHOP_SERVER_TEST"),
        patch("shop_hoa_thuan.runtime.lan_ipv4_addresses", return_value=[]),
    ):
        hosts = production_allowed_hosts()

    assert "SHOP_SERVER_TEST" not in hosts
    assert "localhost" in hosts
    assert "127.0.0.1" in hosts


def test_auto_discovered_hosts_round_trip_through_environment(monkeypatch: object) -> None:
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)  # type: ignore[attr-defined]
    with (
        patch("shop_hoa_thuan.runtime.socket.gethostname", return_value="SHOP_SERVER_TEST"),
        patch("shop_hoa_thuan.runtime.lan_ipv4_addresses", return_value=[]),
    ):
        hosts = production_allowed_hosts()
        monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", ",".join(hosts))  # type: ignore[attr-defined]
        assert production_allowed_hosts() == hosts


@pytest.mark.parametrize("value", ["*", "SHOP_SERVER_TEST"])
def test_explicit_invalid_production_hosts_remain_rejected(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", value)

    with pytest.raises(RuntimeError, match=r"hostname|\*"):
        production_allowed_hosts()

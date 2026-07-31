from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shop_hoa_thuan import launcher


def test_winsw_service_does_not_enable_host_wildcard_or_run_migrations() -> None:
    root = Path(__file__).resolve().parents[1]
    xml = (root / "packaging" / "winsw" / "ShopHoaThuanService.xml").read_text(encoding="utf-8")

    assert "<name>Shop Hoà Thuận Server</name>" in xml
    assert "DJANGO_ALLOWED_HOSTS" not in xml
    assert "ShopHoaThuanServer.exe" in xml
    assert "migrate" not in xml.lower()
    assert "%ProgramData%\\Shop Hoa Thuan\\logs\\service" in xml


def test_admin_service_script_is_scoped_to_test_service_and_private_firewall() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "windows" / "phase9_test_service.ps1").read_text(encoding="utf-8")

    assert "ShopHoaThuanTestServer" in script
    assert "-Profile Private" in script
    assert "Shop Hoa Thuan Test LAN 2505" in script
    assert "[switch]$Cleanup" in script


def test_pyinstaller_bundle_keeps_django_logging_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "packaging" / "pyinstaller" / "shop_hoa_thuan.spec").read_text(encoding="utf-8")

    assert '"apps.core.logging"' in spec
    assert 'collect_submodules("whitenoise")' in spec
    assert 'project_root / "pyproject.toml"' in spec
    assert "a.zipfiles" in spec
    assert "sys.path.insert(0, str(project_root))" in spec


def test_native_server_smoke_script_uses_only_the_packaged_server() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "windows" / "test_native_server.ps1").read_text(encoding="utf-8")

    assert "ShopHoaThuanServer.exe" in script
    assert "Invoke-WebRequest" in script
    assert "Stop-Process" in script
    assert "RedirectStandardError" in script
    assert "python -c" not in script


def test_launcher_opens_existing_server_without_starting_another() -> None:
    with (
        patch("shop_hoa_thuan.launcher.is_healthy", return_value=True),
        patch("shop_hoa_thuan.launcher.request_service_start") as start,
        patch("shop_hoa_thuan.launcher.webbrowser.open") as open_browser,
    ):
        assert launcher.main() == 0

    start.assert_not_called()
    open_browser.assert_called_once_with("http://127.0.0.1:2505/")


def test_launcher_requests_windows_service_and_never_spawns_waitress() -> None:
    with (
        patch("shop_hoa_thuan.launcher.is_healthy", return_value=False),
        patch("shop_hoa_thuan.launcher.request_service_start", return_value=True) as start,
        patch("shop_hoa_thuan.launcher.wait_for_health", return_value=True),
        patch("shop_hoa_thuan.launcher.webbrowser.open"),
    ):
        assert launcher.main() == 0

    start.assert_called_once()

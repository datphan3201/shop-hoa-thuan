from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

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
    assert "migrate --noinput" in script
    assert "Stop-Process -Id $service.ProcessId -Force" in script
    assert "Remove-TestResources" in script


def test_pyinstaller_bundle_keeps_django_logging_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "packaging" / "pyinstaller" / "shop_hoa_thuan.spec").read_text(encoding="utf-8")

    assert '"apps.core.logging"' in spec
    assert 'collect_submodules("whitenoise")' in spec
    assert 'project_root / "pyproject.toml"' in spec
    assert "a.zipfiles" in spec
    assert "sys.path.insert(0, str(project_root))" in spec


@pytest.mark.parametrize("spec_name", ["health_check.spec", "launcher.spec", "update_gui.spec"])
def test_standalone_windows_specs_embed_runtime_binaries(spec_name: str) -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "packaging" / "pyinstaller" / spec_name).read_text(encoding="utf-8")

    assert "a.binaries" in spec
    assert "a.zipfiles" in spec
    assert "a.datas" in spec


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


def test_installer_runs_migration_and_opens_direct_lan_application() -> None:
    root = Path(__file__).resolve().parents[1]
    installer = (root / "packaging" / "installer" / "ShopHoaThuan.iss").read_text(encoding="utf-8")
    build_script = (root / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert "#error AppVersion" in installer
    assert "ShopHoaThuanMigration.exe" in installer
    assert "http://127.0.0.1:2505/setup/" not in installer
    assert 'Filename: "http://127.0.0.1:2505/"' in installer
    assert "pyproject.toml" in build_script
    assert "migration_runner.spec" in build_script
    assert "update_gui.spec" in build_script
    assert "backup_gui.spec" in build_script
    assert "restore_gui.spec" in build_script
    assert 'Copy-Item "packaging\\installer\\configure_firewall.ps1"' in build_script
    assert "Cập nhật Shop Hoà Thuận" in installer


def test_installer_contains_backup_and_restore_utilities() -> None:
    root = Path(__file__).resolve().parents[1]
    installer = (root / "packaging" / "installer" / "ShopHoaThuan.iss").read_text(encoding="utf-8")

    assert "ShopHoaThuanBackup.exe" in installer
    assert "ShopHoaThuanRestore.exe" in installer


def test_installer_configures_only_private_firewall_for_packaged_server() -> None:
    root = Path(__file__).resolve().parents[1]
    installer = (root / "packaging" / "installer" / "ShopHoaThuan.iss").read_text(encoding="utf-8")
    firewall = (root / "packaging" / "installer" / "configure_firewall.ps1").read_text(
        encoding="utf-8"
    )

    assert "configure_firewall.ps1" in installer
    assert "-Action Install" in installer
    assert "-Action Remove" in installer
    assert "Shop Hoa Thuan LAN 2505" in firewall
    assert "-Profile Private" in firewall
    assert "-Program $ProgramPath" in firewall
    assert "Public" not in firewall
    assert "-LocalPort $Port" in firewall


def test_update_gui_runs_from_external_worker_before_replacing_application_tree() -> None:
    root = Path(__file__).resolve().parents[1]
    update_gui = (root / "shop_hoa_thuan" / "update_gui.py").read_text(encoding="utf-8")

    assert '"--execute"' in update_gui
    assert "shutil.copy2(sys.executable, worker)" in update_gui
    assert 'tempfile.mkdtemp(prefix="update-worker-"' in update_gui
    assert "_installed_version" in update_gui
    assert '"--current-version"' in update_gui

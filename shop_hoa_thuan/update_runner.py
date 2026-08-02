"""Local update transaction used by the Windows update GUI."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from apps.core.update import UpdateError, stage_update_package
from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    ensure_runtime_secret,
    production_allowed_hosts,
)
from shop_hoa_thuan.version import application_version

_FIREWALL_RULE_NAME = "Shop Hoa Thuan LAN 2505"


def _service_command(action: str) -> None:
    if os.name != "nt":
        return
    service_name = os.getenv("SHOP_SERVICE_NAME", "ShopHoaThuanServer")
    result = subprocess.run(
        ["sc.exe", action, service_name],
        check=False,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode not in {0, 1056}:
        raise UpdateError(f"Không thể {action} service: {result.stdout.strip()}")


def _wait_service_health(timeout_seconds: int = 30) -> None:
    from shop_hoa_thuan.launcher import is_healthy

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_healthy():
            return
        time.sleep(0.5)
    raise UpdateError("Service không đạt health sau update.")


def _firewall_rule_exists() -> bool:
    if os.name != "nt":
        return False
    command = (
        "if (Get-NetFirewallRule -DisplayName "
        f"'{_FIREWALL_RULE_NAME}' -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def _remove_firewall_rule() -> None:
    if os.name != "nt":
        return
    command = (
        f"Get-NetFirewallRule -DisplayName '{_FIREWALL_RULE_NAME}' "
        "-ErrorAction SilentlyContinue | "
        "Remove-NetFirewallRule -ErrorAction SilentlyContinue"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _configure_firewall(app_root: Path) -> None:
    if os.name != "nt":
        return
    script = app_root / "configure_firewall.ps1"
    server = app_root / "ShopHoaThuanServer.exe"
    if not script.is_file() or not server.is_file():
        raise UpdateError("Gói update thiếu cấu hình firewall hoặc server executable.")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Action",
            "Install",
            "-ProgramPath",
            str(server),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise UpdateError(f"Không thể cấu hình firewall LAN trên Public/Private: {detail}")


def perform_update(
    package_path: Path,
    app_root: Path,
    *,
    current_version: str | None = None,
) -> str:
    """Run a bounded update with app and database rollback on failure."""
    from apps.core.backup import BackupError, create_backup, restore_backup
    from apps.core.operations import maintenance_operation

    current_version = current_version or application_version()
    configured_stage = os.getenv("SHOP_UPDATE_STAGE")
    created_stage = configured_stage is None
    if configured_stage is None:
        cleanup_root = Path(tempfile.mkdtemp(prefix="update-stage-", dir=app_root.parent))
    else:
        cleanup_root = Path(configured_stage)
    manifest_stage = cleanup_root / "package" if created_stage else cleanup_root
    try:
        if configured_stage and manifest_stage.exists():
            shutil.rmtree(manifest_stage)
        manifest = stage_update_package(package_path, manifest_stage, current_version)
        staged_app = manifest_stage / "application"
        if not staged_app.is_dir():
            raise UpdateError("Gói update thiếu thư mục application.")

        runtime_paths = ensure_runtime_layout()
        rollback_app = runtime_paths.rollback / f"app-{current_version}"
        rollback_app.parent.mkdir(parents=True, exist_ok=True)
        firewall_was_present = _firewall_rule_exists()
        with maintenance_operation("update", timeout_seconds=60):
            pre_update_backup = create_backup()
            _service_command("stop")
            try:
                if rollback_app.exists():
                    shutil.rmtree(rollback_app)
                shutil.copytree(app_root, rollback_app)
                # An update package is a complete application tree.  Replacing
                # the directory prevents stale binaries/assets from creating a
                # mixed old/new runtime after a successful update.
                if app_root.exists():
                    shutil.rmtree(app_root)
                shutil.copytree(staged_app, app_root)
                migration_runner = app_root / "ShopHoaThuanMigration" / "ShopHoaThuanMigration.exe"
                if not migration_runner.exists():
                    raise UpdateError("Gói update thiếu migration runner.")
                result = subprocess.run([str(migration_runner)], check=False)
                if result.returncode != 0:
                    raise UpdateError("Migration update thất bại.")
                _configure_firewall(app_root)
                _service_command("start")
                _wait_service_health()
            except Exception as error:
                _service_command("stop")
                if app_root.exists():
                    shutil.rmtree(app_root)
                shutil.copytree(rollback_app, app_root)
                try:
                    restore_backup(pre_update_backup.path)
                except BackupError as restore_error:
                    raise UpdateError(
                        "Rollback update thất bại; cần giữ nguyên evidence để xử lý."
                    ) from restore_error
                if not firewall_was_present:
                    _remove_firewall_rule()
                _service_command("start")
                raise UpdateError("Update thất bại và đã rollback.") from error
        return manifest.target_version
    finally:
        shutil.rmtree(cleanup_root, ignore_errors=True)


def initialize_runtime_environment() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECRET_KEY", ensure_runtime_secret())
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", ",".join(production_allowed_hosts()))
    ensure_runtime_layout()


if __name__ == "__main__":
    import argparse

    import django

    parser = argparse.ArgumentParser(description="Cập nhật Shop Hoà Thuận từ gói cục bộ.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--current-version")
    args = parser.parse_args()
    initialize_runtime_environment()
    django.setup()
    raise SystemExit(
        perform_update(args.package, args.app_root, current_version=args.current_version)
    )

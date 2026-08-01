"""Local update transaction used by the Windows update GUI."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from apps.core.update import UpdateError, stage_update_package
from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    ensure_runtime_secret,
    production_allowed_hosts,
)
from shop_hoa_thuan.version import application_version


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


def perform_update(package_path: Path, app_root: Path) -> str:
    """Run a bounded update with app and database rollback on failure."""
    from apps.core.backup import BackupError, create_backup, restore_backup
    from apps.core.operations import maintenance_operation

    manifest_stage = Path(os.getenv("SHOP_UPDATE_STAGE", str(app_root.parent / "update-stage")))
    manifest = stage_update_package(package_path, manifest_stage, application_version())
    staged_app = manifest_stage / "application"
    if not staged_app.is_dir():
        raise UpdateError("Gói update thiếu thư mục application.")

    runtime_paths = ensure_runtime_layout()
    rollback_app = runtime_paths.rollback / f"app-{application_version()}"
    rollback_app.parent.mkdir(parents=True, exist_ok=True)
    with maintenance_operation("update", timeout_seconds=60):
        pre_update_backup = create_backup()
        _service_command("stop")
        try:
            if rollback_app.exists():
                shutil.rmtree(rollback_app)
            shutil.copytree(app_root, rollback_app)
            for source in staged_app.rglob("*"):
                relative = source.relative_to(staged_app)
                destination = app_root / relative
                if source.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            migration_runner = app_root / "ShopHoaThuanMigration" / "ShopHoaThuanMigration.exe"
            if not migration_runner.exists():
                raise UpdateError("Gói update thiếu migration runner.")
            result = subprocess.run([str(migration_runner)], check=False)
            if result.returncode != 0:
                raise UpdateError("Migration update thất bại.")
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
            _service_command("start")
            raise UpdateError("Update thất bại và đã rollback.") from error
    return manifest.target_version


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
    args = parser.parse_args()
    initialize_runtime_environment()
    django.setup()
    raise SystemExit(perform_update(args.package, args.app_root))

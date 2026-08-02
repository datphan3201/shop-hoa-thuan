"""Double-click update UI; the transaction itself lives in update_runner."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from json import loads
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.request import urlopen

from apps.core.update import UpdateError, validate_update_package
from shop_hoa_thuan.runtime import ensure_runtime_layout
from shop_hoa_thuan.update_runner import initialize_runtime_environment, perform_update
from shop_hoa_thuan.version import application_version


def _application_root() -> Path:
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent
    executable_parent = Path(sys.executable).resolve().parent
    if (executable_parent / "ShopHoaThuanServer.exe").exists():
        return executable_parent
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    return Path(program_files) / "Shop Hoa Thuan"


def _installed_version() -> str:
    """Read the running app version so a portable updater can bootstrap an older install."""
    try:
        with urlopen("http://127.0.0.1:2505/health/", timeout=2) as response:
            payload = loads(response.read().decode("utf-8"))
        if isinstance(payload, dict):
            version = payload.get("version")
            if isinstance(version, str) and version:
                return version
    except (OSError, ValueError):
        pass
    return application_version()


def _schedule_worker_cleanup(worker_dir: Path) -> None:
    if os.name != "nt":
        shutil.rmtree(worker_dir, ignore_errors=True)
        return
    escaped = str(worker_dir).replace("'", "''")
    command = f"Start-Sleep -Seconds 2; Remove-Item -LiteralPath '{escaped}' -Recurse -Force"
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _run_update(
    package: Path,
    app_root: Path,
    current_version: str,
    cleanup_dir: Path | None = None,
) -> int:
    initialize_runtime_environment()
    import django

    django.setup()
    try:
        version = perform_update(package, app_root, current_version=current_version)
    except UpdateError as error:
        messagebox.showerror("Cập nhật thất bại", f"UPDATE-002: {error}")
        if cleanup_dir is not None:
            _schedule_worker_cleanup(cleanup_dir)
        return 1
    messagebox.showinfo("Cập nhật hoàn tất", f"Đã cập nhật lên {version}.")
    if cleanup_dir is not None:
        _schedule_worker_cleanup(cleanup_dir)
    return 0


def _launch_external_worker(package: Path, app_root: Path, current_version: str) -> int:
    runtime_paths = ensure_runtime_layout()
    worker_dir = Path(tempfile.mkdtemp(prefix="update-worker-", dir=runtime_paths.rollback))
    worker = worker_dir / "ShopHoaThuanUpdate.exe"
    shutil.copy2(sys.executable, worker)
    subprocess.Popen(
        [
            str(worker),
            "--execute",
            str(package),
            "--app-root",
            str(app_root),
            "--current-version",
            current_version,
            "--cleanup-dir",
            str(worker_dir),
        ],
        cwd=str(worker_dir),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0),
    )
    messagebox.showinfo(
        "Đang cập nhật",
        "Cập nhật đã bắt đầu. Cửa sổ kết quả sẽ hiện ra sau khi service kiểm tra health.",
    )
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--current-version")
    parser.add_argument("--cleanup-dir", type=Path)
    parser.add_argument("package", type=Path, nargs="?")
    args = parser.parse_args()
    if args.execute:
        if args.package is None or args.app_root is None:
            return 1
        return _run_update(
            args.package,
            args.app_root,
            args.current_version or application_version(),
            args.cleanup_dir,
        )

    initialize_runtime_environment()
    package_name = os.getenv("SHOP_UPDATE_PACKAGE", "")
    package = Path(package_name) if package_name else None
    root = tk.Tk()
    root.withdraw()
    if package is None or not package.exists():
        selected = filedialog.askopenfilename(
            title="Chọn gói cập nhật Shop Hoà Thuận",
            filetypes=[("Shop update", "*.zip"), ("Tất cả file", "*.*")],
        )
        if not selected:
            return 1
        package = Path(selected)
    current_version = _installed_version()
    try:
        manifest = validate_update_package(package, current_version)
    except UpdateError as error:
        messagebox.showerror("Không thể cập nhật", f"UPDATE-001: {error}")
        return 1
    if not messagebox.askyesno(
        "Xác nhận cập nhật",
        f"Cập nhật từ {manifest.current_version} lên {manifest.target_version}?\n"
        "Hệ thống sẽ tạo backup trước khi thay đổi.",
    ):
        return 1
    try:
        app_root = _application_root()
        if getattr(sys, "frozen", False):
            return _launch_external_worker(package, app_root, current_version)
        version = perform_update(package, app_root, current_version=current_version)
    except UpdateError as error:
        messagebox.showerror("Cập nhật thất bại", f"UPDATE-002: {error}")
        return 1
    messagebox.showinfo("Cập nhật hoàn tất", f"Đã cập nhật lên {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

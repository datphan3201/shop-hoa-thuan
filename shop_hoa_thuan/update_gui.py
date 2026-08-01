"""Double-click update UI; the transaction itself lives in update_runner."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from apps.core.update import UpdateError, validate_update_package
from shop_hoa_thuan.update_runner import initialize_runtime_environment, perform_update
from shop_hoa_thuan.version import application_version


def main() -> int:
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
    try:
        manifest = validate_update_package(package, application_version())
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
        app_root = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent.parent
        )
        version = perform_update(package, app_root)
    except UpdateError as error:
        messagebox.showerror("Cập nhật thất bại", f"UPDATE-002: {error}")
        return 1
    messagebox.showinfo("Cập nhật hoàn tất", f"Đã cập nhật lên {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

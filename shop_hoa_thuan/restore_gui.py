"""Small native Windows GUI for validated restore with explicit confirmation."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    ensure_runtime_secret,
    production_allowed_hosts,
)


def initialize_runtime_environment() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECRET_KEY", ensure_runtime_secret())
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", ",".join(production_allowed_hosts()))
    ensure_runtime_layout()


def restore_from_gui() -> None:
    backup_name = filedialog.askopenfilename(
        title="Chọn file sao lưu",
        filetypes=[("Shop Hoà Thuận backup", "*.zip")],
    )
    if not backup_name:
        return
    package = Path(backup_name)
    import django

    django.setup()
    from apps.core.backup import BackupError, restore_backup, validate_backup
    from apps.core.operations import maintenance_operation

    try:
        manifest = validate_backup(package)
        if not messagebox.askokcancel(
            "Xác nhận khôi phục",
            "Thao tác này thay thế dữ liệu hiện tại. Bản hiện tại sẽ được backup trước.\n"
            "Bạn có chắc chắn muốn tiếp tục?",
        ):
            return
        confirmation = simpledialog.askstring(
            "Xác nhận mạnh",
            "Nhập chính xác KHÔI PHỤC để tiếp tục:",
            parent=root_window,
        )
        if confirmation != "KHÔI PHỤC":
            messagebox.showwarning("Đã hủy", "Xác nhận không khớp; dữ liệu chưa thay đổi.")
            return
        with maintenance_operation("restore", timeout_seconds=60):
            current_backup = restore_backup(package)
    except (BackupError, OSError, RuntimeError) as error:
        messagebox.showerror("Khôi phục thất bại", f"Dữ liệu chưa được thay đổi an toàn.\n{error}")
        return
    messagebox.showinfo(
        "Khôi phục hoàn tất",
        f"Đã khôi phục phiên bản {manifest.get('application_version', 'không rõ')}.\n"
        f"Backup dự phòng: {current_backup.path}",
    )


root_window: tk.Tk


def main() -> int:
    initialize_runtime_environment()
    global root_window
    root_window = tk.Tk()
    root_window.title("Shop Hoà Thuận - Khôi phục")
    root_window.geometry("500x220")
    root_window.resizable(False, False)
    tk.Label(
        root_window,
        text="Khôi phục dữ liệu Shop Hoà Thuận",
        font=("Segoe UI", 14, "bold"),
    ).pack(pady=(28, 12))
    tk.Button(
        root_window,
        text="Chọn file sao lưu và khôi phục",
        width=30,
        height=2,
        command=restore_from_gui,
    ).pack()
    tk.Label(
        root_window, text="Luôn kiểm tra checksum và tạo backup dự phòng trước khi thay thế."
    ).pack(pady=12)
    root_window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Small native Windows GUI for creating a verified backup."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

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


def create_backup_from_gui() -> None:
    import django

    django.setup()
    from apps.core.backup import create_backup
    from apps.core.operations import maintenance_operation

    try:
        with maintenance_operation("backup", timeout_seconds=60):
            backup = create_backup()
    except Exception as error:
        messagebox.showerror("Sao lưu thất bại", f"Không thể tạo bản sao lưu.\nChi tiết: {error}")
        return
    messagebox.showinfo("Sao lưu hoàn tất", f"Đã tạo và kiểm tra:\n{backup.path}")


def main() -> int:
    initialize_runtime_environment()
    root = tk.Tk()
    root.title("Shop Hoà Thuận - Sao lưu")
    root.geometry("460x180")
    root.resizable(False, False)
    tk.Label(
        root,
        text="Sao lưu dữ liệu Shop Hoà Thuận",
        font=("Segoe UI", 14, "bold"),
    ).pack(pady=(28, 12))
    tk.Button(root, text="Sao lưu ngay", width=24, height=2, command=create_backup_from_gui).pack()
    tk.Label(root, text="Bản sao lưu gồm database, ảnh và manifest kiểm tra.").pack(pady=12)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

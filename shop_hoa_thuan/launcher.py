from __future__ import annotations

import json
import os
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from apps.core.network import server_port
from shop_hoa_thuan.runtime import ensure_runtime_layout

SERVICE_NAME = os.getenv("SHOP_SERVICE_NAME", "ShopHoaThuanServer")
LAUNCHER_ERROR = "SHOP-SERVER-001"


def health_url() -> str:
    return f"http://127.0.0.1:{server_port()}/health/"


def is_healthy() -> bool:
    try:
        with urlopen(health_url(), timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("status") in {"ok", "maintenance"}


def request_service_start() -> bool:
    if os.name != "nt":
        return False
    result = subprocess.run(
        ["sc.exe", "start", SERVICE_NAME],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 or "already running" in result.stdout.lower()


def wait_for_health(timeout_seconds: float = 20) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_healthy():
            return True
        time.sleep(0.5)
    return False


def show_error() -> None:
    """Show a Vietnamese GUI error without ever starting a second server."""
    if os.name != "nt":
        return
    import tkinter.messagebox

    logs = ensure_runtime_layout().logs
    tkinter.messagebox.showerror(
        "Không thể mở Shop Hoà Thuận",
        f"{LAUNCHER_ERROR}: Máy chủ chưa sẵn sàng.\n"
        f"Hãy kiểm tra dịch vụ Windows hoặc nhật ký tại:\n{Path(logs)}",
    )


def main() -> int:
    if is_healthy() or (request_service_start() and wait_for_health()):
        webbrowser.open(health_url().removesuffix("health/"))
        return 0
    show_error()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

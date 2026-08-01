"""Dependency-free health utility used by launcher, installer and updater."""

from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from apps.core.network import server_port


def main() -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    attempts = int(os.getenv("SHOP_HEALTH_ATTEMPTS", "20"))
    url = f"http://127.0.0.1:{server_port()}/health/"
    for _ in range(max(1, attempts)):
        try:
            with urlopen(url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if response.status == 200 and payload.get("status") in {"ok", "maintenance"}:
                return 0
        except (OSError, URLError, ValueError):
            pass
        time.sleep(0.5)
    print("SHOP-HEALTH-001: Máy chủ chưa sẵn sàng.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

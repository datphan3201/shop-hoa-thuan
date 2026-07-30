from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="shop-hoa-thuan-smoke-") as data_directory:
        environment = os.environ.copy()
        environment.update(
            {
                "SHOP_DATA_DIR": data_directory,
                "DJANGO_DEBUG": "false",
                "DJANGO_ALLOWED_HOSTS": "*",
                "SHOP_SERVER_HOST": "127.0.0.1",
                "SHOP_SERVER_PORT": "8876",
            }
        )
        process = subprocess.Popen(
            [sys.executable, "-m", "shop_hoa_thuan.server"],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            for _ in range(40):
                if process.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:8876/health/",
                        timeout=1,
                    ) as response:
                        payload = json.load(response)
                    if response.status == 200 and payload == {
                        "status": "ok",
                        "database": True,
                    }:
                        print("Waitress smoke test: OK")
                        return
                except OSError:
                    time.sleep(0.25)

            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"Waitress không khởi động thành công.\n{output}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()

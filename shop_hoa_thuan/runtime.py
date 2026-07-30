from __future__ import annotations

import os
import secrets
from pathlib import Path


def runtime_data_dir() -> Path:
    configured = os.getenv("SHOP_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt" and os.getenv("PROGRAMDATA"):
        return Path(os.environ["PROGRAMDATA"]) / "Shop Hoa Thuan"
    return Path(__file__).resolve().parent.parent / ".data"


def ensure_runtime_secret() -> str:
    """Load or atomically create the machine-local Django secret."""
    data_dir = runtime_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_path = data_dir / ".secret-key"
    try:
        return secret_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        secret = secrets.token_urlsafe(64)
        try:
            file_descriptor = os.open(
                secret_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            return secret_path.read_text(encoding="utf-8").strip()
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(secret)
        return secret

"""Standalone production migration entry point for installers and updates."""

from __future__ import annotations

import os

from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    ensure_runtime_secret,
    production_allowed_hosts,
)


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECRET_KEY", ensure_runtime_secret())
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", ",".join(production_allowed_hosts()))
    ensure_runtime_layout()

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate_runtime", verbosity=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os

from apps.core.network import server_port
from shop_hoa_thuan.runtime import (
    ensure_runtime_layout,
    ensure_runtime_secret,
    production_allowed_hosts,
)


def main() -> None:
    """Start the packaged Waitress server; migration is an installer utility, never startup."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECRET_KEY", ensure_runtime_secret())
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", ",".join(production_allowed_hosts()))
    ensure_runtime_layout()

    import django
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    from apps.core.operations import OperationBusyError, server_lease
    from shop_hoa_thuan.runner import SchemaIncompatibleError, require_compatible_schema

    django.setup()
    try:
        require_compatible_schema()
    except SchemaIncompatibleError as error:
        raise SystemExit(f"SHOP-SERVER-003: {error}") from error
    lease = server_lease()
    try:
        lease.acquire()
    except OperationBusyError as error:
        raise SystemExit(f"SHOP-SERVER-002: {error}") from error
    application = get_wsgi_application()
    host = os.getenv("SHOP_SERVER_HOST", "0.0.0.0")
    port = server_port()
    try:
        serve(
            application,
            host=host,
            port=port,
            threads=4,
            channel_timeout=120,
            clear_untrusted_proxy_headers=True,
        )
    finally:
        lease.release()


if __name__ == "__main__":
    main()

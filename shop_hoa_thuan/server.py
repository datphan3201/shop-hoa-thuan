from __future__ import annotations

import os

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

    django.setup()
    application = get_wsgi_application()
    host = os.getenv("SHOP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SHOP_SERVER_PORT", "2505"))
    serve(
        application,
        host=host,
        port=port,
        threads=4,
        channel_timeout=120,
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    main()

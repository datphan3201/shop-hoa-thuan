from __future__ import annotations

import os

from shop_hoa_thuan.runtime import ensure_runtime_secret


def main() -> None:
    """Run database preparation and start the packaged Waitress server."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECRET_KEY", ensure_runtime_secret())
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "*")

    import django
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    django.setup()
    call_command("migrate", interactive=False, verbosity=1)
    call_command("seed_data", verbosity=0)

    application = get_wsgi_application()
    host = os.getenv("SHOP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SHOP_SERVER_PORT", "8765"))
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

"""Django settings for Shop Hoà Thuận."""

from __future__ import annotations

import os
from pathlib import Path

from apps.core.logging import SensitiveDataFilter
from shop_hoa_thuan.runtime import ensure_runtime_layout, production_allowed_hosts

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", default=True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret-key")
if not DEBUG and SECRET_KEY == "development-only-secret-key":
    raise RuntimeError("DJANGO_SECRET_KEY bắt buộc khi chạy production.")

ALLOWED_HOSTS = production_allowed_hosts()
RUNTIME_PATHS = ensure_runtime_layout()
DATA_DIR = RUNTIME_PATHS.root

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "apps.core.apps.CoreConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.sales.apps.SalesConfig",
    "apps.reports.apps.ReportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "apps.core.middleware.WriteOperationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "shop_hoa_thuan.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.application_context",
            ],
        },
    },
]

WSGI_APPLICATION = "shop_hoa_thuan.wsgi.application"
ASGI_APPLICATION = "shop_hoa_thuan.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": RUNTIME_PATHS.database,
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
        },
    }
}

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = RUNTIME_PATHS.media
BACKUP_ROOT = RUNTIME_PATHS.backups

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
USE_HTTPS = env_bool("SHOP_USE_HTTPS")
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_SSL_REDIRECT = USE_HTTPS
if USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

_LOG_CATEGORIES = {
    "server": "django.server",
    "security": "django.security",
    "business": "shop.business",
    "backup": "shop.backup",
    "restore": "shop.restore",
    "update": "shop.update",
    "service": "shop.service",
}
_LOG_HANDLERS = {
    name: {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": RUNTIME_PATHS.logs / f"{name}.log",
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 5,
        "formatter": "standard",
        "encoding": "utf-8",
        "filters": ["redact"],
    }
    for name in _LOG_CATEGORIES
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        **_LOG_HANDLERS,
    },
    # Use the class rather than a dotted string so the frozen bundle includes
    # the filter as an explicit import.
    "filters": {"redact": {"()": SensitiveDataFilter}},
    "root": {"handlers": ["console", "server"], "level": "INFO"},
    "loggers": {
        logger_name: {"handlers": ["console", category], "level": "INFO", "propagate": False}
        for category, logger_name in _LOG_CATEGORIES.items()
    },
}

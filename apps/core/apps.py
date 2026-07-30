from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Hệ thống"

    def ready(self) -> None:
        from apps.core import signals  # noqa: F401

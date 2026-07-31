from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.models import ShopSecuritySettings
from apps.core.operations import maintenance_operation


class SchemaIncompatibleError(RuntimeError):
    pass


def schema_is_compatible() -> bool:
    executor = MigrationExecutor(connection)
    return not executor.migration_plan(executor.loader.graph.leaf_nodes())


def require_compatible_schema() -> None:
    if not schema_is_compatible():
        raise SchemaIncompatibleError("Schema chưa tương thích. Hãy chạy migration runner.")


def run_migrations() -> None:
    with maintenance_operation("migration", timeout_seconds=60):
        call_command("migrate", interactive=False, verbosity=1)
        require_compatible_schema()


def run_first_setup(*, username: str, password: str, pin: str) -> None:
    user_model = get_user_model()
    if (
        user_model.objects.exists()
        or ShopSecuritySettings.objects.filter(cost_price_pin_hash__gt="").exists()
    ):
        raise RuntimeError("Hệ thống đã được thiết lập; không chạy first-run lần nữa.")
    with maintenance_operation("first-run"):
        owner = user_model.objects.create_superuser(username=username, password=password)
        owner.is_staff = True
        owner.save(update_fields=["is_staff"])
        ShopSecuritySettings.objects.create(cost_price_pin_hash=make_password(pin))

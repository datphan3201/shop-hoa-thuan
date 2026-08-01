from __future__ import annotations

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

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

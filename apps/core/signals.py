from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite_connection(sender: object, connection: object, **kwargs: object) -> None:
    """Apply durability and integrity pragmas to each SQLite connection."""
    if getattr(connection, "vendor", None) != "sqlite":
        return

    with connection.cursor() as cursor:  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 20000")

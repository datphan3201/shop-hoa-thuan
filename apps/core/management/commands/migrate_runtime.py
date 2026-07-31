from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from shop_hoa_thuan.runner import run_migrations


class Command(BaseCommand):
    help = "Chạy migration production dưới maintenance lock."

    def handle(self, *args: object, **options: object) -> None:
        try:
            run_migrations()
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS("Migration hoàn tất."))

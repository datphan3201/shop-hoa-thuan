from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError

from shop_hoa_thuan.runner import run_first_setup


class Command(BaseCommand):
    help = "Thiết lập tài khoản chủ shop và PIN đúng một lần."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--pin", required=True)

    def handle(self, *args: object, **options: object) -> None:
        try:
            run_first_setup(
                username=str(options["username"]),
                password=str(options["password"]),
                pin=str(options["pin"]),
            )
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS("Thiết lập lần đầu hoàn tất."))

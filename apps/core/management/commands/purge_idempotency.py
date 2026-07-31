from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.core.models import IdempotencyRecord


class Command(BaseCommand):
    help = "Xóa các bản ghi idempotency đã hết thời gian lưu giữ."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Số ngày giữ bản ghi (mặc định: 30).",
        )

    def handle(self, *args: object, **options: object) -> str:
        days = options["days"]
        if not isinstance(days, int) or days < 1:
            raise ValueError("--days phải lớn hơn hoặc bằng 1.")
        deleted, _ = IdempotencyRecord.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=days)
        ).delete()
        message = f"Đã xóa {deleted} bản ghi idempotency hết hạn."
        self.stdout.write(message)
        return message

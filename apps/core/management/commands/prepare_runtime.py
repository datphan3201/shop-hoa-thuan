from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from shop_hoa_thuan.runtime import ensure_runtime_layout, migrate_legacy_layout


class Command(BaseCommand):
    help = "Chuẩn bị cây dữ liệu runtime và chuyển layout cũ an toàn nếu có."

    def handle(self, *args: object, **options: object) -> None:
        paths = ensure_runtime_layout()
        try:
            migrated = migrate_legacy_layout(paths)
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        message = "Đã chuyển layout dữ liệu cũ an toàn." if migrated else "Cây dữ liệu đã sẵn sàng."
        self.stdout.write(self.style.SUCCESS(message))

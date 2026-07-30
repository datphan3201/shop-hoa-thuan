from django.core.management.base import BaseCommand

from apps.catalog.models import Category
from apps.core.models import ShopSecuritySettings

DEFAULT_CATEGORIES = (
    "Áo thun",
    "Áo sơ mi",
    "Áo khoác",
    "Quần jean",
    "Quần short",
    "Váy",
    "Đầm",
    "Đồ bộ",
)


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu an toàn và có thể chạy lại."

    def handle(self, *args: object, **options: object) -> None:
        created_count = 0
        for name in DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            created_count += int(created)

        ShopSecuritySettings.load()
        self.stdout.write(
            self.style.SUCCESS(f"Đã tạo {created_count} loại mặt hàng mới và thiết lập bảo mật.")
        )

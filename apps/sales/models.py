from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class Sale(TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Tiền mặt"
        BANK_TRANSFER = "bank_transfer", "Chuyển khoản"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        COMPLETED = "completed", "Đã hoàn thành"
        CANCELLED = "cancelled", "Đã hủy"

    sale_code = models.CharField("Mã giao dịch", max_length=32, unique=True)
    sold_at = models.DateTimeField("Thời điểm bán", db_index=True)
    subtotal = models.PositiveBigIntegerField("Tổng tiền trước giảm")
    discount_amount = models.PositiveBigIntegerField("Số tiền giảm", default=0)
    final_total = models.PositiveBigIntegerField("Tổng tiền thực tế")
    payment_method = models.CharField(
        "Phương thức thanh toán",
        max_length=20,
        choices=PaymentMethod.choices,
    )
    note = models.TextField("Ghi chú", blank=True)
    status = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        db_index=True,
    )
    cancelled_at = models.DateTimeField("Thời điểm hủy", null=True, blank=True)
    cancellation_reason = models.TextField("Lý do hủy", blank=True)

    class Meta:
        ordering = ("-sold_at", "-id")
        verbose_name = "Giao dịch"
        verbose_name_plural = "Giao dịch"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="sale_subtotal_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_amount__gte=0),
                name="sale_discount_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_amount__lte=models.F("subtotal")),
                name="sale_discount_not_greater_than_subtotal",
            ),
            models.CheckConstraint(
                condition=models.Q(final_total=models.F("subtotal") - models.F("discount_amount")),
                name="sale_final_total_consistent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="completed",
                        cancelled_at__isnull=True,
                        cancellation_reason="",
                    )
                    | models.Q(
                        status="cancelled",
                        cancelled_at__isnull=False,
                    )
                ),
                name="sale_cancellation_state_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "sold_at"), name="sale_status_sold_at_idx"),
            models.Index(fields=("payment_method", "sold_at"), name="sale_payment_sold_at_idx"),
        ]

    def __str__(self) -> str:
        return self.sale_code


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        verbose_name="Giao dịch",
        related_name="items",
        on_delete=models.PROTECT,
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        verbose_name="Biến thể sản phẩm",
        related_name="sale_items",
        on_delete=models.PROTECT,
    )
    product_name_snapshot = models.CharField("Tên sản phẩm", max_length=200)
    category_name_snapshot = models.CharField("Loại mặt hàng", max_length=120)
    size_snapshot = models.CharField("Size", max_length=50)
    color_snapshot = models.CharField("Màu sắc", max_length=120, blank=True)
    sku_snapshot = models.CharField("SKU", max_length=100, blank=True)
    quantity = models.PositiveIntegerField("Số lượng")
    listed_price = models.PositiveBigIntegerField("Giá niêm yết")
    actual_unit_price = models.PositiveBigIntegerField("Giá bán thực tế")
    unit_cost_snapshot = models.PositiveBigIntegerField("Giá vốn tại thời điểm bán")
    line_total = models.PositiveBigIntegerField("Thành tiền")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ("id",)
        verbose_name = "Sản phẩm trong giao dịch"
        verbose_name_plural = "Sản phẩm trong giao dịch"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="sale_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(listed_price__gte=0),
                name="sale_item_listed_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_unit_price__gte=0),
                name="sale_item_actual_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost_snapshot__gte=0),
                name="sale_item_unit_cost_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total=models.F("quantity") * models.F("actual_unit_price")),
                name="sale_item_line_total_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=("sale",), name="sale_item_sale_idx"),
            models.Index(fields=("product_variant",), name="sale_item_variant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sale.sale_code} — {self.product_name_snapshot} {self.size_snapshot}"

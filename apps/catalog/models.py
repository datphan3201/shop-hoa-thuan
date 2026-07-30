from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField("Tên loại mặt hàng", max_length=120)
    description = models.TextField("Mô tả", blank=True)
    active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Loại mặt hàng"
        verbose_name_plural = "Loại mặt hàng"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="category_name_case_insensitive_unique")
        ]

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        verbose_name="Loại mặt hàng",
        related_name="products",
        on_delete=models.PROTECT,
    )
    name = models.CharField("Tên sản phẩm", max_length=200)
    brand = models.CharField("Thương hiệu", max_length=120, blank=True)
    color = models.CharField("Màu sắc", max_length=120, blank=True)
    description = models.TextField("Mô tả", blank=True)
    image = models.ImageField("Ảnh sản phẩm", upload_to="products/%Y/%m/", blank=True)
    active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        indexes = [
            models.Index(fields=("category", "active"), name="product_category_active_idx"),
            models.Index(fields=("name",), name="product_name_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class ProductVariant(TimeStampedModel):
    DEFAULT_SIZES = ("XS", "S", "M", "L", "XL", "XXL", "XXXL", "Free size")

    product = models.ForeignKey(
        Product,
        verbose_name="Sản phẩm",
        related_name="variants",
        on_delete=models.PROTECT,
    )
    size = models.CharField("Size", max_length=50)
    sku = models.CharField("SKU", max_length=100, blank=True, default="")
    cost_price = models.PositiveBigIntegerField("Giá vốn", default=0)
    selling_price = models.PositiveBigIntegerField("Giá bán", default=0)
    quantity = models.PositiveIntegerField("Số lượng", default=0)
    low_stock_threshold = models.PositiveIntegerField("Ngưỡng sắp hết", default=2)
    active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ("product__name", "size")
        verbose_name = "Biến thể sản phẩm"
        verbose_name_plural = "Biến thể sản phẩm"
        constraints = [
            models.UniqueConstraint(
                Lower("size"),
                "product",
                name="variant_product_size_case_insensitive_unique",
            ),
            models.UniqueConstraint(
                Lower("sku"),
                condition=~models.Q(sku=""),
                name="variant_sku_case_insensitive_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(cost_price__gte=0),
                name="variant_cost_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=0),
                name="variant_selling_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="variant_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(low_stock_threshold__gte=0),
                name="variant_low_stock_threshold_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=("active", "quantity"), name="variant_active_quantity_idx"),
            models.Index(fields=("size",), name="variant_size_idx"),
            models.Index(fields=("sku",), name="variant_sku_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        self.size = self.size.strip()
        self.sku = self.sku.strip()
        if not self.size:
            raise ValidationError({"size": "Size là thông tin bắt buộc."})

    @property
    def stock_status(self) -> str:
        if self.quantity == 0:
            return "out_of_stock"
        if self.quantity <= self.low_stock_threshold:
            return "low_stock"
        return "in_stock"

    def __str__(self) -> str:
        return f"{self.product.name} — {self.size}"


class InventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        INITIAL = "initial", "Tồn kho ban đầu"
        IMPORT = "import", "Nhập thêm hàng"
        SALE = "sale", "Bán hàng"
        SALE_RETURN = "sale_return", "Hoàn tồn khi hủy giao dịch"
        ADJUSTMENT = "adjustment", "Điều chỉnh thủ công"

    product_variant = models.ForeignKey(
        ProductVariant,
        verbose_name="Biến thể sản phẩm",
        related_name="inventory_movements",
        on_delete=models.PROTECT,
    )
    movement_type = models.CharField(
        "Loại biến động",
        max_length=20,
        choices=MovementType.choices,
    )
    quantity_before = models.PositiveIntegerField("Số lượng trước")
    quantity_change = models.IntegerField("Số lượng thay đổi")
    quantity_after = models.PositiveIntegerField("Số lượng sau")
    reference_type = models.CharField("Loại tham chiếu", max_length=50, blank=True)
    reference_id = models.CharField("Mã tham chiếu", max_length=100, blank=True)
    note = models.TextField("Ghi chú")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = "Biến động tồn kho"
        verbose_name_plural = "Biến động tồn kho"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_before__gte=0),
                name="movement_quantity_before_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_after__gte=0),
                name="movement_quantity_after_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantity_after=models.F("quantity_before") + models.F("quantity_change")
                ),
                name="movement_quantities_consistent",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product_variant", "-created_at"),
                name="movement_variant_created_idx",
            ),
            models.Index(
                fields=("reference_type", "reference_id"),
                name="movement_reference_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_variant} ({self.quantity_change:+d})"

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import sleep

from django.db import OperationalError, transaction
from django.utils import timezone

from apps.catalog.models import InventoryMovement, ProductVariant
from apps.catalog.services import InsufficientStockError, adjust_inventory
from apps.sales.models import Sale, SaleItem


class SaleValidationError(ValueError):
    pass


class SaleAlreadyCancelledError(SaleValidationError):
    pass


@dataclass(frozen=True)
class SaleLineInput:
    variant_id: int
    quantity: int
    actual_unit_price: int


def _retry_sqlite_lock[ResultT](operation: Callable[[], ResultT]) -> ResultT:
    max_attempts = 6
    for attempt in range(max_attempts):
        try:
            return operation()
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == max_attempts - 1:
                raise
            sleep(0.05 * (attempt + 1))
    raise RuntimeError("Không thể hoàn tất thao tác database.")


def _generate_sale_code(sold_at: datetime) -> str:
    local_sold_at = timezone.localtime(sold_at)
    return f"BH-{local_sold_at:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def complete_sale(
    *,
    lines: list[SaleLineInput],
    discount_amount: int,
    payment_method: str,
    note: str = "",
    sold_at: datetime | None = None,
) -> Sale:
    def operation() -> Sale:
        return _complete_sale_once(
            lines=lines,
            discount_amount=discount_amount,
            payment_method=payment_method,
            note=note,
            sold_at=sold_at,
        )

    return _retry_sqlite_lock(operation)


@transaction.atomic
def _complete_sale_once(
    *,
    lines: list[SaleLineInput],
    discount_amount: int,
    payment_method: str,
    note: str = "",
    sold_at: datetime | None = None,
) -> Sale:
    if not lines:
        raise SaleValidationError("Giao dịch phải có ít nhất một sản phẩm.")
    if discount_amount < 0:
        raise SaleValidationError("Giảm giá không được âm.")
    if payment_method not in Sale.PaymentMethod.values:
        raise SaleValidationError("Phương thức thanh toán không hợp lệ.")

    variant_ids = [line.variant_id for line in lines]
    if len(variant_ids) != len(set(variant_ids)):
        raise SaleValidationError("Không được thêm trùng một size trong giao dịch.")
    if any(line.quantity <= 0 for line in lines):
        raise SaleValidationError("Số lượng bán phải là số nguyên dương.")
    if any(line.actual_unit_price < 0 for line in lines):
        raise SaleValidationError("Giá bán thực tế không được âm.")

    variants = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update()
        .select_related("product", "product__category")
        .filter(pk__in=variant_ids)
    }
    if len(variants) != len(lines):
        raise SaleValidationError("Một hoặc nhiều size không còn tồn tại.")

    subtotal = sum(line.quantity * line.actual_unit_price for line in lines)
    if discount_amount > subtotal:
        raise SaleValidationError("Giảm giá không được lớn hơn tổng tiền.")

    sold_at = sold_at or timezone.now()
    sale = Sale.objects.create(
        sale_code=_generate_sale_code(sold_at),
        sold_at=sold_at,
        subtotal=subtotal,
        discount_amount=discount_amount,
        final_total=subtotal - discount_amount,
        payment_method=payment_method,
        note=note.strip(),
        status=Sale.Status.COMPLETED,
    )

    for line in lines:
        variant = variants[line.variant_id]
        if not variant.active or not variant.product.active:
            raise SaleValidationError("Sản phẩm hoặc size đã ngừng hoạt động.")
        if variant.quantity < line.quantity:
            raise InsufficientStockError(
                f"{variant.product.name} — {variant.size} không đủ tồn kho."
            )
        SaleItem.objects.create(
            sale=sale,
            product_variant=variant,
            product_name_snapshot=variant.product.name,
            category_name_snapshot=variant.product.category.name,
            size_snapshot=variant.size,
            color_snapshot=variant.product.color,
            sku_snapshot=variant.sku,
            quantity=line.quantity,
            listed_price=variant.selling_price,
            actual_unit_price=line.actual_unit_price,
            unit_cost_snapshot=variant.cost_price,
            line_total=line.quantity * line.actual_unit_price,
        )
        adjust_inventory(
            variant_id=variant.pk,
            operation="subtract",
            quantity=line.quantity,
            reason=f"Bán hàng {sale.sale_code}",
            movement_type=InventoryMovement.MovementType.SALE,
            reference_type="sale",
            reference_id=str(sale.pk),
        )

    return sale


def cancel_sale(*, sale_id: int, reason: str) -> Sale:
    def operation() -> Sale:
        return _cancel_sale_once(sale_id=sale_id, reason=reason)

    return _retry_sqlite_lock(operation)


@transaction.atomic
def _cancel_sale_once(*, sale_id: int, reason: str) -> Sale:
    reason = reason.strip()
    if not reason:
        raise SaleValidationError("Bắt buộc nhập lý do hủy giao dịch.")

    sale = Sale.objects.select_for_update().get(pk=sale_id)
    if sale.status == Sale.Status.CANCELLED:
        raise SaleAlreadyCancelledError("Giao dịch đã được hủy trước đó.")

    items = list(sale.items.select_related("product_variant"))
    for item in items:
        adjust_inventory(
            variant_id=item.product_variant_id,
            operation="add",
            quantity=item.quantity,
            reason=f"Hoàn tồn do hủy {sale.sale_code}: {reason}",
            movement_type=InventoryMovement.MovementType.SALE_RETURN,
            reference_type="sale",
            reference_id=str(sale.pk),
        )

    sale.status = Sale.Status.CANCELLED
    sale.cancelled_at = timezone.now()
    sale.cancellation_reason = reason
    sale.save(update_fields=("status", "cancelled_at", "cancellation_reason", "updated_at"))
    return sale

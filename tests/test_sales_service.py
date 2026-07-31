from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.catalog.services import InsufficientStockError
from apps.sales.models import Sale, SaleItem
from apps.sales.services import (
    SaleAlreadyCancelledError,
    SaleLineInput,
    SaleValidationError,
    cancel_sale,
    complete_sale,
)


@pytest.fixture
def sale_variants(db: None) -> tuple[ProductVariant, ProductVariant]:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(
        category=category,
        name="Áo thun Basic",
        color="Trắng",
    )
    size_s = ProductVariant.objects.create(
        product=product,
        size="S",
        sku="ATB-S",
        cost_price=100_000,
        selling_price=180_000,
        quantity=3,
    )
    size_m = ProductVariant.objects.create(
        product=product,
        size="M",
        sku="ATB-M",
        cost_price=105_000,
        selling_price=190_000,
        quantity=2,
    )
    return size_s, size_m


@pytest.mark.django_db
def test_complete_sale_calculates_snapshots_and_decrements_inventory(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, size_m = sale_variants

    sale = complete_sale(
        lines=[
            SaleLineInput(size_s.pk, 2, 170_000),
            SaleLineInput(size_m.pk, 1, 185_000),
        ],
        discount_amount=15_000,
        payment_method=Sale.PaymentMethod.CASH,
        note="Khách quen",
    )

    assert sale.subtotal == 525_000
    assert sale.final_total == 510_000
    assert sale.sale_code.startswith("BH-")
    assert SaleItem.objects.filter(sale=sale).count() == 2
    first_item = sale.items.get(product_variant=size_s)
    assert first_item.product_name_snapshot == "Áo thun Basic"
    assert first_item.category_name_snapshot == "Áo thun"
    assert first_item.color_snapshot == "Trắng"
    assert first_item.listed_price == 180_000
    assert first_item.actual_unit_price == 170_000
    assert first_item.unit_cost_snapshot == 100_000
    assert first_item.line_total == 340_000
    size_s.refresh_from_db()
    size_m.refresh_from_db()
    assert (size_s.quantity, size_m.quantity) == (1, 1)
    assert (
        InventoryMovement.objects.filter(
            movement_type=InventoryMovement.MovementType.SALE,
            reference_id=str(sale.pk),
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_sale_rolls_back_everything_when_any_line_is_out_of_stock(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, size_m = sale_variants

    with pytest.raises(InsufficientStockError):
        complete_sale(
            lines=[
                SaleLineInput(size_s.pk, 1, 180_000),
                SaleLineInput(size_m.pk, 99, 190_000),
            ],
            discount_amount=0,
            payment_method=Sale.PaymentMethod.CASH,
        )

    size_s.refresh_from_db()
    assert size_s.quantity == 3
    assert Sale.objects.count() == 0
    assert SaleItem.objects.count() == 0
    assert InventoryMovement.objects.count() == 0


@pytest.mark.django_db
def test_sale_rejects_invalid_totals_and_empty_lines() -> None:
    with pytest.raises(SaleValidationError, match="ít nhất"):
        complete_sale(
            lines=[],
            discount_amount=0,
            payment_method=Sale.PaymentMethod.CASH,
        )


@pytest.mark.django_db
def test_sale_rejects_duplicate_variant_and_invalid_line_values(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, _ = sale_variants
    with pytest.raises(SaleValidationError, match="trùng"):
        complete_sale(
            lines=[
                SaleLineInput(size_s.pk, 1, 180_000),
                SaleLineInput(size_s.pk, 1, 170_000),
            ],
            discount_amount=0,
            payment_method=Sale.PaymentMethod.CASH,
        )
    with pytest.raises(SaleValidationError, match="số nguyên dương"):
        complete_sale(
            lines=[SaleLineInput(size_s.pk, 0, 180_000)],
            discount_amount=0,
            payment_method=Sale.PaymentMethod.CASH,
        )
    with pytest.raises(SaleValidationError, match="không được âm"):
        complete_sale(
            lines=[SaleLineInput(size_s.pk, 1, -1)],
            discount_amount=0,
            payment_method=Sale.PaymentMethod.CASH,
        )

    assert Sale.objects.count() == 0


@pytest.mark.django_db
def test_sale_rejects_discount_greater_than_server_subtotal(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, _ = sale_variants

    with pytest.raises(SaleValidationError, match="lớn hơn tổng tiền"):
        complete_sale(
            lines=[SaleLineInput(size_s.pk, 1, 180_000)],
            discount_amount=180_001,
            payment_method=Sale.PaymentMethod.CASH,
        )

    size_s.refresh_from_db()
    assert size_s.quantity == 3
    assert Sale.objects.count() == 0


@pytest.mark.django_db
def test_cancel_sale_restores_inventory_exactly_once(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, _ = sale_variants
    sale = complete_sale(
        lines=[SaleLineInput(size_s.pk, 2, 170_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.BANK_TRANSFER,
    )

    cancelled = cancel_sale(sale_id=sale.pk, reason="Khách trả lại hàng")

    assert cancelled.status == Sale.Status.CANCELLED
    assert cancelled.cancelled_at is not None
    size_s.refresh_from_db()
    assert size_s.quantity == 3
    assert (
        InventoryMovement.objects.filter(
            movement_type=InventoryMovement.MovementType.SALE_RETURN,
            reference_id=str(sale.pk),
        ).count()
        == 1
    )

    with pytest.raises(SaleAlreadyCancelledError):
        cancel_sale(sale_id=sale.pk, reason="Hủy lần hai")
    size_s.refresh_from_db()
    assert size_s.quantity == 3


@pytest.mark.django_db
def test_historical_snapshot_does_not_change_after_product_price_changes(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, _ = sale_variants
    sale = complete_sale(
        lines=[SaleLineInput(size_s.pk, 1, 170_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.OTHER,
    )
    size_s.product.name = "Tên mới"
    size_s.product.save(update_fields=["name", "updated_at"])
    size_s.selling_price = 999_000
    size_s.cost_price = 888_000
    size_s.save(update_fields=["selling_price", "cost_price", "updated_at"])

    item = sale.items.get()
    assert item.product_name_snapshot == "Áo thun Basic"
    assert item.listed_price == 180_000
    assert item.unit_cost_snapshot == 100_000


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_sales_cannot_oversell(
    sale_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    size_s, _ = sale_variants
    ProductVariant.objects.filter(pk=size_s.pk).update(quantity=1)
    barrier = Barrier(2)

    def attempt_sale() -> str:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            complete_sale(
                lines=[SaleLineInput(size_s.pk, 1, 180_000)],
                discount_amount=0,
                payment_method=Sale.PaymentMethod.CASH,
            )
        except InsufficientStockError:
            return "insufficient"
        finally:
            close_old_connections()
        return "completed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_sale(), range(2)))

    size_s.refresh_from_db()
    assert sorted(results) == ["completed", "insufficient"]
    assert size_s.quantity == 0
    assert Sale.objects.filter(status=Sale.Status.COMPLETED).count() == 1

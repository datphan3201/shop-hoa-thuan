from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.core.security import UNLOCKED_UNTIL_KEY
from apps.sales.models import Sale
from apps.sales.services import SaleLineInput, complete_sale


@pytest.fixture
def sales_owner_client(db: None, client: Client) -> Client:
    owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(owner)
    return client


@pytest.fixture
def sales_variant(db: None) -> ProductVariant:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(
        category=category,
        name="Áo thun Basic",
        color="Trắng",
    )
    return ProductVariant.objects.create(
        product=product,
        size="M",
        sku="ATB-M",
        cost_price=123_456,
        selling_price=234_567,
        quantity=3,
        low_stock_threshold=1,
    )


def _sale_payload(variant: ProductVariant, *, quantity: int = 1) -> dict[str, str]:
    return {
        "lines_json": json.dumps(
            [
                {
                    "variant_id": variant.pk,
                    "quantity": quantity,
                    "actual_unit_price": 220_000,
                }
            ]
        ),
        "discount_amount": "10000",
        "payment_method": Sale.PaymentMethod.CASH,
        "note": "Khách quen",
    }


@pytest.mark.django_db
def test_sale_create_view_commits_server_totals_and_inventory(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    response = sales_owner_client.post(reverse("sale-create"), _sale_payload(sales_variant))

    sale = Sale.objects.get()
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("sale-detail", args=[sale.pk])
    assert sale.subtotal == 220_000
    assert sale.discount_amount == 10_000
    assert sale.final_total == 210_000
    sales_variant.refresh_from_db()
    assert sales_variant.quantity == 2
    assert InventoryMovement.objects.filter(
        movement_type=InventoryMovement.MovementType.SALE,
        reference_id=str(sale.pk),
    ).exists()


@pytest.mark.django_db
def test_sale_create_view_rejects_out_of_stock_without_partial_sale(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    response = sales_owner_client.post(
        reverse("sale-create"),
        _sale_payload(sales_variant, quantity=99),
    )

    assert response.status_code == 200
    assert "không đủ tồn kho" in response.content.decode()
    assert Sale.objects.count() == 0
    sales_variant.refresh_from_db()
    assert sales_variant.quantity == 3


@pytest.mark.django_db
def test_locked_sale_search_does_not_return_cost_price(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    response = sales_owner_client.get(reverse("sale-variant-search"), {"q": "ATB-M"})
    content = response.content.decode()

    assert response.status_code == 200
    assert "data-cost-price" not in content
    assert "123.456" not in content
    assert "234.567 ₫" in content


@pytest.mark.django_db
def test_unlocked_sale_search_can_return_cost_for_below_cost_warning(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    session = sales_owner_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()

    response = sales_owner_client.get(reverse("sale-variant-search"), {"q": "ATB-M"})

    assert response.status_code == 200
    assert 'data-cost-price="123456"' in response.content.decode()


@pytest.mark.django_db
def test_receipt_never_contains_cost_or_profit(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    sales_owner_client.post(reverse("sale-create"), _sale_payload(sales_variant))
    sale = Sale.objects.get()
    session = sales_owner_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()

    response = sales_owner_client.get(reverse("sale-receipt", args=[sale.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "123.456" not in content
    assert "Giá vốn" not in content
    assert "Lợi nhuận" not in content


@pytest.mark.django_db
def test_cancel_view_requires_reason_and_restores_only_once(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    sales_owner_client.post(reverse("sale-create"), _sale_payload(sales_variant, quantity=2))
    sale = Sale.objects.get()

    invalid_response = sales_owner_client.post(
        reverse("sale-cancel", args=[sale.pk]), {"reason": ""}
    )
    assert invalid_response.status_code == 400

    response = sales_owner_client.post(
        reverse("sale-cancel", args=[sale.pk]),
        {"reason": "Khách trả lại hàng"},
    )
    assert response.status_code == 302
    sales_variant.refresh_from_db()
    assert sales_variant.quantity == 3

    second_response = sales_owner_client.post(
        reverse("sale-cancel", args=[sale.pk]),
        {"reason": "Thử hủy lần hai"},
    )
    assert second_response.status_code == 302
    sales_variant.refresh_from_db()
    assert sales_variant.quantity == 3
    assert (
        InventoryMovement.objects.filter(
            movement_type=InventoryMovement.MovementType.SALE_RETURN,
            reference_id=str(sale.pk),
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_sale_list_filters_by_code_payment_and_status(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    sales_owner_client.post(reverse("sale-create"), _sale_payload(sales_variant))
    sale = Sale.objects.get()

    matching = sales_owner_client.get(
        reverse("sale-list"),
        {
            "q": sale.sale_code,
            "payment_method": Sale.PaymentMethod.CASH,
            "status": Sale.Status.COMPLETED,
        },
    )
    excluded = sales_owner_client.get(
        reverse("sale-list"),
        {"payment_method": Sale.PaymentMethod.BANK_TRANSFER},
    )

    assert sale.sale_code in matching.content.decode()
    assert sale.sale_code not in excluded.content.decode()


@pytest.mark.django_db
def test_sale_list_date_filter_uses_ho_chi_minh_timezone(
    sales_owner_client: Client,
    sales_variant: ProductVariant,
) -> None:
    local_july_31 = complete_sale(
        lines=[SaleLineInput(sales_variant.pk, 1, 220_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 30, 17, 30, tzinfo=UTC),
    )
    local_august_1 = complete_sale(
        lines=[SaleLineInput(sales_variant.pk, 1, 220_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 31, 17, 30, tzinfo=UTC),
    )

    response = sales_owner_client.get(
        reverse("sale-list"),
        {"date_from": "2026-07-31", "date_to": "2026-07-31"},
    )
    content = response.content.decode()

    assert local_july_31.sale_code in content
    assert local_august_1.sale_code not in content

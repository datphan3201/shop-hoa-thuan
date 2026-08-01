from __future__ import annotations

import json

import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariant
from apps.sales.models import Sale


@pytest.mark.django_db
def test_lan_browser_can_complete_then_cancel_a_sale_and_report_excludes_it(client: Client) -> None:
    """Smoke test the everyday no-account workflow across the real HTTP views."""
    client.post(
        reverse("security-action"),
        {"action": "setup", "new_pin": "2468", "confirm_pin": "2468"},
    )
    category_response = client.post(
        reverse("category-create"),
        {"name": "Áo thun", "description": "", "active": "on"},
    )
    assert category_response.status_code == 302

    category = Category.objects.get(name="Áo thun")
    product_response = client.post(
        reverse("product-create"),
        {
            "category": category.pk,
            "name": "Áo cơ bản",
            "brand": "",
            "color": "Trắng",
            "description": "",
            "active": "on",
            "variants-TOTAL_FORMS": "1",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "1",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-size": "M",
            "variants-0-sku": "AO-M",
            "variants-0-cost_price": "100000",
            "variants-0-selling_price": "200000",
            "variants-0-initial_quantity": "2",
            "variants-0-low_stock_threshold": "1",
            "variants-0-active": "on",
        },
    )
    assert product_response.status_code == 302
    product = Product.objects.get(name="Áo cơ bản")
    variant = ProductVariant.objects.get(product=product, size="M")

    sale_response = client.post(
        reverse("sale-create"),
        {
            "lines_json": json.dumps(
                [{"variant_id": variant.pk, "quantity": 1, "actual_unit_price": 180_000}]
            ),
            "discount_amount": "10_000",
            "payment_method": Sale.PaymentMethod.CASH,
            "note": "Khách quen",
        },
    )
    assert sale_response.status_code == 302
    sale = Sale.objects.get()
    variant.refresh_from_db()
    assert sale.final_total == 170_000
    assert variant.quantity == 1
    assert "170.000 ₫" in client.get(reverse("report-overview")).content.decode()

    cancel_response = client.post(
        reverse("sale-cancel", args=[sale.pk]),
        {"reason": "Khách đổi ý"},
    )
    assert cancel_response.status_code == 302
    variant.refresh_from_db()
    sale.refresh_from_db()
    assert variant.quantity == 2
    assert sale.status == Sale.Status.CANCELLED
    assert "170.000 ₫" not in client.get(reverse("report-overview")).content.decode()

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariant


@pytest.mark.django_db
def test_primary_routes_keep_mobile_navigation_without_login(client: Client) -> None:
    category = Category.objects.create(name="Áo")
    product = Product.objects.create(category=category, name="Áo mobile")
    variant = ProductVariant.objects.create(
        product=product,
        size="M",
        selling_price=100_000,
        cost_price=50_000,
        quantity=2,
    )
    routes = [
        reverse("dashboard"),
        reverse("product-list"),
        reverse("product-detail", args=[product.pk]),
        reverse("inventory-list"),
        reverse("inventory-adjust", args=[variant.pk]),
        reverse("sale-list"),
        reverse("sale-create"),
        reverse("report-overview"),
        reverse("security-settings"),
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, route
        assert 'class="mobile-bottom-nav d-lg-none"' in response.content.decode()


def test_pwa_manifest_and_worker_only_cover_safe_static_gets() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    worker = (root / "static" / "service-worker.js").read_text(encoding="utf-8")

    assert manifest["name"] == "Shop Hoà Thuận"
    assert manifest["short_name"] == "Hoà Thuận"
    assert manifest["display"] == "standalone"
    assert {item["name"] for item in manifest["shortcuts"]} == {
        "Bán hàng",
        "Sản phẩm",
        "Tồn kho",
    }
    assert 'event.request.method !== "GET"' in worker
    assert 'url.pathname.startsWith("/static/")' in worker
    assert "clients.claim" in worker
    assert "/sales/" not in worker
    assert "/media/" not in worker

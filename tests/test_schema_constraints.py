from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.core.models import ShopSecuritySettings


@pytest.mark.django_db
def test_category_name_is_unique_ignoring_case() -> None:
    Category.objects.create(name="Áo thun")

    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(name="ÁO THUN")


@pytest.mark.django_db
def test_product_size_is_unique_ignoring_case() -> None:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun Basic")
    ProductVariant.objects.create(product=product, size="M")

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariant.objects.create(product=product, size="m")


@pytest.mark.django_db
def test_sku_is_unique_ignoring_case_but_blank_is_allowed() -> None:
    category = Category.objects.create(name="Áo thun")
    first = Product.objects.create(category=category, name="Sản phẩm 1")
    second = Product.objects.create(category=category, name="Sản phẩm 2")
    ProductVariant.objects.create(product=first, size="S", sku="")
    ProductVariant.objects.create(product=first, size="M", sku="SKU-001")
    ProductVariant.objects.create(product=second, size="L", sku="")

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariant.objects.create(product=second, size="XL", sku="sku-001")


@pytest.mark.django_db
def test_inventory_movement_quantities_must_be_consistent() -> None:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun Basic")
    variant = ProductVariant.objects.create(product=product, size="S")

    with pytest.raises(IntegrityError), transaction.atomic():
        InventoryMovement.objects.create(
            product_variant=variant,
            movement_type=InventoryMovement.MovementType.IMPORT,
            quantity_before=2,
            quantity_change=3,
            quantity_after=4,
            note="Dữ liệu không hợp lệ",
        )


@pytest.mark.django_db
def test_security_settings_is_singleton() -> None:
    first = ShopSecuritySettings.load()
    second = ShopSecuritySettings(cost_price_lock_timeout_minutes=20)
    second.save()

    assert first.pk == 1
    assert second.pk == 1
    assert ShopSecuritySettings.objects.count() == 1
    assert ShopSecuritySettings.objects.get().cost_price_lock_timeout_minutes == 20

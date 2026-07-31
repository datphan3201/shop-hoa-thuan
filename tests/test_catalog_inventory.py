from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from apps.catalog.forms import ProductForm
from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.catalog.services import InsufficientStockError, adjust_inventory
from apps.core.security import UNLOCKED_UNTIL_KEY


@pytest.fixture
def owner_client(db: None, client: Client) -> Client:
    owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(owner)
    session = client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()
    return client


@pytest.fixture
def variant(db: None) -> ProductVariant:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun Basic")
    return ProductVariant.objects.create(
        product=product,
        size="M",
        cost_price=100_000,
        selling_price=180_000,
        quantity=3,
        low_stock_threshold=2,
    )


@pytest.mark.django_db
def test_inventory_add_subtract_and_set_always_create_movements(
    variant: ProductVariant,
) -> None:
    adjust_inventory(
        variant_id=variant.pk,
        operation="add",
        quantity=4,
        reason="Nhập lô mới",
        movement_type=InventoryMovement.MovementType.IMPORT,
    )
    adjust_inventory(
        variant_id=variant.pk,
        operation="subtract",
        quantity=2,
        reason="Điều chỉnh hàng lỗi",
    )
    result = adjust_inventory(
        variant_id=variant.pk,
        operation="set",
        quantity=8,
        reason="Kiểm kê cuối ngày",
    )

    assert result.quantity == 8
    assert list(
        variant.inventory_movements.order_by("id").values_list(
            "quantity_before", "quantity_change", "quantity_after"
        )
    ) == [(3, 4, 7), (7, -2, 5), (5, 3, 8)]


@pytest.mark.django_db
def test_inventory_rejects_negative_stock_without_partial_history(
    variant: ProductVariant,
) -> None:
    with pytest.raises(InsufficientStockError):
        adjust_inventory(
            variant_id=variant.pk,
            operation="subtract",
            quantity=4,
            reason="Không đủ hàng",
        )

    variant.refresh_from_db()
    assert variant.quantity == 3
    assert variant.inventory_movements.count() == 0


@pytest.mark.django_db
def test_inventory_requires_reason(variant: ProductVariant) -> None:
    with pytest.raises(ValueError, match="Bắt buộc"):
        adjust_inventory(
            variant_id=variant.pk,
            operation="add",
            quantity=1,
            reason=" ",
        )


@pytest.mark.django_db
def test_inventory_adjustment_idempotency_replays_single_movement(
    owner_client: Client, variant: ProductVariant
) -> None:
    payload = {"operation": "add", "quantity": "4", "reason": "Nhập lại"}
    headers = {"Idempotency-Key": "mobile-inventory-001"}

    first = owner_client.post(
        reverse("inventory-adjust", args=[variant.pk]), payload, headers=headers
    )
    replay = owner_client.post(
        reverse("inventory-adjust", args=[variant.pk]), payload, headers=headers
    )
    conflict = owner_client.post(
        reverse("inventory-adjust", args=[variant.pk]),
        {**payload, "quantity": "5"},
        headers=headers,
    )

    assert first.status_code == 302
    assert replay.status_code == 302
    assert conflict.status_code == 200
    variant.refresh_from_db()
    assert variant.quantity == 7
    assert variant.inventory_movements.count() == 1
    assert "không khớp" in conflict.content.decode()


@pytest.mark.django_db
def test_stock_status_uses_threshold_and_zero(variant: ProductVariant) -> None:
    assert variant.stock_status == "in_stock"
    variant.quantity = 2
    assert variant.stock_status == "low_stock"
    variant.quantity = 0
    assert variant.stock_status == "out_of_stock"


@pytest.mark.django_db
def test_create_product_with_multiple_sizes_creates_initial_history(
    owner_client: Client,
) -> None:
    category = Category.objects.create(name="Áo thun")
    response = owner_client.post(
        reverse("product-create"),
        {
            "category": category.pk,
            "name": "Áo thun Basic",
            "brand": "",
            "color": "Trắng",
            "description": "",
            "active": "on",
            "variants-TOTAL_FORMS": "2",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "1",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-size": "S",
            "variants-0-sku": "ATB-S",
            "variants-0-cost_price": "100000",
            "variants-0-selling_price": "180000",
            "variants-0-initial_quantity": "3",
            "variants-0-low_stock_threshold": "2",
            "variants-0-active": "on",
            "variants-1-size": "M",
            "variants-1-sku": "ATB-M",
            "variants-1-cost_price": "100000",
            "variants-1-selling_price": "180000",
            "variants-1-initial_quantity": "0",
            "variants-1-low_stock_threshold": "2",
            "variants-1-active": "on",
        },
    )

    product = Product.objects.get(name="Áo thun Basic")
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("product-detail", args=[product.pk])
    assert list(product.variants.order_by("size").values_list("size", "quantity")) == [
        ("M", 0),
        ("S", 3),
    ]
    assert (
        InventoryMovement.objects.filter(
            product_variant__product=product,
            movement_type=InventoryMovement.MovementType.INITIAL,
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_product_create_idempotency_does_not_duplicate_product_or_inventory(
    owner_client: Client,
) -> None:
    category = Category.objects.create(name="Quần")
    payload = {
        "category": category.pk,
        "name": "Quần mobile",
        "brand": "",
        "color": "Xanh",
        "description": "",
        "active": "on",
        "variants-TOTAL_FORMS": "1",
        "variants-INITIAL_FORMS": "0",
        "variants-MIN_NUM_FORMS": "1",
        "variants-MAX_NUM_FORMS": "1000",
        "variants-0-size": "L",
        "variants-0-sku": "QUAN-L",
        "variants-0-cost_price": "100000",
        "variants-0-selling_price": "200000",
        "variants-0-initial_quantity": "2",
        "variants-0-low_stock_threshold": "1",
        "variants-0-active": "on",
    }
    headers = {"Idempotency-Key": "product-create-001"}

    first = owner_client.post(reverse("product-create"), payload, headers=headers)
    replay = owner_client.post(reverse("product-create"), payload, headers=headers)

    assert first.status_code == 302
    assert replay.status_code == 302
    assert first.headers["Location"] == replay.headers["Location"]
    assert Product.objects.filter(name="Quần mobile").count() == 1
    assert (
        InventoryMovement.objects.filter(
            movement_type=InventoryMovement.MovementType.INITIAL
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_product_form_rejects_duplicate_sizes_ignoring_case(owner_client: Client) -> None:
    category = Category.objects.create(name="Áo thun")
    common = {
        "category": category.pk,
        "name": "Áo thun Basic",
        "active": "on",
        "variants-TOTAL_FORMS": "2",
        "variants-INITIAL_FORMS": "0",
        "variants-MIN_NUM_FORMS": "1",
        "variants-MAX_NUM_FORMS": "1000",
    }
    for index, size in enumerate(("M", "m")):
        common.update(
            {
                f"variants-{index}-size": size,
                f"variants-{index}-sku": "",
                f"variants-{index}-cost_price": "100000",
                f"variants-{index}-selling_price": "180000",
                f"variants-{index}-initial_quantity": "1",
                f"variants-{index}-low_stock_threshold": "2",
                f"variants-{index}-active": "on",
            }
        )

    response = owner_client.post(reverse("product-create"), common)

    assert response.status_code == 200
    assert "Không được nhập hai biến thể cùng size." in response.content.decode()
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_uploaded_image_is_resized_and_thumbnail_created(
    owner_client: Client,
    tmp_path: Path,
) -> None:
    category = Category.objects.create(name="Váy")
    image_buffer = BytesIO()
    Image.new("RGB", (2200, 1800), color=(170, 70, 50)).save(image_buffer, format="JPEG")
    upload = SimpleUploadedFile(
        "large.jpg",
        image_buffer.getvalue(),
        content_type="image/jpeg",
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        response = owner_client.post(
            reverse("product-create"),
            {
                "category": category.pk,
                "name": "Váy hoa",
                "color": "Đỏ",
                "image": upload,
                "active": "on",
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "1",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-size": "Free size",
                "variants-0-sku": "VAY-HOA",
                "variants-0-cost_price": "150000",
                "variants-0-selling_price": "290000",
                "variants-0-initial_quantity": "2",
                "variants-0-low_stock_threshold": "1",
                "variants-0-active": "on",
            },
        )
        product = Product.objects.get(name="Váy hoa")
        with Image.open(product.image.path) as resized:
            assert max(resized.size) <= 1600
        with Image.open(product.thumbnail.path) as thumbnail:
            assert max(thumbnail.size) <= 360

    assert response.status_code == 302


@pytest.mark.django_db
def test_product_upload_rejects_file_that_only_claims_to_be_an_image(
    owner_client: Client,
) -> None:
    category = Category.objects.create(name="Nón")
    upload = SimpleUploadedFile("fake.jpg", b"not a JPEG", content_type="image/jpeg")
    response = owner_client.post(
        reverse("product-create"),
        {
            "category": category.pk,
            "name": "Nón bảo hiểm",
            "image": upload,
            "active": "on",
            "variants-TOTAL_FORMS": "1",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "1",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-size": "M",
            "variants-0-sku": "NON-M",
            "variants-0-cost_price": "100000",
            "variants-0-selling_price": "180000",
            "variants-0-initial_quantity": "1",
            "variants-0-low_stock_threshold": "1",
            "variants-0-active": "on",
        },
    )

    assert response.status_code == 200
    assert "không phải ảnh hợp lệ" in response.content.decode()
    assert not Product.objects.filter(name="Nón bảo hiểm").exists()


@pytest.mark.django_db
def test_product_image_field_allows_mobile_camera_and_supported_image_types() -> None:
    form = ProductForm()

    assert form.fields["image"].widget.attrs["accept"] == "image/jpeg,image/png,image/webp"
    assert form.fields["image"].widget.attrs["capture"] == "environment"


@pytest.mark.django_db
def test_cost_price_is_not_rendered_on_product_and_inventory_pages(
    owner_client: Client,
    variant: ProductVariant,
) -> None:
    session = owner_client.session
    session.pop(UNLOCKED_UNTIL_KEY, None)
    session.save()
    product_response = owner_client.get(reverse("product-detail", args=[variant.product_id]))
    inventory_response = owner_client.get(reverse("inventory-list"))

    assert "100.000 ₫" not in product_response.content.decode()
    assert "100.000 ₫" not in inventory_response.content.decode()
    assert "•••••• ₫" in product_response.content.decode()


@pytest.mark.django_db
def test_category_update_rejects_stale_revision(owner_client: Client) -> None:
    category = Category.objects.create(name="Áo khoác")
    url = reverse("category-update", args=[category.pk])
    first = owner_client.post(
        url,
        {"name": "Áo khoác mới", "description": "", "active": "on", "revision": "1"},
    )
    stale = owner_client.post(
        url,
        {"name": "Ghi đè cũ", "description": "", "active": "on", "revision": "1"},
    )

    assert first.status_code == 302
    assert stale.status_code == 200
    category.refresh_from_db()
    assert category.name == "Áo khoác mới"
    assert category.revision == 2
    assert "đã được thay đổi" in stale.content.decode()

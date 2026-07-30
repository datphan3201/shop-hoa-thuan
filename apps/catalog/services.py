from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import Image, ImageOps

from apps.catalog.models import InventoryMovement, Product, ProductVariant

InventoryOperation = Literal["add", "subtract", "set"]


class InsufficientStockError(ValueError):
    pass


@transaction.atomic
def adjust_inventory(
    *,
    variant_id: int,
    operation: InventoryOperation,
    quantity: int,
    reason: str,
    movement_type: str = InventoryMovement.MovementType.ADJUSTMENT,
    reference_type: str = "",
    reference_id: str = "",
) -> ProductVariant:
    reason = reason.strip()
    if not reason:
        raise ValueError("Bắt buộc nhập lý do điều chỉnh tồn kho.")
    if quantity < 0:
        raise ValueError("Số lượng không được âm.")

    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    quantity_before = variant.quantity
    if operation == "add":
        quantity_after = quantity_before + quantity
    elif operation == "subtract":
        quantity_after = quantity_before - quantity
    elif operation == "set":
        quantity_after = quantity
    else:
        raise ValueError("Thao tác tồn kho không hợp lệ.")

    if quantity_after < 0:
        raise InsufficientStockError("Số lượng tồn kho không đủ.")

    quantity_change = quantity_after - quantity_before
    ProductVariant.objects.filter(pk=variant.pk).update(quantity=quantity_after)
    InventoryMovement.objects.create(
        product_variant=variant,
        movement_type=movement_type,
        quantity_before=quantity_before,
        quantity_change=quantity_change,
        quantity_after=quantity_after,
        reference_type=reference_type,
        reference_id=reference_id,
        note=reason,
    )
    variant.quantity = quantity_after
    return variant


def process_product_image(product: Product, uploaded_image: UploadedFile | None) -> None:
    if not uploaded_image or not product.image:
        return

    image_path = Path(product.image.path)
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        output_format = source.format if source.format in {"JPEG", "PNG", "WEBP"} else "JPEG"
        if output_format == "JPEG" and image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        save_options: dict[str, object] = {"optimize": True}
        if output_format in {"JPEG", "WEBP"}:
            save_options["quality"] = 85
        image.save(image_path, format=output_format, **save_options)

        thumbnail = image.copy()
        thumbnail.thumbnail((360, 360), Image.Resampling.LANCZOS)
        if thumbnail.mode not in {"RGB", "L"}:
            thumbnail = thumbnail.convert("RGB")

        from io import BytesIO

        thumbnail_buffer = BytesIO()
        thumbnail.save(thumbnail_buffer, format="JPEG", quality=82, optimize=True)
        thumbnail_name = f"{uuid.uuid4().hex}.jpg"
        product.thumbnail.save(
            thumbnail_name,
            ContentFile(thumbnail_buffer.getvalue()),
            save=False,
        )
        product.save(update_fields=["thumbnail", "updated_at"])

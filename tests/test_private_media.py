from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from django.test import Client, override_settings
from PIL import Image


@pytest.mark.django_db
def test_product_media_is_lan_accessible_but_does_not_expose_filesystem_path(
    client: Client, tmp_path: Path
) -> None:
    media_root = tmp_path / "media"
    media_file = media_root / "products" / "sample.jpg"
    media_file.parent.mkdir(parents=True)
    image_buffer = BytesIO()
    Image.new("RGB", (10, 10), color=(20, 30, 40)).save(image_buffer, format="JPEG")
    media_file.write_bytes(image_buffer.getvalue())
    (media_root / "products" / "unsafe.txt").write_text("no", encoding="utf-8")
    with override_settings(MEDIA_ROOT=media_root):
        response = client.get("/media/products/sample.jpg")
        unsafe = client.get("/media/products/unsafe.txt")
        missing = client.get("/media/../settings.py")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, max-age=86400"
    assert response.headers["Content-Type"] == "image/jpeg"
    assert unsafe.status_code == 404
    assert missing.status_code == 404


@pytest.mark.django_db
def test_private_media_rejects_spoofed_or_corrupt_image_content(
    client: Client, tmp_path: Path
) -> None:
    media_root = tmp_path / "media"
    media_file = media_root / "products" / "not-really-an-image.jpg"
    media_file.parent.mkdir(parents=True)
    media_file.write_text("not an image", encoding="utf-8")
    with override_settings(MEDIA_ROOT=media_root):
        response = client.get("/media/products/not-really-an-image.jpg")

    assert response.status_code == 404

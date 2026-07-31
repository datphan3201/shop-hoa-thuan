from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings


@pytest.mark.django_db
def test_product_media_requires_login_and_does_not_expose_filesystem_path(
    client: Client, tmp_path: Path
) -> None:
    media_root = tmp_path / "media"
    media_file = media_root / "products" / "sample.jpg"
    media_file.parent.mkdir(parents=True)
    media_file.write_bytes(b"image")
    (media_root / "products" / "unsafe.txt").write_text("no", encoding="utf-8")
    with override_settings(MEDIA_ROOT=media_root):
        anonymous = client.get("/media/products/sample.jpg")
        assert anonymous.status_code == 302
        owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
        client.force_login(owner)
        response = client.get("/media/products/sample.jpg")
        unsafe = client.get("/media/products/unsafe.txt")
        missing = client.get("/media/../settings.py")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, max-age=86400"
    assert response.headers["Content-Type"] == "image/jpeg"
    assert unsafe.status_code == 404
    assert missing.status_code == 404

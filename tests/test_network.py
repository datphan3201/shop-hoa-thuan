from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings

from apps.core.network import discover_device_access, server_port


def test_device_access_uses_configured_port_lan_and_optional_tailscale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHOP_SERVER_PORT", "2600")
    monkeypatch.setenv("SHOP_TAILSCALE_HOSTNAME", "shop.tailnet.ts.net")
    with patch("apps.core.network.lan_ipv4_addresses", return_value=["192.168.1.10"]):
        access = discover_device_access()

    assert server_port() == 2600
    assert access.localhost_url == "http://127.0.0.1:2600/"
    assert access.lan_urls == ("http://192.168.1.10:2600/",)
    assert access.tailscale_url == "https://shop.tailnet.ts.net/"


def test_invalid_server_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_SERVER_PORT", "70000")

    with pytest.raises(RuntimeError, match="1-65535"):
        server_port()


@pytest.mark.django_db
def test_device_access_page_is_private_and_renders_qr(client: Client) -> None:
    user = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(user)
    with override_settings():
        response = client.get("/settings/device-access/")

    content = response.content.decode()
    assert response.status_code == 200
    assert "Mã QR mở Shop Hoà Thuận" in content
    assert "data:image/svg+xml;base64," in content

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client, override_settings

from apps.core.network import (
    DeviceAccess,
    connected_wifi,
    discover_device_access,
    server_port,
    wifi_ipv4_addresses,
)


def test_device_access_uses_configured_port_lan_and_optional_tailscale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHOP_SERVER_PORT", "2600")
    monkeypatch.setenv("SHOP_TAILSCALE_HOSTNAME", "shop.tailnet.ts.net")
    with (
        patch("apps.core.network.lan_ipv4_addresses", return_value=["192.168.1.10"]),
        patch("apps.core.network.connected_wifi", return_value=("VIETTEL", "Wi-Fi")),
    ):
        access = discover_device_access()

    assert server_port() == 2600
    assert access.localhost_url == "http://127.0.0.1:2600/"
    assert access.lan_urls == ("http://192.168.1.10:2600/",)
    assert access.tailscale_url == "https://shop.tailnet.ts.net/"
    assert access.wifi_name == "VIETTEL"
    assert access.wifi_interface == "Wi-Fi"
    assert access.wifi_label == "VIETTEL (Wi-Fi)"


def test_connected_wifi_parses_connected_windows_interface() -> None:
    output = """
    Name                   : Wi-Fi
    State                  : connected
    SSID                   : VIETTEL
    BSSID                  : 00:11:22:33:44:55
    """
    with (
        patch("apps.core.network.os.name", "nt"),
        patch("apps.core.network.subprocess.run") as run,
    ):
        run.return_value.stdout = output
        assert connected_wifi() == ("VIETTEL", "Wi-Fi")


def test_wifi_ipv4_addresses_parses_current_adapter_addresses() -> None:
    output = """
    Configuration for interface \"Wi-Fi\"
        DHCP enabled: Yes
        IP Address: 192.168.1.69
        Subnet Prefix: 192.168.1.0/24 (mask 255.255.255.0)
        Default Gateway: 192.168.1.1
    """
    with (
        patch("apps.core.network.os.name", "nt"),
        patch("apps.core.network.subprocess.run") as run,
    ):
        run.return_value.stdout = output
        assert wifi_ipv4_addresses("Wi-Fi") == ["192.168.1.69"]


def test_device_access_prefers_current_wifi_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_SERVER_PORT", "2505")
    with (
        patch("apps.core.network.connected_wifi", return_value=("VIETTEL", "Wi-Fi")),
        patch("apps.core.network.wifi_ipv4_addresses", return_value=["192.168.1.69"]),
        patch("apps.core.network.lan_ipv4_addresses", return_value=["192.168.100.10"]),
    ):
        access = discover_device_access()

    assert access.lan_addresses == ("192.168.1.69",)
    assert access.lan_urls[0] == "http://192.168.1.69:2505/"


def test_invalid_server_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_SERVER_PORT", "70000")

    with pytest.raises(RuntimeError, match="1-65535"):
        server_port()


@pytest.mark.django_db
def test_device_access_page_renders_qr_without_login(client: Client) -> None:
    with override_settings():
        response = client.get("/settings/device-access/")

    content = response.content.decode()
    assert response.status_code == 200
    assert "Wi-Fi đang dùng" in response.content.decode()
    assert "device-access-live" in response.content.decode()
    assert "Mã QR mở Shop Hoà Thuận" in content
    assert "data:image/svg+xml;base64," in content


@pytest.mark.django_db
def test_device_access_live_refresh_is_uncached_and_uses_latest_network_snapshot(
    client: Client,
) -> None:
    access = DeviceAccess(
        hostname="SHOP-SERVER",
        port=2505,
        lan_addresses=("192.168.1.69",),
        tailscale_hostname=None,
        wifi_name="VIETTEL",
        wifi_interface="Wi-Fi",
    )
    with patch("apps.core.views.discover_device_access", return_value=access):
        response = client.get("/settings/device-access/live/?t=2")

    content = response.content.decode()
    assert response.status_code == 200
    assert (
        response.headers["Cache-Control"]
        == "max-age=0, no-cache, no-store, must-revalidate, private"
    )
    assert "VIETTEL (Wi-Fi)" in content
    assert "192.168.1.69:2505" in content
    assert 'data-qr-target="http://192.168.1.69:2505/"' in content

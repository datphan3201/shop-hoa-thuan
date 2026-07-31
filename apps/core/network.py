from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from typing import cast


def server_port() -> int:
    value = os.getenv("SHOP_SERVER_PORT", "2505")
    try:
        port = int(value)
    except ValueError as error:
        raise RuntimeError("SHOP_SERVER_PORT phải là số nguyên hợp lệ.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("SHOP_SERVER_PORT phải nằm trong khoảng 1-65535.")
    return port


def lan_ipv4_addresses() -> list[str]:
    """Return stable, non-loopback private IPv4 addresses without shelling out."""
    addresses: set[str] = set()
    for entry in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
        address = cast(str, entry[4][0])
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.is_private and not parsed.is_loopback and not parsed.is_link_local:
            addresses.add(address)
    return sorted(addresses)


@dataclass(frozen=True)
class DeviceAccess:
    hostname: str
    port: int
    lan_addresses: tuple[str, ...]
    tailscale_hostname: str | None

    @property
    def localhost_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    @property
    def lan_urls(self) -> tuple[str, ...]:
        return tuple(f"http://{address}:{self.port}/" for address in self.lan_addresses)

    @property
    def tailscale_url(self) -> str | None:
        if not self.tailscale_hostname:
            return None
        return f"https://{self.tailscale_hostname}/"


def discover_device_access() -> DeviceAccess:
    hostname = socket.gethostname().strip() or "shophoathuan"
    tailscale = os.getenv("SHOP_TAILSCALE_HOSTNAME", "").strip() or None
    return DeviceAccess(
        hostname=hostname,
        port=server_port(),
        lan_addresses=tuple(lan_ipv4_addresses()),
        tailscale_hostname=tailscale,
    )

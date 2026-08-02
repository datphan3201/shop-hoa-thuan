from __future__ import annotations

import ipaddress
import os
import re
import socket
import subprocess
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
    wifi_name: str | None = None
    wifi_interface: str | None = None

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

    @property
    def wifi_label(self) -> str:
        if self.wifi_name and self.wifi_interface:
            return f"{self.wifi_name} ({self.wifi_interface})"
        return self.wifi_name or self.wifi_interface or "Chưa xác định"


def connected_wifi() -> tuple[str | None, str | None]:
    """Return the connected Windows SSID and adapter name when available."""
    if os.name != "nt":
        return None, None
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return None, None

    for block in re.split(r"\r?\n\s*\r?\n", result.stdout):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, separator, value = line.partition(":")
            if separator:
                fields[key.strip().lower()] = value.strip()
        ssid = fields.get("ssid", "")
        if ssid:
            return ssid, fields.get("name") or None
    return None, None


def wifi_ipv4_addresses(interface_name: str | None) -> list[str]:
    """Read current IPv4 addresses for the connected Windows Wi-Fi adapter."""
    if os.name != "nt" or not interface_name:
        return []
    try:
        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "addresses", f"name={interface_name}"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return []

    addresses: list[str] = []
    for line in result.stdout.splitlines():
        if not re.search(r"(?:ip\s*address|địa\s*chỉ\s*ip)", line, re.IGNORECASE):
            continue
        for value in re.findall(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)", line):
            try:
                parsed = ipaddress.ip_address(value)
            except ValueError:
                continue
            if parsed.version == 4 and parsed.is_private and not parsed.is_link_local:
                if value not in addresses:
                    addresses.append(value)
    return addresses


def discover_device_access() -> DeviceAccess:
    hostname = socket.gethostname().strip() or "shophoathuan"
    tailscale = os.getenv("SHOP_TAILSCALE_HOSTNAME", "").strip() or None
    wifi_name, wifi_interface = connected_wifi()
    addresses = wifi_ipv4_addresses(wifi_interface) or lan_ipv4_addresses()
    return DeviceAccess(
        hostname=hostname,
        port=server_port(),
        lan_addresses=tuple(addresses),
        tailscale_hostname=tailscale,
        wifi_name=wifi_name,
        wifi_interface=wifi_interface,
    )

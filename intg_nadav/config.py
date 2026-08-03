"""
NAD AV configuration for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass
from ucapi_framework import BaseConfigManager

CONNECTION_BLUOS = "BluOS"
CONNECTION_TELNET = "Telnet"
CONNECTION_TCP = "TCP"
CONNECTION_RS232 = "RS232"

DEFAULT_PORTS = {
    CONNECTION_BLUOS: 11000,
    CONNECTION_TELNET: 23,
    CONNECTION_TCP: 53,
    CONNECTION_RS232: 0,
}


def sanitize_identifier(value: str) -> str:
    """Build a dot-free identifier component (dots break device_from_entity_id)."""
    return value.replace(".", "_").replace("/", "_").replace("\\", "_").replace(":", "_")


@dataclass
class NADDeviceConfig:
    """NAD device configuration."""

    identifier: str
    name: str
    connection_type: str
    host: str | None = None
    port: int = 11000
    serial_port: str = "/dev/ttyUSB0"
    min_volume: int = -92
    max_volume: int = -20
    volume_step: int = 5
    sources: dict[int, str] | None = None

    @property
    def is_bluos(self) -> bool:
        """Return True for BluOS streaming models (M10, M33, C700, C658, ...)."""
        return self.connection_type == CONNECTION_BLUOS


class NADConfigManager(BaseConfigManager[NADDeviceConfig]):
    """NAD configuration manager with automatic JSON persistence."""
    pass

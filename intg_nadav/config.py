"""
NAD AV configuration for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass
from ucapi_framework import BaseConfigManager


@dataclass
class NADDeviceConfig:
    """NAD device configuration."""
    
    identifier: str
    name: str
    connection_type: str
    host: str | None = None
    port: int = 53
    serial_port: str = "/dev/ttyUSB0"
    min_volume: int = -92
    max_volume: int = -20
    volume_step: int = 4
    sources: dict[int, str] | None = None


class NADConfigManager(BaseConfigManager[NADDeviceConfig]):
    """NAD configuration manager with automatic JSON persistence."""
    pass
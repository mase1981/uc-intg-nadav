"""
NAD AV driver for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import ucapi
from ucapi_framework import BaseIntegrationDriver, get_config_path
from intg_nadav.config import NADDeviceConfig, NADConfigManager
from intg_nadav.device import NADDevice
from intg_nadav.media_player import NADMediaPlayer
from intg_nadav.setup_flow import NADSetupFlow

_LOG = logging.getLogger(__name__)


class NADDriver(BaseIntegrationDriver[NADDevice, NADDeviceConfig]):
    """NAD AV integration driver."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        """Initialize NAD driver."""
        super().__init__(
            loop=loop,
            device_class=NADDevice,
            entity_classes=NADMediaPlayer,
            driver_id="nadav",
        )
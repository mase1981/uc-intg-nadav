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


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    )
    
    loop = asyncio.get_running_loop()
    
    driver = NADDriver(loop)
    
    config_path = get_config_path(driver.api.config_dir_path)
    _LOG.info("Using configuration path: %s", config_path)
    
    driver.config_manager = NADConfigManager(
        config_path,
        add_handler=driver.on_device_added,
        remove_handler=driver.on_device_removed,
        config_class=NADDeviceConfig,
    )
    
    setup_handler = NADSetupFlow.create_handler(driver)
    
    await driver.api.init("driver.json", setup_handler=setup_handler)
    
    await driver.register_all_configured_devices()
    
    await driver.api.set_device_state(ucapi.DeviceStates.CONNECTED)
    
    _LOG.info("NAD AV integration started")
    
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user")
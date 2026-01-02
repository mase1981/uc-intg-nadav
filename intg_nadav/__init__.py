"""
NAD AV integration for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os

from ucapi import DeviceStates
from ucapi_framework import BaseConfigManager, get_config_path

from intg_nadav.config import NADDeviceConfig
from intg_nadav.driver import NADDriver
from intg_nadav.setup_flow import NADSetupFlow

__version__ = "1.0.4"

_LOG = logging.getLogger(__name__)


async def main():
    """Main entry point for NAD integration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    )
    
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)
    
    _LOG.info("Starting NAD AV integration v%s", __version__)
    
    try:
        loop = asyncio.get_running_loop()
        
        driver = NADDriver(loop)
        
        config_path = get_config_path(driver.api.config_dir_path or "")
        _LOG.info("Using configuration path: %s", config_path)
        
        driver.config_manager = BaseConfigManager(
            config_path,
            add_handler=driver.on_device_added,
            remove_handler=driver.on_device_removed,
            config_class=NADDeviceConfig,
        )
        
        setup_handler = NADSetupFlow.create_handler(driver)
        
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        await driver.api.init(os.path.abspath(driver_path), setup_handler)
        
        await driver.register_all_configured_devices()
        
        device_count = len(list(driver.config_manager.all()))
        if device_count > 0:
            _LOG.info("Configured with %d device(s)", device_count)
            await driver.api.set_device_state(DeviceStates.CONNECTED)
        else:
            _LOG.info("No devices configured, waiting for setup")
            await driver.api.set_device_state(DeviceStates.DISCONNECTED)
        
        _LOG.info("=" * 70)
        _LOG.info("✅ NAD AV integration started successfully")
        _LOG.info("=" * 70)
        _LOG.info("Integration is running and ready for configuration")
        _LOG.info("Press Ctrl+C to stop")
        _LOG.info("=" * 70)
        
        await asyncio.Future()
    
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user")
    except asyncio.CancelledError:
        _LOG.info("Integration task cancelled")
    except Exception as err:
        _LOG.critical("Fatal error: %s", err, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
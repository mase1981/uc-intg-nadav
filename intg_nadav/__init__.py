"""
NAD AV integration for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
from pathlib import Path

from ucapi_framework import BaseConfigManager, get_config_path

from intg_nadav.config import NADDeviceConfig
from intg_nadav.driver import NADDriver

_LOG = logging.getLogger(__name__)

# Load version from driver.json
try:
    driver_path = Path(__file__).parent.parent / "driver.json"
    with open(driver_path, "r", encoding="utf-8") as f:
        driver_info = json.load(f)
        __version__ = driver_info.get("version", "0.0.0")
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    __version__ = "0.0.0"

__all__ = ["__version__"]


async def main():
    """Main entry point for NAD integration."""
    logging.basicConfig(level=logging.DEBUG)
    
    loop = asyncio.get_running_loop()
    
    driver = NADDriver(loop)
    
    config_path = get_config_path(driver.api.config_dir_path)
    driver.config_manager = BaseConfigManager(
        config_path,
        add_handler=driver.on_device_added,
        remove_handler=driver.on_device_removed,
        config_class=NADDeviceConfig,
    )
    
    from intg_nadav.setup_flow import NADSetupFlow
    setup_handler = NADSetupFlow.create_handler(driver)
    
    await driver.api.init("driver.json", setup_handler=setup_handler)
    
    await driver.register_all_configured_devices()
    
    import ucapi
    await driver.api.set_device_state(ucapi.DeviceStates.CONNECTED)
    
    _LOG.info("NAD AV integration started (version %s)", __version__)
    
    await asyncio.Future()
"""
NAD AV integration for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from ucapi_framework import BaseConfigManager, get_config_path

from intg_nadav.config import NADDeviceConfig
from intg_nadav.driver import NADDriver

_LOG = logging.getLogger(__name__)

# Load version from driver.json
try:
    # Handle PyInstaller frozen binary
    if getattr(sys, 'frozen', False):
        # Running as compiled binary - binary is in bin/ subdirectory
        driver_path = Path(sys.executable).parent.parent / "driver.json"
    else:
        # Running as normal Python script
        driver_path = Path(__file__).parent.parent / "driver.json"
    
    with open(driver_path, "r", encoding="utf-8") as f:
        driver_info = json.load(f)
        __version__ = driver_info.get("version", "0.0.0")
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    _LOG.warning("Could not load version from driver.json: %s", e)
    __version__ = "0.0.0"

__all__ = ["__version__"]


async def main():
    """Main entry point for NAD integration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    )
    
    _LOG.info("Starting NAD AV integration (version %s)", __version__)
    
    loop = asyncio.get_running_loop()
    
    driver = NADDriver(loop)
    
    config_path = get_config_path(driver.api.config_dir_path)
    _LOG.info("Using configuration path: %s", config_path)
    
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
    
    _LOG.info("NAD AV integration ready")
    
    await asyncio.Future()
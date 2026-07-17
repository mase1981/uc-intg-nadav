"""
NAD AV integration for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

try:
    _driver_path = Path(__file__).parent.parent / "driver.json"
    with open(_driver_path, "r", encoding="utf-8") as f:
        __version__ = json.load(f).get("version", "0.0.0")
except (FileNotFoundError, json.JSONDecodeError):
    __version__ = "0.0.0"

__all__ = ["__version__", "main"]


def _migrate_configs(config_manager) -> None:
    """Migrate legacy configs to dot-free identifiers.

    Dotted identifiers (e.g. ``192.168.1.89_53``) break the framework's
    ``device_from_entity_id`` (it splits on ``.``), so subscribed entities can
    never be mapped back to their device. Rewrite them to ``nad_<host>_<port>``
    so existing users keep their device without re-running setup.
    """
    from intg_nadav.config import sanitize_identifier

    _LOG = logging.getLogger(__name__)
    for cfg in list(config_manager.all()):
        old_id = cfg.identifier
        if old_id.startswith("nad_") and "." not in old_id:
            continue

        if cfg.connection_type == "RS232":
            new_id = f"nad_{sanitize_identifier(cfg.serial_port)}"
        else:
            new_id = f"nad_{sanitize_identifier(cfg.host or old_id)}_{cfg.port}"

        if new_id == old_id:
            continue

        _LOG.info("Migrating device identifier '%s' -> '%s'", old_id, new_id)
        cfg.identifier = new_id
        config_manager.add_or_update(cfg)
        config_manager.remove(old_id)


async def main():
    from ucapi import DeviceStates
    from ucapi_framework import BaseConfigManager, get_config_path

    from intg_nadav.config import NADDeviceConfig
    from intg_nadav.driver import NADDriver
    from intg_nadav.setup_flow import NADSetupFlow

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.DEBUG),
        format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    _LOG = logging.getLogger(__name__)
    _LOG.info("Starting NAD AV integration v%s", __version__)

    driver = NADDriver()
    config_path = get_config_path(driver.api.config_dir_path or "")

    # Migrate legacy configs first, on a handler-less manager, so the add/remove
    # handlers don't fire before the driver/API are initialized.
    try:
        migration_manager = BaseConfigManager(config_path, config_class=NADDeviceConfig)
        _migrate_configs(migration_manager)
    except Exception as err:
        _LOG.warning("Config migration skipped: %s", err)

    config_manager = BaseConfigManager(
        config_path,
        add_handler=driver.on_device_added,
        remove_handler=driver.on_device_removed,
        config_class=NADDeviceConfig,
    )
    driver.config_manager = config_manager

    setup_handler = NADSetupFlow.create_handler(driver)
    driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
    await driver.api.init(os.path.abspath(driver_path), setup_handler)
    await driver.register_all_configured_devices(connect=False)

    device_count = len(list(config_manager.all()))
    await driver.api.set_device_state(
        DeviceStates.CONNECTED if device_count > 0 else DeviceStates.DISCONNECTED
    )
    _LOG.info("NAD AV integration started - %d device(s) configured", device_count)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

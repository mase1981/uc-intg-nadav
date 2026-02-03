"""
NAD Sensor entities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi.sensor import Attributes, DeviceClasses, Sensor, States
from ucapi_framework.entity import Entity

from intg_nadav.config import NADDeviceConfig
from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


class NADModelSensor(Sensor, Entity):
    """NAD device model sensor."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize sensor."""
        self._device = device
        self._device_config = device_config

        entity_id = f"sensor.{device_config.identifier}_model"

        super().__init__(
            entity_id,
            f"{device_config.name} Model",
            [],  # features - no specific features needed
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.VALUE: "Unknown",
            },
            device_class=None,
        )


class NADVersionSensor(Sensor, Entity):
    """NAD device firmware version sensor."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize sensor."""
        self._device = device
        self._device_config = device_config

        entity_id = f"sensor.{device_config.identifier}_version"

        super().__init__(
            entity_id,
            f"{device_config.name} Version",
            [],  # features - no specific features needed
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.VALUE: "Unknown",
            },
            device_class=None,
        )

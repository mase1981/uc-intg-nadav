"""
NAD sensor entities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ucapi import sensor
from ucapi_framework import SensorEntity

if TYPE_CHECKING:
    from intg_nadav.config import NADDeviceConfig
    from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


class _BaseSensor(SensorEntity):
    _sub_id = "sensor"
    _label = "Sensor"

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.{self._sub_id}"
        super().__init__(
            entity_id,
            f"{device_config.name} {self._label}",
            [],
            {
                sensor.Attributes.STATE: sensor.States.UNKNOWN,
                sensor.Attributes.VALUE: "",
            },
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    def _value(self) -> str:
        raise NotImplementedError

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({
                sensor.Attributes.STATE: sensor.States.UNAVAILABLE,
                sensor.Attributes.VALUE: "unavailable",
            })
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._value(),
        })


class NADModelSensor(_BaseSensor):
    _sub_id = "model"
    _label = "Model"

    def _value(self) -> str:
        return self._device.model or "Unknown"


class NADVersionSensor(_BaseSensor):
    _sub_id = "version"
    _label = "Version"

    def _value(self) -> str:
        return self._device.version or "Unknown"


class NADSourceSensor(_BaseSensor):
    _sub_id = "source"
    _label = "Source"

    def _value(self) -> str:
        return self._device.source or "None"


class NADConnectionSensor(_BaseSensor):
    _sub_id = "connection"
    _label = "Connection"

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({
                sensor.Attributes.STATE: sensor.States.UNAVAILABLE,
                sensor.Attributes.VALUE: "disconnected",
            })
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: "connected",
        })

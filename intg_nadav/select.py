"""
NAD select entities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from ucapi import select, StatusCodes
from ucapi_framework import SelectEntity

if TYPE_CHECKING:
    from intg_nadav.config import NADDeviceConfig
    from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)

SPEAKER_OPTIONS = ["On", "Off"]
REPEAT_OPTIONS = ["Off", "All", "One"]


def _base_attrs() -> dict:
    return {
        select.Attributes.STATE: select.States.UNKNOWN,
        select.Attributes.OPTIONS: [],
        select.Attributes.CURRENT_OPTION: "",
    }


class NADSourceSelect(SelectEntity):
    """Input/source selector (physical inputs on BluOS, sources on classic)."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.source"
        super().__init__(
            entity_id,
            f"{device_config.name} Source",
            _base_attrs(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        d = self._device
        options = d.source_list
        if d.state == "UNAVAILABLE" or not options:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: options,
            select.Attributes.CURRENT_OPTION: d.source or "",
        })

    async def _handle_command(self, entity, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        if cmd_id == select.Commands.SELECT_OPTION:
            option = params.get("option", "") if params else ""
            if not option:
                return StatusCodes.BAD_REQUEST
            ok = await self._device.select_source(option)
            return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR
        return StatusCodes.NOT_IMPLEMENTED


class NADPresetSelect(SelectEntity):
    """BluOS preset selector."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.preset"
        super().__init__(
            entity_id,
            f"{device_config.name} Preset",
            _base_attrs(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        d = self._device
        options = [p.get("name", f"Preset {p.get('id')}") for p in d.presets]
        if d.state == "UNAVAILABLE" or not options:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: options,
            select.Attributes.CURRENT_OPTION: options[0],
        })

    async def _handle_command(self, entity, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        if cmd_id == select.Commands.SELECT_OPTION:
            option = params.get("option", "") if params else ""
            for preset in self._device.presets:
                if preset.get("name") == option:
                    ok = await self._device.client.select_preset(int(preset.get("id", 0)))
                    return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR
            return StatusCodes.BAD_REQUEST
        return StatusCodes.NOT_IMPLEMENTED


class NADRepeatSelect(SelectEntity):
    """BluOS repeat-mode selector."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.repeat"
        super().__init__(
            entity_id,
            f"{device_config.name} Repeat",
            _base_attrs(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        d = self._device
        if d.state == "UNAVAILABLE":
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: REPEAT_OPTIONS,
            select.Attributes.CURRENT_OPTION: d.repeat.capitalize(),
        })

    async def _handle_command(self, entity, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        if cmd_id == select.Commands.SELECT_OPTION:
            option = params.get("option", "") if params else ""
            repeat_val = {"Off": "OFF", "All": "ALL", "One": "ONE"}.get(option)
            if repeat_val is None:
                return StatusCodes.BAD_REQUEST
            ok = await self._device.client.set_repeat(repeat_val)
            return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR
        return StatusCodes.NOT_IMPLEMENTED


class _SpeakerSelect(SelectEntity):
    """Classic speaker A/B selector."""

    _sub_id = "speaker"
    _label = "Speaker"

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.{self._sub_id}"
        super().__init__(
            entity_id,
            f"{device_config.name} {self._label}",
            _base_attrs(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _current(self) -> str:
        raise NotImplementedError

    async def _apply(self, state: str) -> bool:
        raise NotImplementedError

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: SPEAKER_OPTIONS,
            select.Attributes.CURRENT_OPTION: self._current(),
        })

    async def _handle_command(self, entity, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        if cmd_id == select.Commands.SELECT_OPTION:
            option = params.get("option", "") if params else ""
            if option not in SPEAKER_OPTIONS:
                return StatusCodes.BAD_REQUEST
            ok = await self._apply(option)
            return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR
        return StatusCodes.NOT_IMPLEMENTED


class NADSpeakerASelect(_SpeakerSelect):
    _sub_id = "speaker_a"
    _label = "Speaker A"

    def _current(self) -> str:
        return self._device.speaker_a

    async def _apply(self, state: str) -> bool:
        return await self._device.client.set_speaker_a(state)


class NADSpeakerBSelect(_SpeakerSelect):
    _sub_id = "speaker_b"
    _label = "Speaker B"

    def _current(self) -> str:
        return self._device.speaker_b

    async def _apply(self, state: str) -> bool:
        return await self._device.client.set_speaker_b(state)

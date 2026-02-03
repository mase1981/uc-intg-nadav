"""
NAD Select entities for speaker and listening mode control.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.select import Attributes, Features, Select, States

from intg_nadav.config import NADDeviceConfig
from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


class NADSpeakerASelect(Select):
    """Select entity for Speaker A control."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize select entity."""
        self._device = device
        self._device_config = device_config

        entity_id = f"select.{device_config.identifier}_speaker_a"
        entity_name = f"{device_config.name} Speaker A"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.CURRENT_OPTION: "Off",
            Attributes.OPTIONS: ["On", "Off"],
        }

        super().__init__(
            entity_id,
            entity_name,
            attributes,
            cmd_handler=self.handle_command,
        )

        _LOG.info("[%s] Speaker A select entity initialized", self.id)

    async def handle_command(
        self, entity: Select, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle select commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            if cmd_id == "select_option" and params and "option" in params:
                state = params["option"]
                success = await self._device.set_speaker_a(state)
                if success:
                    await self._device.poll_device()  # Immediate update
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            return StatusCodes.NOT_IMPLEMENTED

        except Exception as err:
            _LOG.error("[%s] Command error: %s", self.id, err)
            return StatusCodes.SERVER_ERROR


class NADSpeakerBSelect(Select):
    """Select entity for Speaker B control."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize select entity."""
        self._device = device
        self._device_config = device_config

        entity_id = f"select.{device_config.identifier}_speaker_b"
        entity_name = f"{device_config.name} Speaker B"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.CURRENT_OPTION: "Off",
            Attributes.OPTIONS: ["On", "Off"],
        }

        super().__init__(
            entity_id,
            entity_name,
            attributes,
            cmd_handler=self.handle_command,
        )

        _LOG.info("[%s] Speaker B select entity initialized", self.id)

    async def handle_command(
        self, entity: Select, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle select commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            if cmd_id == "select_option" and params and "option" in params:
                state = params["option"]
                success = await self._device.set_speaker_b(state)
                if success:
                    await self._device.poll_device()  # Immediate update
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            return StatusCodes.NOT_IMPLEMENTED

        except Exception as err:
            _LOG.error("[%s] Command error: %s", self.id, err)
            return StatusCodes.SERVER_ERROR


class NADListeningModeSelect(Select):
    """Select entity for listening mode control."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize select entity."""
        self._device = device
        self._device_config = device_config

        entity_id = f"select.{device_config.identifier}_listening_mode"
        entity_name = f"{device_config.name} Listening Mode"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.CURRENT_OPTION: "",
            Attributes.OPTIONS: [],
        }

        super().__init__(
            entity_id,
            entity_name,
            attributes,
            cmd_handler=self.handle_command,
        )

        _LOG.info("[%s] Listening Mode select entity initialized", self.id)

    async def handle_command(
        self, entity: Select, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle select commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            if cmd_id == "select_option" and params and "option" in params:
                mode = params["option"]
                success = await self._device.set_listening_mode(mode)
                if success:
                    await self._device.poll_device()  # Immediate update
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            return StatusCodes.NOT_IMPLEMENTED

        except Exception as err:
            _LOG.error("[%s] Command error: %s", self.id, err)
            return StatusCodes.SERVER_ERROR

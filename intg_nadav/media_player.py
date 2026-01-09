"""
NAD AV media player entity for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any
from ucapi import StatusCodes
from ucapi.media_player import Attributes, Commands, DeviceClasses, Features, MediaPlayer, States, Options

from intg_nadav.config import NADDeviceConfig
from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


class NADMediaPlayer(MediaPlayer):
    """Media player entity for NAD AV receivers."""
    
    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize NAD media player."""
        self._device = device
        
        features = [
            Features.ON_OFF,
            Features.TOGGLE,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
        ]
        
        # CRITICAL FIX: Initialize with current source list
        attributes = {
            Attributes.STATE: States.UNKNOWN,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
        }
        
        # Add source support if sources are configured
        if device.source_list:
            features.append(Features.SELECT_SOURCE)
            attributes[Attributes.SOURCE] = ""
            attributes[Attributes.SOURCE_LIST] = device.source_list
            _LOG.info("NAD Media Player initialized with %d sources: %s", 
                     len(device.source_list), device.source_list)
        
        options = {
            Options.SIMPLE_COMMANDS: [
                Commands.ON,
                Commands.OFF,
                Commands.VOLUME_UP,
                Commands.VOLUME_DOWN,
                Commands.MUTE_TOGGLE,
            ]
        }
        
        # Add source selection to simple commands if available
        if device.source_list:
            options[Options.SIMPLE_COMMANDS].append(Commands.SELECT_SOURCE)
        
        super().__init__(
            identifier=device_config.identifier,
            name={"en": device_config.name},
            features=features,
            attributes=attributes,
            device_class=DeviceClasses.RECEIVER,
            options=options,
            cmd_handler=self.handle_command,
        )
    
    async def handle_command(
        self, entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle media player commands."""
        _LOG.info("[%s] Command: %s %s", self._device.name, cmd_id, params or "")
        
        try:
            success = False
            
            if cmd_id == Commands.ON:
                success = await self._device.turn_on()
            
            elif cmd_id == Commands.OFF:
                success = await self._device.turn_off()
            
            elif cmd_id == Commands.TOGGLE:
                if self._device.power:
                    success = await self._device.turn_off()
                else:
                    success = await self._device.turn_on()
            
            elif cmd_id == Commands.VOLUME:
                volume = params.get("volume", 0) if params else 0
                success = await self._device.set_volume(int(volume))
            
            elif cmd_id == Commands.VOLUME_UP:
                success = await self._device.volume_up()
            
            elif cmd_id == Commands.VOLUME_DOWN:
                success = await self._device.volume_down()
            
            elif cmd_id == Commands.MUTE_TOGGLE:
                success = await self._device.mute(not self._device.muted)
            
            elif cmd_id == Commands.MUTE:
                success = await self._device.mute(True)
            
            elif cmd_id == Commands.UNMUTE:
                success = await self._device.mute(False)
            
            elif cmd_id == Commands.SELECT_SOURCE:
                source = params.get("source") if params else None
                if source:
                    _LOG.info("[%s] Selecting source: %s", self._device.name, source)
                    success = await self._device.select_source(source)
                else:
                    _LOG.warning("[%s] SELECT_SOURCE called without source parameter", self._device.name)
                    return StatusCodes.BAD_REQUEST
            
            else:
                _LOG.warning("[%s] Unsupported command: %s", self._device.name, cmd_id)
                return StatusCodes.NOT_IMPLEMENTED
            
            return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
        except Exception as err:
            _LOG.error("[%s] Command failed: %s - %s", self._device.name, cmd_id, err)
            return StatusCodes.SERVER_ERROR
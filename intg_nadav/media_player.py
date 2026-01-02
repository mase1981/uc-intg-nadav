"""
NAD AV media player entity for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any
from ucapi import MediaPlayer, StatusCodes, media_player
from intg_nadav.config import NADDeviceConfig
from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


class NADMediaPlayer(MediaPlayer):
    """Media player entity for NAD AV receivers."""
    
    def __init__(self, device_config: NADDeviceConfig, device: NADDevice):
        """Initialize NAD media player."""
        self._device = device
        
        features = [
            media_player.Features.ON_OFF,
            media_player.Features.TOGGLE,
            media_player.Features.VOLUME,
            media_player.Features.VOLUME_UP_DOWN,
            media_player.Features.MUTE_TOGGLE,
            media_player.Features.MUTE,
            media_player.Features.UNMUTE,
        ]
        
        if device.source_list:
            features.append(media_player.Features.SELECT_SOURCE)
        
        attributes = {
            media_player.Attributes.STATE: media_player.States.UNKNOWN,
            media_player.Attributes.VOLUME: 0,
            media_player.Attributes.MUTED: False,
        }
        
        if device.source_list:
            attributes[media_player.Attributes.SOURCE_LIST] = device.source_list
        
        super().__init__(
            identifier=device_config.identifier,
            name={"en": device_config.name},
            features=features,
            attributes=attributes,
            device_class=media_player.DeviceClasses.RECEIVER,
            options={
                media_player.Options.VOLUME_STEPS: 100,
            },
            cmd_handler=self.handle_command,
        )
    
    async def handle_command(
        self, entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle media player commands."""
        _LOG.info("[%s] Command: %s %s", self._device.name, cmd_id, params)
        
        try:
            if cmd_id == media_player.Commands.ON:
                success = await self._device.turn_on()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.OFF:
                success = await self._device.turn_off()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.TOGGLE:
                if self._device.power:
                    success = await self._device.turn_off()
                else:
                    success = await self._device.turn_on()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.VOLUME:
                volume = params.get("volume", 0) if params else 0
                success = await self._device.set_volume(int(volume))
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.VOLUME_UP:
                success = await self._device.volume_up()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.VOLUME_DOWN:
                success = await self._device.volume_down()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.MUTE_TOGGLE:
                success = await self._device.mute(not self._device.muted)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.MUTE:
                success = await self._device.mute(True)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.UNMUTE:
                success = await self._device.mute(False)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            if cmd_id == media_player.Commands.SELECT_SOURCE:
                source = params.get("source") if params else None
                if source:
                    success = await self._device.select_source(source)
                    return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                return StatusCodes.BAD_REQUEST
            
            _LOG.warning("[%s] Unsupported command: %s", self._device.name, cmd_id)
            return StatusCodes.NOT_IMPLEMENTED
            
        except Exception as err:
            _LOG.error("[%s] Command failed: %s - %s", self._device.name, cmd_id, err)
            return StatusCodes.SERVER_ERROR
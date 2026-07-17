"""
NAD media player entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from ucapi import media_player, StatusCodes
from ucapi.media_player import BrowseOptions, BrowseResults, SearchOptions, SearchResults
from ucapi_framework import MediaPlayerEntity

from intg_nadav import browser

if TYPE_CHECKING:
    from intg_nadav.config import NADDeviceConfig
    from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)

_COMMON_FEATURES = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.VOLUME,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.MUTE,
    media_player.Features.UNMUTE,
    media_player.Features.SELECT_SOURCE,
]

_BLUOS_FEATURES = [
    media_player.Features.PLAY_PAUSE,
    media_player.Features.STOP,
    media_player.Features.NEXT,
    media_player.Features.PREVIOUS,
    media_player.Features.SHUFFLE,
    media_player.Features.REPEAT,
    media_player.Features.SEEK,
    media_player.Features.MEDIA_TITLE,
    media_player.Features.MEDIA_ARTIST,
    media_player.Features.MEDIA_ALBUM,
    media_player.Features.MEDIA_IMAGE_URL,
    media_player.Features.MEDIA_POSITION,
    media_player.Features.MEDIA_DURATION,
    media_player.Features.MEDIA_TYPE,
    media_player.Features.PLAY_MEDIA,
    media_player.Features.BROWSE_MEDIA,
]


class NADMediaPlayer(MediaPlayerEntity):
    """Media player entity for NAD receivers and amplifiers."""

    def __init__(self, device_config: NADDeviceConfig, device: NADDevice) -> None:
        self._device = device
        self._is_bluos = device_config.is_bluos

        features = list(_COMMON_FEATURES)
        device_class = media_player.DeviceClasses.RECEIVER
        attributes = {
            media_player.Attributes.STATE: media_player.States.UNKNOWN,
            media_player.Attributes.VOLUME: 0,
            media_player.Attributes.MUTED: False,
            media_player.Attributes.SOURCE: "",
            media_player.Attributes.SOURCE_LIST: [],
        }

        if self._is_bluos:
            features += _BLUOS_FEATURES
            device_class = media_player.DeviceClasses.SPEAKER
            attributes[media_player.Attributes.MEDIA_TYPE] = "music"
            attributes[media_player.Attributes.SHUFFLE] = False
            attributes[media_player.Attributes.REPEAT] = media_player.RepeatMode.OFF

        entity_id = f"media_player.{device_config.identifier}"
        super().__init__(
            entity_id,
            device_config.name,
            features=features,
            attributes=attributes,
            device_class=device_class,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        d = self._device
        if d.state == "UNAVAILABLE":
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return

        attrs: dict[str, Any] = {
            media_player.Attributes.STATE: self.map_entity_states(d.state),
            media_player.Attributes.VOLUME: d.volume,
            media_player.Attributes.MUTED: d.muted,
            media_player.Attributes.SOURCE: d.source or "",
            media_player.Attributes.SOURCE_LIST: d.source_list,
        }

        if self._is_bluos:
            attrs[media_player.Attributes.MEDIA_TYPE] = "music"
            attrs[media_player.Attributes.SHUFFLE] = d.shuffle
            attrs[media_player.Attributes.REPEAT] = _repeat_to_uc(d.repeat)
            attrs[media_player.Attributes.MEDIA_TITLE] = d.title or ""
            attrs[media_player.Attributes.MEDIA_ARTIST] = d.artist or ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = d.album or ""
            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = d.image_url or ""
            if d.position is not None:
                attrs[media_player.Attributes.MEDIA_POSITION] = d.position
            if d.duration is not None:
                attrs[media_player.Attributes.MEDIA_DURATION] = d.duration

        self.update(attrs)

    async def browse(self, options: BrowseOptions) -> BrowseResults | StatusCodes:
        if not self._is_bluos:
            return StatusCodes.NOT_IMPLEMENTED
        client = self._device.client
        if client is None or not client.is_connected:
            return StatusCodes.SERVICE_UNAVAILABLE
        return await browser.browse(self._device, options)

    async def search(self, options: SearchOptions) -> SearchResults | StatusCodes:
        return StatusCodes.NOT_IMPLEMENTED

    async def _handle_command(
        self, entity: media_player.MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        d = self._device
        if d.client is None or not d.client.is_connected:
            _LOG.warning("[%s] Device not connected, command %s rejected", self.id, cmd_id)
            return StatusCodes.SERVICE_UNAVAILABLE
        try:
            return await self._dispatch(cmd_id, params)
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _dispatch(self, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        d = self._device
        C = media_player.Commands

        if cmd_id == C.ON:
            ok = await d.turn_on()
        elif cmd_id == C.OFF:
            ok = await d.turn_off()
        elif cmd_id == C.TOGGLE:
            ok = await (d.turn_off() if d.power else d.turn_on())
        elif cmd_id == C.VOLUME:
            if not params or "volume" not in params:
                return StatusCodes.BAD_REQUEST
            ok = await d.set_volume(int(params["volume"]))
        elif cmd_id == C.VOLUME_UP:
            ok = await d.volume_up()
        elif cmd_id == C.VOLUME_DOWN:
            ok = await d.volume_down()
        elif cmd_id == C.MUTE_TOGGLE:
            ok = await d.mute_toggle()
        elif cmd_id == C.MUTE:
            ok = await d.set_mute(True)
        elif cmd_id == C.UNMUTE:
            ok = await d.set_mute(False)
        elif cmd_id == C.SELECT_SOURCE:
            source = params.get("source") if params else None
            if not source:
                return StatusCodes.BAD_REQUEST
            ok = await d.select_source(source)
        elif cmd_id in (C.PLAY_PAUSE, C.STOP, C.NEXT, C.PREVIOUS, C.SHUFFLE,
                        C.REPEAT, C.SEEK, C.PLAY_MEDIA):
            return await self._dispatch_bluos(cmd_id, params)
        else:
            return StatusCodes.NOT_IMPLEMENTED

        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR

    async def _dispatch_bluos(self, cmd_id: str, params: dict[str, Any] | None) -> StatusCodes:
        client = self._device.client
        C = media_player.Commands
        if not hasattr(client, "play_pause"):
            return StatusCodes.NOT_IMPLEMENTED

        if cmd_id == C.PLAY_PAUSE:
            ok = await client.play_pause()
        elif cmd_id == C.STOP:
            ok = await client.stop()
        elif cmd_id == C.NEXT:
            ok = await client.next_track()
        elif cmd_id == C.PREVIOUS:
            ok = await client.previous_track()
        elif cmd_id == C.SHUFFLE:
            ok = await client.set_shuffle(not client.shuffle)
        elif cmd_id == C.REPEAT:
            cycle = {"OFF": "ALL", "ALL": "ONE", "ONE": "OFF"}
            ok = await client.set_repeat(cycle.get(client.repeat, "OFF"))
        elif cmd_id == C.SEEK:
            if not params or "media_position" not in params:
                return StatusCodes.BAD_REQUEST
            ok = await client.seek(int(params["media_position"]))
        elif cmd_id == C.PLAY_MEDIA:
            return await self._handle_play_media(params)
        else:
            return StatusCodes.NOT_IMPLEMENTED
        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR

    async def _handle_play_media(self, params: dict[str, Any] | None) -> StatusCodes:
        client = self._device.client
        if not params:
            return StatusCodes.BAD_REQUEST
        media_id = params.get("media_id", "")
        if not media_id:
            return StatusCodes.BAD_REQUEST

        if media_id.startswith("preset_"):
            try:
                ok = await client.select_preset(int(media_id[7:]))
            except ValueError:
                return StatusCodes.BAD_REQUEST
        elif media_id.startswith("input_"):
            ok = await client.select_input(params.get("media_id_name", "") or media_id[6:])
        elif media_id.startswith("queue_"):
            ok = await client.play()
        else:
            ok = await client.play_url(media_id)
        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR


def _repeat_to_uc(repeat: str) -> media_player.RepeatMode:
    return {
        "OFF": media_player.RepeatMode.OFF,
        "ALL": media_player.RepeatMode.ALL,
        "ONE": media_player.RepeatMode.ONE,
    }.get(repeat, media_player.RepeatMode.OFF)

"""
BluOS media browser for NAD streaming models.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ucapi import StatusCodes
from ucapi.api_definitions import Pagination
from ucapi.media_player import (
    BrowseMediaItem,
    BrowseOptions,
    BrowseResults,
    MediaClass,
    MediaContentType,
)

if TYPE_CHECKING:
    from intg_nadav.device import NADDevice

_LOG = logging.getLogger(__name__)


async def browse(device: NADDevice, options: BrowseOptions) -> BrowseResults | StatusCodes:
    media_id = getattr(options, "media_id", None)

    if not media_id or media_id == "root":
        return _browse_root(device)
    if media_id == "inputs":
        return await _browse_inputs(device)
    if media_id == "presets":
        return await _browse_presets(device)
    if media_id == "queue":
        return await _browse_queue(device)
    return StatusCodes.NOT_FOUND


def _browse_root(device: NADDevice) -> BrowseResults:
    items = [
        BrowseMediaItem(
            title="Inputs",
            media_class=MediaClass.DIRECTORY,
            media_type="directory",
            media_id="inputs",
            can_browse=True,
            can_play=False,
            thumbnail="icon://uc:input",
        ),
        BrowseMediaItem(
            title="Presets",
            media_class=MediaClass.PLAYLIST,
            media_type="directory",
            media_id="presets",
            can_browse=True,
            can_play=False,
            thumbnail="icon://uc:music",
        ),
        BrowseMediaItem(
            title="Queue",
            media_class=MediaClass.TRACK,
            media_type="directory",
            media_id="queue",
            can_browse=True,
            can_play=False,
            thumbnail="icon://uc:music",
        ),
    ]
    return _results("NAD", "root", MediaClass.DIRECTORY, items)


async def _browse_inputs(device: NADDevice) -> BrowseResults:
    client = device.client
    inputs = client.inputs or await client.fetch_inputs()
    items = []
    for inp in inputs:
        name = inp.get("name", "")
        url = inp.get("url", "")
        if not name or not url:
            continue
        items.append(BrowseMediaItem(
            title=name,
            media_class=MediaClass.TRACK,
            media_type=MediaContentType.TRACK,
            media_id=url,
            can_browse=False,
            can_play=True,
            thumbnail=inp.get("image") or "icon://uc:input",
        ))
    return _results("Inputs", "inputs", MediaClass.DIRECTORY, items)


async def _browse_presets(device: NADDevice) -> BrowseResults:
    client = device.client
    presets = client.presets or await client.fetch_presets()
    items = []
    for preset in presets:
        preset_id = preset.get("id", "")
        name = preset.get("name", "")
        if not preset_id or not name:
            continue
        items.append(BrowseMediaItem(
            title=name,
            media_class=MediaClass.RADIO,
            media_type=MediaContentType.RADIO,
            media_id=f"preset_{preset_id}",
            can_browse=False,
            can_play=True,
            thumbnail=preset.get("image") or "icon://uc:music",
        ))
    return _results("Presets", "presets", MediaClass.PLAYLIST, items)


async def _browse_queue(device: NADDevice) -> BrowseResults:
    client = device.client
    queue = await client.fetch_queue()
    items = []
    for idx, song in enumerate(queue):
        title = song.get("title", song.get("fn", f"Track {idx + 1}"))
        song_id = song.get("songid", song.get("id", str(idx)))
        items.append(BrowseMediaItem(
            title=title,
            media_class=MediaClass.TRACK,
            media_type=MediaContentType.TRACK,
            media_id=f"queue_{song_id}",
            can_browse=False,
            can_play=True,
            thumbnail=song.get("image") or None,
            artist=song.get("art") or None,
            album=song.get("alb") or None,
        ))
    return _results("Queue", "queue", MediaClass.TRACK, items)


def _results(title: str, media_id: str, media_class, items: list) -> BrowseResults:
    return BrowseResults(
        media=BrowseMediaItem(
            title=title,
            media_class=media_class,
            media_type="directory" if media_id != "root" else "root",
            media_id=media_id,
            can_browse=True,
            items=items,
        ),
        pagination=Pagination(page=1, limit=len(items), count=len(items)),
    )

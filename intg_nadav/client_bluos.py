"""
BluOS HTTP client for NAD streaming models (M10, M33, C700, C658, ...).

BluOS players expose an HTTP API on port 11000 returning XML. This is the only
network control protocol these models support - they do NOT speak the classic
NAD telnet/RS232 command set.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp
from yarl import URL

_LOG = logging.getLogger(__name__)


class BluOSClient:
    """Async BluOS API client with parsed state and debounced volume/mute."""

    def __init__(self, host: str, port: int = 11000, log_id: str = "BluOS", volume_step: int = 5) -> None:
        self._host = host
        self._port = port
        self._log_id = log_id
        self._volume_step = volume_step
        self._base_url = f"http://{host}:{port}"
        self._session: aiohttp.ClientSession | None = None

        self._raw_state: dict[str, Any] = {}
        self._sync_status: dict[str, Any] = {}
        self._etag: str | None = None

        self._presets: list[dict[str, Any]] = []
        self._inputs: list[dict[str, Any]] = []

        self._state: str = "UNAVAILABLE"
        self._volume: int = 0
        self._muted: bool = False
        self._shuffle: bool = False
        self._repeat: str = "OFF"
        self._title: str = ""
        self._artist: str = ""
        self._album: str = ""
        self._image_url: str = ""
        self._source: str = ""
        self._model: str = ""
        self._device_name: str = ""
        self._position: int | None = None
        self._duration: int | None = None

        self._volume_queue: asyncio.Queue = asyncio.Queue()
        self._mute_queue: asyncio.Queue = asyncio.Queue()
        self._volume_worker_task: asyncio.Task | None = None
        self._mute_worker_task: asyncio.Task | None = None
        self._target_volume: int | None = None
        self._target_mute: bool | None = None
        self._volume_before_mute: int | None = None

    # ------------------------------------------------------------------ props
    @property
    def is_connected(self) -> bool:
        return self._session is not None and not self._session.closed

    @property
    def state(self) -> str:
        return self._state

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> str:
        return self._repeat

    @property
    def title(self) -> str:
        return self._title

    @property
    def artist(self) -> str:
        return self._artist

    @property
    def album(self) -> str:
        return self._album

    @property
    def image_url(self) -> str:
        return self._image_url

    @property
    def source(self) -> str:
        return self._source

    @property
    def source_list(self) -> list[str]:
        return [i["name"] for i in self._inputs if i.get("name")]

    @property
    def model(self) -> str:
        return self._model

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def position(self) -> int | None:
        return self._position

    @property
    def duration(self) -> int | None:
        return self._duration

    @property
    def presets(self) -> list[dict[str, Any]]:
        return self._presets

    @property
    def inputs(self) -> list[dict[str, Any]]:
        return self._inputs

    # ------------------------------------------------------------- lifecycle
    async def connect(self) -> None:
        """Create session, verify reachability, prime state and workers."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)

        if not await self._test_connection():
            await self.close()
            raise ConnectionError(f"Cannot reach BluOS device at {self._host}:{self._port}")

        try:
            await self.refresh()
        except ConnectionError:
            _LOG.warning("[%s] Initial BluOS state query failed, using defaults", self._log_id)

        await self.fetch_sync_status()
        self._presets = await self.fetch_presets()
        self._inputs = await self.fetch_inputs()

        if self._volume_worker_task is None:
            self._volume_worker_task = asyncio.create_task(self._volume_worker())
        if self._mute_worker_task is None:
            self._mute_worker_task = asyncio.create_task(self._mute_worker())
        self._state = "ON"

    async def close(self) -> None:
        for task_attr in ("_volume_worker_task", "_mute_worker_task"):
            task = getattr(self, task_attr)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_attr, None)

        self._volume_queue = asyncio.Queue()
        self._mute_queue = asyncio.Queue()
        self._target_volume = None
        self._target_mute = None
        self._volume_before_mute = None
        self._etag = None

        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._raw_state = {}
        self._state = "UNAVAILABLE"

    async def _test_connection(self) -> bool:
        try:
            async with self._session.get(
                f"{self._base_url}/Status", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    # --------------------------------------------------------------- polling
    async def refresh(self) -> None:
        """Fetch Status + SyncStatus and update parsed state. Raise on failure."""
        await self._fetch_status()
        await self.fetch_sync_status()
        if not self._raw_state:
            raise ConnectionError("Failed to get BluOS status")
        self._parse_state()

    async def _fetch_status(self) -> bool:
        try:
            params = {"etag": self._etag, "timeout": "5"} if self._etag else {}
            async with self._session.get(f"{self._base_url}/Status", params=params) as resp:
                if resp.status != 200:
                    return False
                new_state = self._parse_xml(await resp.text())
                if "etag" in new_state:
                    self._etag = new_state["etag"]
                if new_state != self._raw_state:
                    self._raw_state = new_state
                    return True
                return False
        except asyncio.TimeoutError:
            return False
        except Exception as err:
            raise ConnectionError(f"Status fetch failed: {err}") from err

    async def fetch_sync_status(self) -> None:
        try:
            async with self._session.get(f"{self._base_url}/SyncStatus") as resp:
                if resp.status == 200:
                    self._sync_status = self._parse_xml(await resp.text())
                    self._model = self._sync_status.get("modelName", self._sync_status.get("model", "")) or self._model
                    self._device_name = self._sync_status.get("name", "") or self._device_name
        except Exception as err:
            _LOG.debug("[%s] SyncStatus fetch error: %s", self._log_id, err)

    def _parse_state(self) -> None:
        state_str = self._raw_state.get("state", "").lower()
        if state_str in ("play", "stream"):
            self._state = "PLAYING"
        elif state_str == "pause":
            self._state = "PAUSED"
        else:
            self._state = "ON"

        self._volume = int(self._raw_state.get("volume", "0") or 0)
        self._muted = self._raw_state.get("mute", "0") == "1"
        self._shuffle = self._raw_state.get("shuffle", "0") == "1"

        repeat_val = self._raw_state.get("repeat", "0")
        self._repeat = {"2": "ONE", "1": "ALL"}.get(repeat_val, "OFF")

        self._title = self._raw_state.get("title1", self._raw_state.get("name", ""))
        self._artist = self._raw_state.get("artist", self._raw_state.get("title2", ""))
        self._album = self._raw_state.get("album", self._raw_state.get("title3", ""))
        image = self._raw_state.get("image", "")
        self._image_url = self._absolute_url(image)
        self._source = self._resolve_source()

        self._position = self._to_int(self._raw_state.get("secs"))
        self._duration = self._to_int(self._raw_state.get("totlen"))

    def _resolve_source(self) -> str:
        """Friendly name of the active input/service."""
        service = self._raw_state.get("service", "")
        input_id = self._raw_state.get("inputId", "")
        if service == "Capture" and input_id:
            for item in self._inputs:
                if item.get("id") == input_id:
                    return item.get("name", input_id)
            return self._raw_state.get("title1", input_id)
        return service or ""

    def _absolute_url(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base_url}{path}"

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _parse_xml(self, xml_text: str) -> dict[str, Any]:
        try:
            root = ET.fromstring(xml_text)
            state: dict[str, Any] = {}
            state.update(root.attrib)
            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if elem.text and elem.text.strip():
                    state[tag] = elem.text.strip()
                for attr_name, attr_value in elem.attrib.items():
                    state[f"{tag}_{attr_name}"] = attr_value
            return state
        except Exception as err:
            _LOG.error("[%s] XML parse error: %s", self._log_id, err)
            return {}

    # ----------------------------------------------------------- browse data
    async def fetch_presets(self) -> list[dict[str, Any]]:
        try:
            async with self._session.get(f"{self._base_url}/Presets") as resp:
                if resp.status != 200:
                    return []
                root = ET.fromstring(await resp.text())
                presets = []
                for preset in root.findall(".//preset"):
                    data = {
                        "id": preset.get("id"),
                        "name": preset.get("name"),
                        "url": preset.get("url"),
                        "image": self._absolute_url(preset.get("image", "")),
                    }
                    if data["id"] and data["name"]:
                        presets.append(data)
                return presets
        except Exception as err:
            _LOG.debug("[%s] Presets fetch error: %s", self._log_id, err)
            return []

    async def fetch_inputs(self) -> list[dict[str, Any]]:
        """List selectable inputs via RadioBrowse?service=Capture."""
        try:
            async with self._session.get(
                f"{self._base_url}/RadioBrowse", params={"service": "Capture"}
            ) as resp:
                if resp.status != 200:
                    return []
                root = ET.fromstring(await resp.text())
                inputs = []
                for item in root.findall(".//item"):
                    url = item.get("URL")
                    name = item.get("text")
                    if not url or not name:
                        continue
                    inputs.append({
                        "id": item.get("id", ""),
                        "name": name,
                        "url": url,
                        "image": self._absolute_url(item.get("image", "")),
                        "input_type": item.get("inputType", ""),
                    })
                return inputs
        except Exception as err:
            _LOG.debug("[%s] Inputs fetch error: %s", self._log_id, err)
            return []

    async def fetch_queue(self) -> list[dict[str, Any]]:
        try:
            async with self._session.get(f"{self._base_url}/Playlist") as resp:
                if resp.status != 200:
                    return []
                root = ET.fromstring(await resp.text())
                items = []
                for song in root.findall(".//song"):
                    data: dict[str, Any] = dict(song.attrib)
                    for elem in song:
                        if elem.text and elem.text.strip():
                            data[elem.tag] = elem.text.strip()
                    if data.get("title") or data.get("fn"):
                        items.append(data)
                return items
        except Exception as err:
            _LOG.debug("[%s] Queue fetch error: %s", self._log_id, err)
            return []

    # ---------------------------------------------------------------- commands
    async def _send(self, endpoint: str, params: dict[str, Any] | None = None) -> bool:
        if not self.is_connected:
            return False
        try:
            async with self._session.get(f"{self._base_url}/{endpoint}", params=params or {}) as resp:
                return resp.status == 200
        except Exception as err:
            _LOG.error("[%s] Command %s error: %s", self._log_id, endpoint, err)
            return False

    async def _send_encoded(self, endpoint: str, query: str) -> bool:
        """Send a request whose query is already percent-encoded (BluOS input URLs)."""
        if not self.is_connected:
            return False
        try:
            url = URL(f"{self._base_url}/{endpoint}?{query}", encoded=True)
            async with self._session.get(url) as resp:
                return resp.status == 200
        except Exception as err:
            _LOG.error("[%s] Encoded command %s error: %s", self._log_id, endpoint, err)
            return False

    async def play(self) -> bool:
        return await self._send("Play")

    async def pause(self) -> bool:
        return await self._send("Pause")

    async def stop(self) -> bool:
        return await self._send("Stop")

    async def play_pause(self) -> bool:
        return await self._send("Pause", {"toggle": "1"})

    async def next_track(self) -> bool:
        return await self._send("Skip")

    async def previous_track(self) -> bool:
        return await self._send("Back")

    async def set_volume(self, volume: int) -> bool:
        volume = max(0, min(100, volume))
        await self._volume_queue.put(volume)
        return True

    async def volume_up(self) -> bool:
        current = self._target_volume if self._target_volume is not None else self._volume
        self._target_volume = min(100, current + self._volume_step)
        return await self.set_volume(self._target_volume)

    async def volume_down(self) -> bool:
        current = self._target_volume if self._target_volume is not None else self._volume
        self._target_volume = max(0, current - self._volume_step)
        return await self.set_volume(self._target_volume)

    async def set_mute(self, muted: bool) -> bool:
        await self._mute_queue.put(muted)
        return True

    async def mute_toggle(self) -> bool:
        current = self._target_mute if self._target_mute is not None else self._muted
        self._target_mute = not current
        return await self.set_mute(self._target_mute)

    async def set_shuffle(self, shuffle: bool) -> bool:
        return await self._send("Shuffle", {"state": "1" if shuffle else "0"})

    async def set_repeat(self, repeat: str) -> bool:
        value = {"OFF": "0", "ALL": "1", "ONE": "2"}.get(repeat.upper(), "0")
        return await self._send("Repeat", {"state": value})

    async def seek(self, position: int) -> bool:
        return await self._send("Play", {"seek": str(position)})

    async def select_preset(self, preset_id: int) -> bool:
        return await self._send("Preset", {"id": str(preset_id)})

    async def play_url(self, url: str) -> bool:
        return await self._send_encoded("Play", f"url={url}")

    async def select_input(self, name: str) -> bool:
        """Select a physical/streaming input by its friendly name."""
        for item in self._inputs:
            if item.get("name") == name:
                return await self.play_url(item["url"])
        _LOG.warning("[%s] Input '%s' not found in %s", self._log_id, name,
                     [i.get("name") for i in self._inputs])
        return False

    # ----------------------------------------------------------------- workers
    async def _volume_worker(self) -> None:
        while True:
            try:
                volume = await self._volume_queue.get()
                while not self._volume_queue.empty():
                    try:
                        volume = self._volume_queue.get_nowait()
                        self._volume_queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                await self._send("Volume", {"level": str(volume)})
                await asyncio.sleep(0.05)
                self._volume_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOG.error("[%s] Volume worker error: %s", self._log_id, err)

    async def _mute_worker(self) -> None:
        while True:
            try:
                mute_value = await self._mute_queue.get()
                while not self._mute_queue.empty():
                    try:
                        mute_value = self._mute_queue.get_nowait()
                        self._mute_queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                await self._send("Volume", {"mute": "1" if mute_value else "0"})
                await asyncio.sleep(0.05)
                self._mute_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOG.error("[%s] Mute worker error: %s", self._log_id, err)

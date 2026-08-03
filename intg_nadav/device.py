"""
NAD device implementation for Unfolded Circle integration.

Routes between two transport families:
- BluOS streaming models (M10, M33, C700, C658) via the BluOS HTTP API.
- Classic T-Series (Telnet), D-Series (TCP) and RS-232 models via nad_receiver.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi_framework import DeviceEvents, PollingDevice

from intg_nadav.client_bluos import BluOSClient
from intg_nadav.client_classic import ClassicNADClient
from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class NADDevice(PollingDevice):
    """NAD receiver/amplifier device using the polling pattern."""

    def __init__(self, device_config: NADDeviceConfig, **kwargs: Any) -> None:
        poll_interval = 5 if device_config.is_bluos else 10
        super().__init__(device_config, poll_interval=poll_interval, **kwargs)
        self._device_config = device_config
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._client: BluOSClient | ClassicNADClient | None = None
        self._refresh_counter = 0

    # ------------------------------------------------------------------ meta
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str | None:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address or self._device_config.serial_port})"

    @property
    def is_bluos(self) -> bool:
        return self._device_config.is_bluos

    @property
    def client(self) -> BluOSClient | ClassicNADClient | None:
        return self._client

    @property
    def state(self) -> str:
        return self._client.state if self._client else "UNAVAILABLE"

    # --------------------------------------------------------- shared state
    @property
    def volume(self) -> int:
        return self._client.volume if self._client else 0

    @property
    def muted(self) -> bool:
        return self._client.muted if self._client else False

    @property
    def source(self) -> str | None:
        return self._client.source if self._client else None

    @property
    def source_list(self) -> list[str]:
        return self._client.source_list if self._client else []

    @property
    def model(self) -> str | None:
        return self._client.model if self._client else None

    @property
    def power(self) -> bool:
        if not self._client:
            return False
        if self.is_bluos:
            return self._client.state in ("ON", "PLAYING", "PAUSED")
        return self._client.power

    # ------------------------------------------------------- BluOS-only state
    @property
    def title(self) -> str:
        return self._client.title if isinstance(self._client, BluOSClient) else ""

    @property
    def artist(self) -> str:
        return self._client.artist if isinstance(self._client, BluOSClient) else ""

    @property
    def album(self) -> str:
        return self._client.album if isinstance(self._client, BluOSClient) else ""

    @property
    def image_url(self) -> str:
        return self._client.image_url if isinstance(self._client, BluOSClient) else ""

    @property
    def shuffle(self) -> bool:
        return self._client.shuffle if isinstance(self._client, BluOSClient) else False

    @property
    def repeat(self) -> str:
        return self._client.repeat if isinstance(self._client, BluOSClient) else "OFF"

    @property
    def position(self) -> int | None:
        return self._client.position if isinstance(self._client, BluOSClient) else None

    @property
    def duration(self) -> int | None:
        return self._client.duration if isinstance(self._client, BluOSClient) else None

    @property
    def presets(self) -> list[dict[str, Any]]:
        return self._client.presets if isinstance(self._client, BluOSClient) else []

    @property
    def inputs(self) -> list[dict[str, Any]]:
        return self._client.inputs if isinstance(self._client, BluOSClient) else []

    # ----------------------------------------------------- classic-only state
    @property
    def version(self) -> str | None:
        return self._client.version if isinstance(self._client, ClassicNADClient) else None

    @property
    def speaker_a(self) -> str:
        return self._client.speaker_a if isinstance(self._client, ClassicNADClient) else "Off"

    @property
    def speaker_b(self) -> str:
        return self._client.speaker_b if isinstance(self._client, ClassicNADClient) else "Off"

    # -------------------------------------------------------------- lifecycle
    def _create_client(self) -> BluOSClient | ClassicNADClient:
        if self.is_bluos:
            return BluOSClient(
                self._device_config.host,
                self._device_config.port,
                self.log_id,
                self._device_config.volume_step,
            )
        return ClassicNADClient(self._device_config, self.log_id)

    async def establish_connection(self) -> BluOSClient | ClassicNADClient:
        async with self._connect_lock:
            if self._client is None:
                self._client = self._create_client()
            if not self._client.is_connected:
                await self._client.connect()
            _LOG.info("[%s] Connection established", self.log_id)
            return self._client

    async def poll_device(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.refresh()
            if isinstance(self._client, BluOSClient):
                self._refresh_counter += 1
                if self._refresh_counter % 12 == 0:
                    self._client._presets = await self._client.fetch_presets()
                    self._client._inputs = await self._client.fetch_inputs()
            self.push_update()
        except Exception as err:
            _LOG.debug("[%s] Poll error: %s", self.log_id, err)
            if self._client and self.state != "UNAVAILABLE":
                self._client._state = "UNAVAILABLE"
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def disconnect(self) -> None:
        async with self._connect_lock:
            if self._client:
                await self._client.close()
                self._client = None
        await super().disconnect()

    # --------------------------------------------------------- shared commands
    async def turn_on(self) -> bool:
        if not self._client:
            return False
        if isinstance(self._client, BluOSClient):
            return await self._client.play()
        return await self._client.turn_on()

    async def turn_off(self) -> bool:
        if not self._client:
            return False
        if isinstance(self._client, BluOSClient):
            return await self._client.pause()
        return await self._client.turn_off()

    async def set_volume(self, volume: int) -> bool:
        return await self._client.set_volume(volume) if self._client else False

    async def volume_up(self) -> bool:
        return await self._client.volume_up() if self._client else False

    async def volume_down(self) -> bool:
        return await self._client.volume_down() if self._client else False

    async def set_mute(self, mute: bool) -> bool:
        return await self._client.set_mute(mute) if self._client else False

    async def mute_toggle(self) -> bool:
        if not self._client:
            return False
        if isinstance(self._client, BluOSClient):
            return await self._client.mute_toggle()
        return await self._client.set_mute(not self._client.muted)

    async def select_source(self, source: str) -> bool:
        if not self._client:
            return False
        if isinstance(self._client, BluOSClient):
            return await self._client.select_input(source)
        return await self._client.select_source(source)

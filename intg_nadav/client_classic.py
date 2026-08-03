"""
Classic NAD control client for T-Series (Telnet), D-Series (TCP) and RS-232 models.

Wraps the synchronous `nad_receiver` library with async execution and automatic
reconnection. These models speak the classic NAD Main.* command set.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Callable

from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class ClassicNADClient:
    """Classic NAD receiver/amplifier client (Telnet/TCP/RS232)."""

    def __init__(self, config: NADDeviceConfig, log_id: str = "NAD") -> None:
        self._config = config
        self._log_id = log_id
        self._receiver = None

        self._state: str = "UNAVAILABLE"
        self._power: bool = False
        self._volume: int = 0
        self._muted: bool = False
        self._source: str | None = None
        self._source_list: list[str] = []
        self._model: str | None = None
        self._version: str | None = None
        self._speaker_a: str = "Off"
        self._speaker_b: str = "Off"

        self._min_vol_nad = (config.min_volume + 90) * 2
        self._max_vol_nad = (config.max_volume + 90) * 2

    # ------------------------------------------------------------------ props
    @property
    def is_connected(self) -> bool:
        return self._receiver is not None

    @property
    def state(self) -> str:
        return self._state

    @property
    def power(self) -> bool:
        return self._power

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def source(self) -> str | None:
        return self._source

    @property
    def source_list(self) -> list[str]:
        return self._source_list

    @property
    def model(self) -> str | None:
        return self._model

    @property
    def version(self) -> str | None:
        return self._version

    @property
    def speaker_a(self) -> str:
        return self._speaker_a

    @property
    def speaker_b(self) -> str:
        return self._speaker_b

    @property
    def _is_tcp(self) -> bool:
        return self._config.connection_type == "TCP"

    # ------------------------------------------------------------- lifecycle
    async def connect(self) -> None:
        await self._create_receiver()
        try:
            await asyncio.wait_for(self.refresh(), timeout=5.0)
        except asyncio.TimeoutError:
            _LOG.warning("[%s] Initial poll timed out", self._log_id)
        except Exception as err:
            _LOG.warning("[%s] Initial poll failed: %s", self._log_id, err)
        await self._query_model_version()
        self._state = "ON"

    async def close(self) -> None:
        try:
            if self._receiver and hasattr(self._receiver, "transport") and self._receiver.transport:
                self._receiver.transport.close()
        except Exception:
            pass
        self._receiver = None
        self._state = "UNAVAILABLE"

    async def _create_receiver(self) -> None:
        from nad_receiver import NADReceiver, NADReceiverTCP, NADReceiverTelnet

        cfg = self._config
        if self._receiver:
            await self.close()

        if cfg.connection_type == "TCP":
            _LOG.info("[%s] Creating TCP client for %s", self._log_id, cfg.host)
            self._receiver = NADReceiverTCP(cfg.host)
            try:
                self._source_list = self._receiver.available_sources()
            except Exception:
                self._source_list = []
        elif cfg.connection_type == "Telnet":
            _LOG.info("[%s] Creating Telnet client for %s:%d", self._log_id, cfg.host, cfg.port)
            self._receiver = NADReceiverTelnet(cfg.host, cfg.port)
            self._source_list = list(cfg.sources.values()) if cfg.sources else []
        else:
            _LOG.info("[%s] Creating RS232 client for %s", self._log_id, cfg.serial_port)
            self._receiver = NADReceiver(cfg.serial_port)
            self._source_list = list(cfg.sources.values()) if cfg.sources else []

    async def _run(self, func: Callable, *args, **kwargs) -> Any:
        """Run a blocking receiver call, reconnecting once on connection loss."""
        if self._receiver is None:
            await self._create_receiver()
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except (BrokenPipeError, OSError, EOFError) as err:
            _LOG.warning("[%s] Connection lost (%s), reconnecting", self._log_id, err)
            await self._create_receiver()
            return await asyncio.to_thread(func, *args, **kwargs)

    # --------------------------------------------------------------- polling
    async def refresh(self) -> None:
        if self._receiver is None:
            raise ConnectionError("Not connected")
        if self._is_tcp:
            await self._refresh_tcp()
        else:
            await self._refresh_serial()

    async def _refresh_tcp(self) -> None:
        status = await self._run(self._receiver.status)
        if status is None:
            raise ConnectionError("No status from TCP device")
        self._power = status.get("power", False)
        self._muted = status.get("muted", False)
        self._source = status.get("source")
        self._volume = self._nad_vol_to_percent(status.get("volume", 0))
        self._state = "ON" if self._power else "OFF"

    async def _refresh_serial(self) -> None:
        power_state = await self._run(self._receiver.main_power, "?")
        if not power_state:
            self._power = False
            self._state = "OFF"
            return

        self._power = power_state == "On"
        self._state = "ON" if self._power else "OFF"
        if not self._power:
            return

        mute_state = await self._run(self._receiver.main_mute, "?")
        self._muted = mute_state == "On"

        volume_db = await self._run(self._receiver.main_volume, "?")
        if volume_db is not None:
            self._volume = self._db_to_percent(volume_db)

        if self._config.sources:
            try:
                source_num = await self._run(self._receiver.main_source, "?")
                if source_num is not None:
                    source_num = int(source_num)
                    self._source = self._config.sources.get(source_num, f"Source {source_num}")
            except Exception as err:
                _LOG.debug("[%s] Source query error: %s", self._log_id, err)

        for attr, method in (("_speaker_a", "main_speaker_a"), ("_speaker_b", "main_speaker_b")):
            try:
                value = await self._run(getattr(self._receiver, method), "?")
                if value:
                    setattr(self, attr, value)
            except Exception as err:
                _LOG.debug("[%s] %s query error: %s", self._log_id, method, err)

    async def _query_model_version(self) -> None:
        if self._is_tcp:
            return
        try:
            model = await self._run(self._receiver.main_model, "?")
            if model:
                self._model = model
        except Exception as err:
            _LOG.debug("[%s] Model query error: %s", self._log_id, err)
        try:
            version = await self._run(self._receiver.main_version, "?")
            if version:
                self._version = version
        except Exception as err:
            _LOG.debug("[%s] Version query error: %s", self._log_id, err)

    # -------------------------------------------------------------- commands
    async def turn_on(self) -> bool:
        if self._is_tcp:
            await self._run(self._receiver.power_on)
        else:
            await self._run(self._receiver.main_power, "=", "On")
        self._power = True
        self._state = "ON"
        return True

    async def turn_off(self) -> bool:
        if self._is_tcp:
            await self._run(self._receiver.power_off)
        else:
            await self._run(self._receiver.main_power, "=", "Off")
        self._power = False
        self._state = "OFF"
        return True

    async def set_volume(self, volume: int) -> bool:
        if self._is_tcp:
            await self._run(self._receiver.set_volume, self._percent_to_nad_vol(volume))
        else:
            await self._run(self._receiver.main_volume, "=", self._percent_to_db(volume))
        self._volume = volume
        return True

    async def volume_up(self) -> bool:
        step = self._config.volume_step
        if self._is_tcp:
            await self._run(self._receiver.set_volume, self._percent_to_nad_vol(min(100, self._volume + step)))
        else:
            for _ in range(step):
                await self._run(self._receiver.main_volume, "+")
        self._volume = min(100, self._volume + step)
        return True

    async def volume_down(self) -> bool:
        step = self._config.volume_step
        if self._is_tcp:
            await self._run(self._receiver.set_volume, self._percent_to_nad_vol(max(0, self._volume - step)))
        else:
            for _ in range(step):
                await self._run(self._receiver.main_volume, "-")
        self._volume = max(0, self._volume - step)
        return True

    async def set_mute(self, mute: bool) -> bool:
        if self._is_tcp:
            await self._run(self._receiver.mute if mute else self._receiver.unmute)
        else:
            await self._run(self._receiver.main_mute, "=", "On" if mute else "Off")
        self._muted = mute
        return True

    async def select_source(self, source: str) -> bool:
        if self._is_tcp:
            await self._run(self._receiver.select_source, source)
            self._source = source
            return True

        source_num = None
        if self._config.sources:
            for num, name in self._config.sources.items():
                if name == source:
                    source_num = num
                    break
        if source_num is None:
            _LOG.error("[%s] Source '%s' not configured", self._log_id, source)
            return False
        await self._run(self._receiver.main_source, "=", source_num)
        self._source = source
        return True

    async def set_speaker_a(self, state: str) -> bool:
        if self._is_tcp:
            return False
        await self._run(self._receiver.main_speaker_a, "=", state)
        self._speaker_a = state
        return True

    async def set_speaker_b(self, state: str) -> bool:
        if self._is_tcp:
            return False
        await self._run(self._receiver.main_speaker_b, "=", state)
        self._speaker_b = state
        return True

    async def set_listening_mode(self, mode: str) -> bool:
        if self._is_tcp:
            return False
        await self._run(self._receiver.main_listeningmode, "+")
        return True

    # --------------------------------------------------------------- scaling
    def _nad_vol_to_percent(self, nad_vol: int) -> int:
        if nad_vol < self._min_vol_nad:
            return 0
        if nad_vol > self._max_vol_nad:
            return 100
        span = self._max_vol_nad - self._min_vol_nad
        return int(((nad_vol - self._min_vol_nad) / span) * 100) if span else 0

    def _percent_to_nad_vol(self, percent: int) -> int:
        span = self._max_vol_nad - self._min_vol_nad
        return int((percent / 100) * span + self._min_vol_nad)

    def _db_to_percent(self, db: float) -> int:
        span = self._config.max_volume - self._config.min_volume
        return int(((db - self._config.min_volume) / span) * 100) if span else 0

    def _percent_to_db(self, percent: int) -> int:
        span = self._config.max_volume - self._config.min_volume
        return int((percent / 100) * span + self._config.min_volume)

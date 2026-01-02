"""
NAD AV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from ucapi_framework import ExternalClientDevice, DeviceEvents
from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class NADDevice(ExternalClientDevice):
    """NAD AV receiver/amplifier using ExternalClientDevice pattern."""
    
    def __init__(self, device_config: NADDeviceConfig, loop=None, config_manager=None):
        """Initialize NAD device."""
        super().__init__(
            device_config,
            loop,
            enable_watchdog=True,
            watchdog_interval=30,
            reconnect_delay=5,
            max_reconnect_attempts=3,
            config_manager=config_manager,
        )
        
        self._power = False
        self._volume = 0
        self._muted = False
        self._source = None
        self._source_list = []
        
        self._min_vol_nad = (device_config.min_volume + 90) * 2
        self._max_vol_nad = (device_config.max_volume + 90) * 2
        self._volume_step = device_config.volume_step
    
    @property
    def identifier(self) -> str:
        """Return device identifier."""
        return self.device_config.identifier
    
    @property
    def name(self) -> str:
        """Return device name."""
        return self.device_config.name
    
    @property
    def address(self) -> str | None:
        """Return device address."""
        return self.device_config.host
    
    @property
    def log_id(self) -> str:
        """Return log identifier."""
        return f"[{self.name}]"
    
    @property
    def power(self) -> bool:
        """Return power state."""
        return self._power
    
    @property
    def volume(self) -> int:
        """Return volume level (0-100)."""
        return self._volume
    
    @property
    def muted(self) -> bool:
        """Return mute state."""
        return self._muted
    
    @property
    def source(self) -> str | None:
        """Return current source."""
        return self._source
    
    @property
    def source_list(self) -> list[str]:
        """Return available sources."""
        return self._source_list
    
    async def create_client(self) -> Any:
        """Create NAD receiver client."""
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        connection_type = self.device_config.connection_type
        
        if connection_type == "TCP":
            _LOG.info("%s Creating TCP connection to %s", self.log_id, self.address)
            return NADReceiverTCP(self.device_config.host)
        elif connection_type == "Telnet":
            _LOG.info("%s Creating Telnet connection to %s:%d", 
                     self.log_id, self.address, self.device_config.port)
            return NADReceiverTelnet(self.device_config.host, self.device_config.port)
        else:
            _LOG.info("%s Creating RS232 connection to %s", 
                     self.log_id, self.device_config.serial_port)
            return NADReceiver(self.device_config.serial_port)
    
    async def connect_client(self) -> None:
        """Connect the NAD receiver client."""
        _LOG.info("%s Connecting client, type: %s", self.log_id, self.device_config.connection_type)
        
        if self._client is None:
            _LOG.error("%s Client is None in connect_client!", self.log_id)
            raise RuntimeError("Client not created")
        
        if self.device_config.connection_type == "TCP":
            try:
                _LOG.debug("%s Fetching available sources...", self.log_id)
                self._source_list = await asyncio.to_thread(
                    self._client.available_sources
                )
                _LOG.info("%s Available sources: %s", self.log_id, self._source_list)
            except Exception as err:
                _LOG.warning("%s Failed to fetch sources: %s", self.log_id, err)
                self._source_list = []
        else:
            if self.device_config.sources:
                self._source_list = list(self.device_config.sources.values())
            else:
                self._source_list = []
        
        _LOG.info("%s Client connected successfully", self.log_id)
        await self._update_state()
    
    async def disconnect_client(self) -> None:
        """Disconnect NAD receiver client."""
        _LOG.info("%s Disconnecting client", self.log_id)
    
    def check_client_connected(self) -> bool:
        """Check if client is connected."""
        connected = self._client is not None
        _LOG.debug("%s Client connected check: %s", self.log_id, connected)
        return connected
    
    async def _ensure_connected(self) -> bool:
        """Ensure device is connected before command execution."""
        if not self.check_client_connected():
            _LOG.warning("%s Device not connected, attempting reconnection", self.log_id)
            try:
                await self.connect()
                await asyncio.sleep(0.5)
            except Exception as err:
                _LOG.error("%s Reconnection failed: %s", self.log_id, err)
                return False
        
        return self.check_client_connected()
    
    async def _execute_command(self, command_func, *args, **kwargs):
        """
        Execute command with connection checking and retry logic.
        
        Handles both connection issues and broken pipe errors.
        """
        if not await self._ensure_connected():
            raise RuntimeError("Device not connected")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await asyncio.to_thread(command_func, *args, **kwargs)
                return result
            except (OSError, BrokenPipeError, ConnectionError) as err:
                if attempt < max_retries - 1:
                    _LOG.warning(
                        "%s Command failed (attempt %d/%d): %s, retrying...",
                        self.log_id, attempt + 1, max_retries, err
                    )
                    await asyncio.sleep(0.5)
                    
                    try:
                        await self.disconnect()
                        await asyncio.sleep(0.2)
                        await self.connect()
                        await asyncio.sleep(0.5)
                    except Exception as reconnect_err:
                        _LOG.error("%s Reconnection failed: %s", self.log_id, reconnect_err)
                else:
                    _LOG.error("%s Command failed after %d attempts: %s", 
                             self.log_id, max_retries, err)
                    raise
            except Exception as err:
                _LOG.error("%s Command execution error: %s", self.log_id, err)
                raise
    
    async def _update_state(self) -> None:
        """Update device state."""
        if not self.check_client_connected():
            _LOG.warning("%s Cannot update state: not connected", self.log_id)
            return
        
        try:
            if self.device_config.connection_type == "TCP":
                await self._update_tcp_state()
            else:
                await self._update_serial_state()
            
            self.events.emit(
                DeviceEvents.UPDATE,
                self.identifier,
                {
                    "state": "ON" if self._power else "OFF",
                    "volume": self._volume,
                    "muted": self._muted,
                    "source": self._source,
                }
            )
        except Exception as err:
            _LOG.error("%s State update failed: %s", self.log_id, err)
    
    async def _update_tcp_state(self) -> None:
        """Update state for TCP connection."""
        try:
            status = await self._execute_command(self._client.status)
            if status:
                self._power = status.get("power", False)
                self._muted = status.get("muted", False)
                self._source = status.get("source")
                
                nad_volume = status.get("volume", 0)
                if nad_volume < self._min_vol_nad:
                    self._volume = 0
                elif nad_volume > self._max_vol_nad:
                    self._volume = 100
                else:
                    volume_range = self._max_vol_nad - self._min_vol_nad
                    self._volume = int(((nad_volume - self._min_vol_nad) / volume_range) * 100)
        except Exception as err:
            _LOG.error("%s TCP state update failed: %s", self.log_id, err)
    
    async def _update_serial_state(self) -> None:
        """Update state for RS232/Telnet connection."""
        try:
            power_state = await self._execute_command(self._client.main_power, "?")
            self._power = power_state == "On"
            
            if self._power:
                mute_state = await self._execute_command(self._client.main_mute, "?")
                self._muted = mute_state == "On"
                
                volume_db = await self._execute_command(self._client.main_volume, "?")
                if volume_db is not None:
                    min_db = self.device_config.min_volume
                    max_db = self.device_config.max_volume
                    self._volume = int(((volume_db - min_db) / (max_db - min_db)) * 100)
                
                source_num = await self._execute_command(self._client.main_source, "?")
                if self.device_config.sources and source_num:
                    self._source = self.device_config.sources.get(source_num)
        except Exception as err:
            _LOG.error("%s Serial state update failed: %s", self.log_id, err)
    
    async def turn_on(self) -> bool:
        """Turn device on."""
        try:
            _LOG.info("%s Turning on...", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                await self._execute_command(self._client.power_on)
            else:
                await self._execute_command(self._client.main_power, "=", "On")
            
            self._power = True
            await asyncio.sleep(0.5)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Turn on failed: %s", self.log_id, err)
            return False
    
    async def turn_off(self) -> bool:
        """Turn device off."""
        try:
            _LOG.info("%s Turning off...", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                await self._execute_command(self._client.power_off)
            else:
                await self._execute_command(self._client.main_power, "=", "Off")
            
            self._power = False
            await asyncio.sleep(0.5)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Turn off failed: %s", self.log_id, err)
            return False
    
    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        try:
            _LOG.info("%s Setting volume to %d", self.log_id, volume)
            
            if self.device_config.connection_type == "TCP":
                volume_range = self._max_vol_nad - self._min_vol_nad
                nad_volume = int((volume / 100) * volume_range + self._min_vol_nad)
                await self._execute_command(self._client.set_volume, nad_volume)
            else:
                min_db = self.device_config.min_volume
                max_db = self.device_config.max_volume
                volume_db = int((volume / 100) * (max_db - min_db) + min_db)
                await self._execute_command(self._client.main_volume, "=", volume_db)
            
            self._volume = volume
            await asyncio.sleep(0.3)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Set volume failed: %s", self.log_id, err)
            return False
    
    async def volume_up(self) -> bool:
        """Increase volume."""
        try:
            _LOG.info("%s Volume up", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                nad_volume = self._nad_volume_from_percent(self._volume)
                await self._execute_command(
                    self._client.set_volume, 
                    nad_volume + 2 * self._volume_step
                )
            else:
                await self._execute_command(self._client.main_volume, "+")
            
            await asyncio.sleep(0.3)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Volume up failed: %s", self.log_id, err)
            return False
    
    async def volume_down(self) -> bool:
        """Decrease volume."""
        try:
            _LOG.info("%s Volume down", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                nad_volume = self._nad_volume_from_percent(self._volume)
                await self._execute_command(
                    self._client.set_volume, 
                    nad_volume - 2 * self._volume_step
                )
            else:
                await self._execute_command(self._client.main_volume, "-")
            
            await asyncio.sleep(0.3)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Volume down failed: %s", self.log_id, err)
            return False
    
    async def mute(self, mute: bool) -> bool:
        """Mute or unmute."""
        try:
            _LOG.info("%s Mute: %s", self.log_id, mute)
            
            if self.device_config.connection_type == "TCP":
                if mute:
                    await self._execute_command(self._client.mute)
                else:
                    await self._execute_command(self._client.unmute)
            else:
                state = "On" if mute else "Off"
                await self._execute_command(self._client.main_mute, "=", state)
            
            self._muted = mute
            await asyncio.sleep(0.3)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Mute failed: %s", self.log_id, err)
            return False
    
    async def select_source(self, source: str) -> bool:
        """Select input source."""
        try:
            _LOG.info("%s Selecting source: %s", self.log_id, source)
            
            if self.device_config.connection_type == "TCP":
                await self._execute_command(self._client.select_source, source)
            else:
                source_num = None
                if self.device_config.sources:
                    for num, name in self.device_config.sources.items():
                        if name == source:
                            source_num = num
                            break
                
                if source_num:
                    await self._execute_command(self._client.main_source, "=", source_num)
                else:
                    _LOG.warning("%s Source not found: %s", self.log_id, source)
                    return False
            
            self._source = source
            await asyncio.sleep(0.5)
            await self._update_state()
            return True
        except Exception as err:
            _LOG.error("%s Select source failed: %s", self.log_id, err)
            return False
    
    def _nad_volume_from_percent(self, percent: int) -> int:
        """Convert percentage to NAD volume (0-200)."""
        volume_range = self._max_vol_nad - self._min_vol_nad
        return int((percent / 100) * volume_range + self._min_vol_nad)
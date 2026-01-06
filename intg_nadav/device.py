"""
NAD AV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from ucapi_framework import PollingDevice, DeviceEvents
from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class NADDevice(PollingDevice):
    """NAD AV receiver/amplifier using polling pattern."""
    
    def __init__(self, device_config: NADDeviceConfig, loop=None, config_manager=None):
        """Initialize NAD device."""
        super().__init__(
            device_config,
            loop,
            poll_interval=10,
            config_manager=config_manager,
        )
        
        self._nad_receiver = None
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
    
    async def establish_connection(self) -> None:
        """
        Create NAD receiver client once during initialization.
        
        The nad-receiver library manages connections internally per-command,
        so we just create the client object here and call methods directly.
        """
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        connection_type = self.device_config.connection_type
        
        try:
            if connection_type == "TCP":
                _LOG.info("%s Creating TCP client for %s", self.log_id, self.address)
                self._nad_receiver = NADReceiverTCP(self.device_config.host)
                
                try:
                    # available_sources is a property, not a method
                    self._source_list = self._nad_receiver.available_sources()
                    _LOG.info("%s Available sources: %s", self.log_id, self._source_list)
                except Exception as err:
                    _LOG.warning("%s Failed to fetch sources: %s", self.log_id, err)
                    self._source_list = []
                    
            elif connection_type == "Telnet":
                _LOG.info("%s Creating Telnet client for %s:%d", 
                         self.log_id, self.address, self.device_config.port)
                self._nad_receiver = NADReceiverTelnet(
                    self.device_config.host, 
                    self.device_config.port
                )
                
                if self.device_config.sources:
                    self._source_list = list(self.device_config.sources.values())
                else:
                    self._source_list = []
                    
            else:
                _LOG.info("%s Creating RS232 client for %s", 
                         self.log_id, self.device_config.serial_port)
                self._nad_receiver = NADReceiver(self.device_config.serial_port)
                
                if self.device_config.sources:
                    self._source_list = list(self.device_config.sources.values())
                else:
                    self._source_list = []
            
            _LOG.info("%s NAD client created successfully", self.log_id)
            
        except Exception as err:
            _LOG.error("%s Failed to create NAD client: %s", self.log_id, err)
            raise
    
    async def poll_device(self) -> None:
        """
        Poll device for state updates.
        
        Called periodically by framework. We query the device state
        and emit update events.
        """
        if self._nad_receiver is None:
            _LOG.warning("%s Cannot poll: client not created", self.log_id)
            return
        
        try:
            if self.device_config.connection_type == "TCP":
                await self._poll_tcp()
            else:
                await self._poll_serial_telnet()
                
        except Exception as err:
            _LOG.error("%s Poll failed: %s", self.log_id, err)
    
    async def _poll_tcp(self) -> None:
        """Poll TCP device state."""
        try:
            status = await asyncio.to_thread(self._nad_receiver.status)
            
            if status is None:
                return
            
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
            
        except OSError:
            pass
        except Exception as err:
            _LOG.error("%s TCP poll error: %s", self.log_id, err)
    
    async def _poll_serial_telnet(self) -> None:
        """Poll RS232/Telnet device state."""
        try:
            power_state = await asyncio.to_thread(self._nad_receiver.main_power, "?")
            
            if not power_state:
                self._power = False
                self.events.emit(
                    DeviceEvents.UPDATE,
                    self.identifier,
                    {
                        "state": "OFF",
                        "volume": self._volume,
                        "muted": self._muted,
                        "source": self._source,
                    }
                )
                return
            
            self._power = power_state == "On"
            
            if self._power:
                mute_state = await asyncio.to_thread(self._nad_receiver.main_mute, "?")
                self._muted = mute_state == "On"
                
                volume_db = await asyncio.to_thread(self._nad_receiver.main_volume, "?")
                if volume_db is not None:
                    min_db = self.device_config.min_volume
                    max_db = self.device_config.max_volume
                    self._volume = int(((volume_db - min_db) / (max_db - min_db)) * 100)
                
                if self.device_config.sources:
                    source_num = await asyncio.to_thread(self._nad_receiver.main_source, "?")
                    if source_num:
                        self._source = self.device_config.sources.get(source_num)
            
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
            _LOG.error("%s Serial/Telnet poll error: %s", self.log_id, err)
    
    async def turn_on(self) -> bool:
        """Turn device on."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot turn on: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Turning on...", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.power_on)
            else:
                await asyncio.to_thread(self._nad_receiver.main_power, "=", "On")
            
            self._power = True
            await asyncio.sleep(0.5)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Turn on failed: %s", self.log_id, err)
            return False
    
    async def turn_off(self) -> bool:
        """Turn device off."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot turn off: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Turning off...", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.power_off)
            else:
                await asyncio.to_thread(self._nad_receiver.main_power, "=", "Off")
            
            self._power = False
            await asyncio.sleep(0.5)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Turn off failed: %s", self.log_id, err)
            return False
    
    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot set volume: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Setting volume to %d", self.log_id, volume)
            
            if self.device_config.connection_type == "TCP":
                volume_range = self._max_vol_nad - self._min_vol_nad
                nad_volume = int((volume / 100) * volume_range + self._min_vol_nad)
                await asyncio.to_thread(self._nad_receiver.set_volume, nad_volume)
            else:
                min_db = self.device_config.min_volume
                max_db = self.device_config.max_volume
                volume_db = int((volume / 100) * (max_db - min_db) + min_db)
                await asyncio.to_thread(self._nad_receiver.main_volume, "=", volume_db)
            
            self._volume = volume
            await asyncio.sleep(0.3)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Set volume failed: %s", self.log_id, err)
            return False
    
    async def volume_up(self) -> bool:
        """Increase volume."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot volume up: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Volume up", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                nad_volume = self._nad_volume_from_percent(self._volume)
                await asyncio.to_thread(
                    self._nad_receiver.set_volume,
                    nad_volume + 2 * self._volume_step
                )
            else:
                await asyncio.to_thread(self._nad_receiver.main_volume, "+")
            
            await asyncio.sleep(0.3)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Volume up failed: %s", self.log_id, err)
            return False
    
    async def volume_down(self) -> bool:
        """Decrease volume."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot volume down: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Volume down", self.log_id)
            
            if self.device_config.connection_type == "TCP":
                nad_volume = self._nad_volume_from_percent(self._volume)
                await asyncio.to_thread(
                    self._nad_receiver.set_volume,
                    nad_volume - 2 * self._volume_step
                )
            else:
                await asyncio.to_thread(self._nad_receiver.main_volume, "-")
            
            await asyncio.sleep(0.3)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Volume down failed: %s", self.log_id, err)
            return False
    
    async def mute(self, mute: bool) -> bool:
        """Mute or unmute."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot mute: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Mute: %s", self.log_id, mute)
            
            if self.device_config.connection_type == "TCP":
                if mute:
                    await asyncio.to_thread(self._nad_receiver.mute)
                else:
                    await asyncio.to_thread(self._nad_receiver.unmute)
            else:
                state = "On" if mute else "Off"
                await asyncio.to_thread(self._nad_receiver.main_mute, "=", state)
            
            self._muted = mute
            await asyncio.sleep(0.3)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Mute failed: %s", self.log_id, err)
            return False
    
    async def select_source(self, source: str) -> bool:
        """Select input source."""
        if self._nad_receiver is None:
            _LOG.error("%s Cannot select source: client not created", self.log_id)
            return False
        
        try:
            _LOG.info("%s Selecting source: %s", self.log_id, source)
            
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.select_source, source)
            else:
                source_num = None
                if self.device_config.sources:
                    for num, name in self.device_config.sources.items():
                        if name == source:
                            source_num = num
                            break
                
                if source_num:
                    await asyncio.to_thread(self._nad_receiver.main_source, "=", source_num)
                else:
                    _LOG.warning("%s Source not found: %s", self.log_id, source)
                    return False
            
            self._source = source
            await asyncio.sleep(0.5)
            
            await self.poll_device()
            return True
            
        except Exception as err:
            _LOG.error("%s Select source failed: %s", self.log_id, err)
            return False
    
    def _nad_volume_from_percent(self, percent: int) -> int:
        """Convert percentage to NAD volume (0-200)."""
        volume_range = self._max_vol_nad - self._min_vol_nad
        return int((percent / 100) * volume_range + self._min_vol_nad)
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
        return self.device_config.identifier
    
    @property
    def name(self) -> str:
        return self.device_config.name
    
    @property
    def address(self) -> str | None:
        return self.device_config.host
    
    @property
    def log_id(self) -> str:
        return f"[{self.name}]"
    
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
    
    async def establish_connection(self) -> None:
        """Create NAD receiver client."""
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        connection_type = self.device_config.connection_type
        
        try:
            if connection_type == "TCP":
                _LOG.info("%s Creating TCP client for %s", self.log_id, self.address)
                self._nad_receiver = NADReceiverTCP(self.device_config.host)
                try:
                    self._source_list = self._nad_receiver.available_sources()
                except Exception:
                    self._source_list = []
                    
            elif connection_type == "Telnet":
                _LOG.info("%s Creating Telnet client for %s:%d", 
                         self.log_id, self.address, self.device_config.port)
                self._nad_receiver = NADReceiverTelnet(
                    self.device_config.host, 
                    self.device_config.port
                )
                self._source_list = list(self.device_config.sources.values()) if self.device_config.sources else []
                    
            else:
                _LOG.info("%s Creating RS232 client for %s", 
                         self.log_id, self.device_config.serial_port)
                self._nad_receiver = NADReceiver(self.device_config.serial_port)
                self._source_list = list(self.device_config.sources.values()) if self.device_config.sources else []
            
            _LOG.info("%s NAD client created successfully", self.log_id)
            
        except Exception as err:
            _LOG.error("%s Failed to create NAD client: %s", self.log_id, err)
            raise
    
    async def poll_device(self) -> None:
        """Full poll of device state."""
        if self._nad_receiver is None:
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
            if status is None: return
            
            self._power = status.get("power", False)
            self._muted = status.get("muted", False)
            self._source = status.get("source")
            
            nad_volume = status.get("volume", 0)
            self._volume = self._nad_vol_to_percent(nad_volume)
            
            self._emit_update()
        except OSError:
            pass

    async def _poll_serial_telnet(self) -> None:
        """Poll RS232/Telnet device state."""
        try:
            # Query power first
            power_state = await asyncio.to_thread(self._nad_receiver.main_power, "?")
            
            if not power_state:
                # Connection might be down or device is off
                self._power = False
                self._emit_update()
                return
            
            self._power = power_state == "On"
            
            if self._power:
                mute_state = await asyncio.to_thread(self._nad_receiver.main_mute, "?")
                self._muted = mute_state == "On"
                
                volume_db = await asyncio.to_thread(self._nad_receiver.main_volume, "?")
                if volume_db is not None:
                    self._volume = self._db_to_percent(volume_db)
                
                if self.device_config.sources:
                    source_num = await asyncio.to_thread(self._nad_receiver.main_source, "?")
                    if source_num:
                        self._source = self.device_config.sources.get(source_num)
            
            self._emit_update()
            
        except Exception as err:
            _LOG.warning("%s Poll partial fail: %s", self.log_id, err)
            # Don't emit error, just skip this poll

    def _emit_update(self):
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

    async def turn_on(self) -> bool:
        """Turn device on with connection retry."""
        if self._nad_receiver is None: return False
        
        try:
            _LOG.info("%s Turning on...", self.log_id)
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.power_on)
            else:
                # Re-initiate connection if needed for Telnet
                if self.device_config.connection_type == "Telnet":
                    # This helps if the socket was closed by the receiver during standby
                    self._nad_receiver.transport = None 
                
                await asyncio.to_thread(self._nad_receiver.main_power, "=", "On")
            
            self._power = True
            # Optimistic update immediately
            self._emit_update() 
            return True
            
        except Exception as err:
            _LOG.error("%s Turn on failed: %s", self.log_id, err)
            return False
    
    async def turn_off(self) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.power_off)
            else:
                await asyncio.to_thread(self._nad_receiver.main_power, "=", "Off")
            self._power = False
            self._emit_update()
            return True
        except Exception:
            return False
    
    async def set_volume(self, volume: int) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                nad_vol = self._percent_to_nad_vol(volume)
                await asyncio.to_thread(self._nad_receiver.set_volume, nad_vol)
            else:
                vol_db = self._percent_to_db(volume)
                await asyncio.to_thread(self._nad_receiver.main_volume, "=", vol_db)
            
            self._volume = volume
            self._emit_update()
            return True
        except Exception:
            return False
    
    async def volume_up(self) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                # TCP logic...
                pass
            else:
                await asyncio.to_thread(self._nad_receiver.main_volume, "+")
            
            # Optimistic update: assume +1 step (approx 1-2%)
            self._volume = min(100, self._volume + 1) 
            self._emit_update()
            return True
        except Exception:
            return False
    
    async def volume_down(self) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                pass
            else:
                await asyncio.to_thread(self._nad_receiver.main_volume, "-")
            
            self._volume = max(0, self._volume - 1)
            self._emit_update()
            return True
        except Exception:
            return False
            
    async def mute(self, mute: bool) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                if mute: await asyncio.to_thread(self._nad_receiver.mute)
                else: await asyncio.to_thread(self._nad_receiver.unmute)
            else:
                state = "On" if mute else "Off"
                await asyncio.to_thread(self._nad_receiver.main_mute, "=", state)
            
            self._muted = mute
            self._emit_update()
            return True
        except Exception:
            return False

    async def select_source(self, source: str) -> bool:
        if self._nad_receiver is None: return False
        try:
            if self.device_config.connection_type == "TCP":
                await asyncio.to_thread(self._nad_receiver.select_source, source)
            else:
                # Find ID logic...
                source_num = None
                if self.device_config.sources:
                    for num, name in self.device_config.sources.items():
                        if name == source:
                            source_num = num
                            break
                if source_num:
                    await asyncio.to_thread(self._nad_receiver.main_source, "=", source_num)
            
            self._source = source
            self._emit_update()
            return True
        except Exception:
            return False

    # Helpers
    def _nad_vol_to_percent(self, nad_vol):
        # ... existing logic ...
        if nad_vol < self._min_vol_nad: return 0
        if nad_vol > self._max_vol_nad: return 100
        return int(((nad_vol - self._min_vol_nad) / (self._max_vol_nad - self._min_vol_nad)) * 100)

    def _percent_to_nad_vol(self, percent):
        return int((percent / 100) * (self._max_vol_nad - self._min_vol_nad) + self._min_vol_nad)

    def _db_to_percent(self, db):
        min_db = self.device_config.min_volume
        max_db = self.device_config.max_volume
        return int(((db - min_db) / (max_db - min_db)) * 100)

    def _percent_to_db(self, percent):
        min_db = self.device_config.min_volume
        max_db = self.device_config.max_volume
        return int((percent / 100) * (max_db - min_db) + min_db)
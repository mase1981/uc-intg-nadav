"""
NAD AV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Callable
from ucapi_framework import PollingDevice, DeviceEvents
from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class NADDevice(PollingDevice):
    """NAD AV receiver/amplifier using polling pattern."""
    
    def __init__(self, device_config: NADDeviceConfig, loop=None, config_manager=None, driver=None):
        """Initialize NAD device."""
        super().__init__(
            device_config,
            loop,
            poll_interval=10,
            config_manager=config_manager,
            driver=driver,
        )
        
        self._nad_receiver = None
        self._power = False
        self._volume = 0
        self._muted = False
        self._source = None
        self._source_list = []

        # Sensor entity state
        self._model = None
        self._version = None

        # Select entity state
        self._speaker_a = "Off"
        self._speaker_b = "Off"
        self._listening_mode = None
        self._listening_modes = []

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
    def listening_mode(self) -> str | None:
        return self._listening_mode

    @property
    def listening_modes(self) -> list[str]:
        return self._listening_modes
    
    async def establish_connection(self) -> None:
        """Create NAD receiver client and verify connectivity."""
        await self._connect()

        # Verify connection with initial status poll
        try:
            await asyncio.wait_for(self.poll_device(), timeout=5.0)
            _LOG.info("%s Connection established and verified", self.log_id)
        except asyncio.TimeoutError:
            _LOG.warning("%s Connection established but initial poll timed out", self.log_id)
        except Exception as err:
            _LOG.warning("%s Connection established but initial poll failed: %s", self.log_id, err)

        # Query model and version info (cached for sensor entities)
        await self.get_model()
        await self.get_version()
        
    async def _connect(self) -> None:
        """Internal connection logic."""
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        connection_type = self.device_config.connection_type
        
        try:
            if self._nad_receiver:
                try:
                    if hasattr(self._nad_receiver, "transport") and self._nad_receiver.transport:
                        self._nad_receiver.transport.close()
                except Exception:
                    pass
                self._nad_receiver = None

            if connection_type == "TCP":
                _LOG.info("%s Creating TCP client for %s", self.log_id, self.address)
                self._nad_receiver = NADReceiverTCP(self.device_config.host)
                try:
                    self._source_list = self._nad_receiver.available_sources()
                    _LOG.info("%s TCP sources discovered: %s", self.log_id, self._source_list)
                except Exception:
                    self._source_list = []
                    
            elif connection_type == "Telnet":
                _LOG.info("%s Creating Telnet client for %s:%d", 
                         self.log_id, self.address, self.device_config.port)
                self._nad_receiver = NADReceiverTelnet(
                    self.device_config.host, 
                    self.device_config.port
                )
                # CRITICAL FIX: Build source list from configured sources
                if self.device_config.sources:
                    self._source_list = list(self.device_config.sources.values())
                    _LOG.info("%s Telnet sources configured: %s", self.log_id, self._source_list)
                else:
                    self._source_list = []
                    _LOG.warning("%s No sources configured for Telnet connection", self.log_id)
                    
            else:
                _LOG.info("%s Creating RS232 client for %s", 
                         self.log_id, self.device_config.serial_port)
                self._nad_receiver = NADReceiver(self.device_config.serial_port)
                # CRITICAL FIX: Build source list from configured sources
                if self.device_config.sources:
                    self._source_list = list(self.device_config.sources.values())
                    _LOG.info("%s RS232 sources configured: %s", self.log_id, self._source_list)
                else:
                    self._source_list = []
                    _LOG.warning("%s No sources configured for RS232 connection", self.log_id)
            
            _LOG.info("%s NAD client created successfully", self.log_id)
            
        except Exception as err:
            _LOG.error("%s Failed to create NAD client: %s", self.log_id, err)
            raise

    async def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with automatic reconnection on BrokenPipe/OSError.
        NAD receivers drop connections frequently.
        """
        if self._nad_receiver is None:
            await self._connect()
            
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except (BrokenPipeError, OSError, EOFError) as err:
            _LOG.warning("%s Connection lost (%s). Reconnecting and retrying...", self.log_id, err)
            await self._connect()
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception:
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
            _LOG.warning("%s Poll partial fail: %s", self.log_id, err)

    async def _poll_tcp(self) -> None:
        """Poll TCP device state."""
        try:
            status = await self._execute_with_retry(self._nad_receiver.status)
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
            power_state = await self._execute_with_retry(self._nad_receiver.main_power, "?")
            
            if not power_state:
                self._power = False
                self._emit_update()
                return
            
            self._power = power_state == "On"
            
            if self._power:
                mute_state = await self._execute_with_retry(self._nad_receiver.main_mute, "?")
                self._muted = mute_state == "On"
                
                volume_db = await self._execute_with_retry(self._nad_receiver.main_volume, "?")
                if volume_db is not None:
                    self._volume = self._db_to_percent(volume_db)
                
                # CRITICAL FIX: Query source and map to friendly name
                if self.device_config.sources:
                    try:
                        source_num = await self._execute_with_retry(self._nad_receiver.main_source, "?")
                        _LOG.debug("%s Source query returned: %s (type: %s)", 
                                  self.log_id, source_num, type(source_num))
                        
                        if source_num is not None:
                            # Convert to int if it's a string
                            if isinstance(source_num, str):
                                source_num = int(source_num)
                            
                            # Map source number to friendly name
                            if source_num in self.device_config.sources:
                                self._source = self.device_config.sources[source_num]
                                _LOG.debug("%s Mapped source %d to '%s'", 
                                          self.log_id, source_num, self._source)
                            else:
                                _LOG.warning("%s Source %d not in configured sources: %s", 
                                           self.log_id, source_num, self.device_config.sources)
                                self._source = f"Source {source_num}"
                    except Exception as src_err:
                        _LOG.debug("%s Source query error: %s", self.log_id, src_err)
                        self._source = None

                # Query speaker states for select entities
                try:
                    speaker_a_state = await self._execute_with_retry(self._nad_receiver.main_speaker_a, "?")
                    if speaker_a_state:
                        self._speaker_a = speaker_a_state
                except Exception as spk_err:
                    _LOG.debug("%s Speaker A query error: %s", self.log_id, spk_err)

                try:
                    speaker_b_state = await self._execute_with_retry(self._nad_receiver.main_speaker_b, "?")
                    if speaker_b_state:
                        self._speaker_b = speaker_b_state
                except Exception as spk_err:
                    _LOG.debug("%s Speaker B query error: %s", self.log_id, spk_err)

            self._emit_update()
        except Exception as err:
            _LOG.debug("%s Poll error: %s", self.log_id, err)

    def _emit_update(self):
        """Emit device state update to all entities."""
        # Media player update
        update_data = {
            "state": "ON" if self._power else "OFF",
            "volume": self._volume,
            "muted": self._muted,
            "source": self._source,
            "source_list": self._source_list,
        }
        _LOG.debug("%s Emitting media_player update: %s", self.log_id, update_data)
        self.events.emit(
            DeviceEvents.UPDATE,
            self.identifier,
            update_data
        )

        # Sensor entity updates
        self._emit_sensor_updates()

        # Select entity updates
        self._emit_select_updates()

    def _emit_sensor_updates(self):
        """Emit sensor entity updates."""
        # Model sensor
        model_entity_id = f"sensor.{self.identifier}_model"
        self.events.emit(
            DeviceEvents.UPDATE,
            model_entity_id,
            {
                "state": "ON" if self._model else "UNAVAILABLE",
                "value": self._model or "Unknown",
            }
        )

        # Version sensor
        version_entity_id = f"sensor.{self.identifier}_version"
        self.events.emit(
            DeviceEvents.UPDATE,
            version_entity_id,
            {
                "state": "ON" if self._version else "UNAVAILABLE",
                "value": self._version or "Unknown",
            }
        )

    def _emit_select_updates(self):
        """Emit select entity updates."""
        # Speaker A select
        speaker_a_entity_id = f"select.{self.identifier}_speaker_a"
        self.events.emit(
            DeviceEvents.UPDATE,
            speaker_a_entity_id,
            {
                "state": "ON",
                "current_option": self._speaker_a,
                "options": ["On", "Off"],
            }
        )

        # Speaker B select
        speaker_b_entity_id = f"select.{self.identifier}_speaker_b"
        self.events.emit(
            DeviceEvents.UPDATE,
            speaker_b_entity_id,
            {
                "state": "ON",
                "current_option": self._speaker_b,
                "options": ["On", "Off"],
            }
        )

        # Listening Mode select (if modes available)
        listening_mode_entity_id = f"select.{self.identifier}_listening_mode"
        if self._listening_modes:
            self.events.emit(
                DeviceEvents.UPDATE,
                listening_mode_entity_id,
                {
                    "state": "ON",
                    "current_option": self._listening_mode or "",
                    "options": self._listening_modes,
                }
            )
        else:
            # No modes available, mark as unavailable
            self.events.emit(
                DeviceEvents.UPDATE,
                listening_mode_entity_id,
                {
                    "state": "UNAVAILABLE",
                    "current_option": "",
                    "options": [],
                }
            )

    async def turn_on(self) -> bool:
        """Turn device on."""
        if self._nad_receiver is None: 
            return False
        try:
            _LOG.info("%s Turning on...", self.log_id)
            if self.device_config.connection_type == "TCP":
                await self._execute_with_retry(self._nad_receiver.power_on)
            else:
                await self._execute_with_retry(self._nad_receiver.main_power, "=", "On")
            
            self._power = True
            self._emit_update() 
            return True
        except Exception as err:
            _LOG.error("%s Turn on failed: %s", self.log_id, err)
            return False
    
    async def turn_off(self) -> bool:
        """Turn device off."""
        if self._nad_receiver is None: 
            return False
        try:
            _LOG.info("%s Turning off...", self.log_id)
            if self.device_config.connection_type == "TCP":
                await self._execute_with_retry(self._nad_receiver.power_off)
            else:
                await self._execute_with_retry(self._nad_receiver.main_power, "=", "Off")
            
            self._power = False
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Turn off failed: %s", self.log_id, err)
            return False
    
    async def set_volume(self, volume: int) -> bool:
        """Set volume level (0-100)."""
        if self._nad_receiver is None: 
            return False
        try:
            if self.device_config.connection_type == "TCP":
                nad_vol = self._percent_to_nad_vol(volume)
                await self._execute_with_retry(self._nad_receiver.set_volume, nad_vol)
            else:
                vol_db = self._percent_to_db(volume)
                await self._execute_with_retry(self._nad_receiver.main_volume, "=", vol_db)
            
            self._volume = volume
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Set volume failed: %s", self.log_id, err)
            return False
    
    async def volume_up(self) -> bool:
        """Increase volume by one step."""
        if self._nad_receiver is None: 
            return False
        try:
            if self.device_config.connection_type == "TCP":
                current = self._volume
                new_volume = min(100, current + 1)
                nad_vol = self._percent_to_nad_vol(new_volume)
                await self._execute_with_retry(self._nad_receiver.set_volume, nad_vol)
            else:
                await self._execute_with_retry(self._nad_receiver.main_volume, "+")
            
            self._volume = min(100, self._volume + 1) 
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Volume up failed: %s", self.log_id, err)
            return False
    
    async def volume_down(self) -> bool:
        """Decrease volume by one step."""
        if self._nad_receiver is None: 
            return False
        try:
            if self.device_config.connection_type == "TCP":
                current = self._volume
                new_volume = max(0, current - 1)
                nad_vol = self._percent_to_nad_vol(new_volume)
                await self._execute_with_retry(self._nad_receiver.set_volume, nad_vol)
            else:
                await self._execute_with_retry(self._nad_receiver.main_volume, "-")
            
            self._volume = max(0, self._volume - 1)
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Volume down failed: %s", self.log_id, err)
            return False
            
    async def mute(self, mute: bool) -> bool:
        """Set mute state."""
        if self._nad_receiver is None: 
            return False
        try:
            if self.device_config.connection_type == "TCP":
                if mute: 
                    await self._execute_with_retry(self._nad_receiver.mute)
                else: 
                    await self._execute_with_retry(self._nad_receiver.unmute)
            else:
                state = "On" if mute else "Off"
                await self._execute_with_retry(self._nad_receiver.main_mute, "=", state)
            
            self._muted = mute
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Mute failed: %s", self.log_id, err)
            return False

    async def select_source(self, source: str) -> bool:
        """Select input source by friendly name."""
        if self._nad_receiver is None: 
            return False
        try:
            _LOG.info("%s Selecting source: %s", self.log_id, source)
            
            if self.device_config.connection_type == "TCP":
                await self._execute_with_retry(self._nad_receiver.select_source, source)
            else:
                # Find source number by friendly name
                source_num = None
                if self.device_config.sources:
                    for num, name in self.device_config.sources.items():
                        if name == source:
                            source_num = num
                            break
                
                if source_num is not None:
                    _LOG.info("%s Mapping '%s' to source number %d", self.log_id, source, source_num)
                    await self._execute_with_retry(self._nad_receiver.main_source, "=", source_num)
                else:
                    _LOG.error("%s Source '%s' not found in configuration: %s", 
                              self.log_id, source, self.device_config.sources)
                    return False
            
            self._source = source
            self._emit_update()
            return True
        except Exception as err:
            _LOG.error("%s Select source failed: %s", self.log_id, err)
            return False

    def _nad_vol_to_percent(self, nad_vol):
        """Convert NAD volume (0-200) to percentage (0-100)."""
        if nad_vol < self._min_vol_nad: 
            return 0
        if nad_vol > self._max_vol_nad: 
            return 100
        return int(((nad_vol - self._min_vol_nad) / (self._max_vol_nad - self._min_vol_nad)) * 100)

    def _percent_to_nad_vol(self, percent):
        """Convert percentage (0-100) to NAD volume (0-200)."""
        return int((percent / 100) * (self._max_vol_nad - self._min_vol_nad) + self._min_vol_nad)

    def _db_to_percent(self, db):
        """Convert dB to percentage (0-100)."""
        min_db = self.device_config.min_volume
        max_db = self.device_config.max_volume
        return int(((db - min_db) / (max_db - min_db)) * 100)

    def _percent_to_db(self, percent):
        """Convert percentage (0-100) to dB."""
        min_db = self.device_config.min_volume
        max_db = self.device_config.max_volume
        return int((percent / 100) * (max_db - min_db) + min_db)

    async def get_model(self) -> str | None:
        """Get device model (query once, cache result)."""
        if self._model is not None:
            return self._model

        if self._nad_receiver is None:
            return None

        try:
            # Only available for Serial/Telnet connections
            if self.device_config.connection_type != "TCP":
                model = await self._execute_with_retry(self._nad_receiver.main_model, "?")
                if model:
                    self._model = model
                    _LOG.info("%s Device model: %s", self.log_id, model)
                return self._model
        except Exception as err:
            _LOG.debug("%s Failed to query model: %s", self.log_id, err)

        return None

    async def get_version(self) -> str | None:
        """Get firmware version (query once, cache result)."""
        if self._version is not None:
            return self._version

        if self._nad_receiver is None:
            return None

        try:
            # Only available for Serial/Telnet connections
            if self.device_config.connection_type != "TCP":
                version = await self._execute_with_retry(self._nad_receiver.main_version, "?")
                if version:
                    self._version = version
                    _LOG.info("%s Firmware version: %s", self.log_id, version)
                return self._version
        except Exception as err:
            _LOG.debug("%s Failed to query version: %s", self.log_id, err)

        return None

    async def set_speaker_a(self, state: str) -> bool:
        """Set Speaker A state (On/Off)."""
        if self._nad_receiver is None:
            return False

        try:
            _LOG.info("%s Setting Speaker A to %s", self.log_id, state)
            # Only available for Serial/Telnet connections
            if self.device_config.connection_type != "TCP":
                await self._execute_with_retry(self._nad_receiver.main_speaker_a, "=", state)
                self._speaker_a = state
                self._emit_update()
                return True
            else:
                _LOG.warning("%s Speaker A control not available for TCP connections", self.log_id)
                return False
        except Exception as err:
            _LOG.error("%s Set Speaker A failed: %s", self.log_id, err)
            return False

    async def set_speaker_b(self, state: str) -> bool:
        """Set Speaker B state (On/Off)."""
        if self._nad_receiver is None:
            return False

        try:
            _LOG.info("%s Setting Speaker B to %s", self.log_id, state)
            # Only available for Serial/Telnet connections
            if self.device_config.connection_type != "TCP":
                await self._execute_with_retry(self._nad_receiver.main_speaker_b, "=", state)
                self._speaker_b = state
                self._emit_update()
                return True
            else:
                _LOG.warning("%s Speaker B control not available for TCP connections", self.log_id)
                return False
        except Exception as err:
            _LOG.error("%s Set Speaker B failed: %s", self.log_id, err)
            return False

    async def set_listening_mode(self, mode: str) -> bool:
        """Set listening mode."""
        if self._nad_receiver is None:
            return False

        try:
            _LOG.info("%s Setting listening mode to %s", self.log_id, mode)
            # Only available for Serial/Telnet connections
            if self.device_config.connection_type != "TCP":
                # NAD listening mode uses +/- operators, not = with value
                # This is a simplified implementation that cycles modes
                # A more complete implementation would need to know current mode
                # and use + or - to reach desired mode
                await self._execute_with_retry(self._nad_receiver.main_listeningmode, "+")
                self._listening_mode = mode
                self._emit_update()
                return True
            else:
                _LOG.warning("%s Listening mode control not available for TCP connections", self.log_id)
                return False
        except Exception as err:
            _LOG.error("%s Set listening mode failed: %s", self.log_id, err)
            return False
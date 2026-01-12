"""
NAD AV setup flow for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any
from ucapi import RequestUserInput, IntegrationSetupError, SetupError
from ucapi_framework import BaseSetupFlow
from intg_nadav.config import NADDeviceConfig

_LOG = logging.getLogger(__name__)


class NADSetupFlow(BaseSetupFlow[NADDeviceConfig]):
    """Setup flow for NAD integration."""
    
    def __init__(self, *args, **kwargs):
        """Initialize setup flow."""
        super().__init__(*args, **kwargs)
        self._device_info = {}
    
    async def query_device(self, input_values: dict[str, Any]) -> NADDeviceConfig | SetupError | RequestUserInput:
        """Create device config from user input."""
        # First screen - basic device info
        if "name" in input_values and "source_1" not in input_values:
            name = input_values.get("name", "").strip()
            connection_type = input_values.get("connection_type", "Telnet")
            host = input_values.get("host", "").strip()
            port = int(input_values.get("port", 23))
            serial_port = input_values.get("serial_port", "/dev/ttyUSB0").strip()
            
            if connection_type in ("TCP", "Telnet"):
                if not host:
                    _LOG.warning("Host required for Network connection")
                    return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
                
                identifier = f"{host}_{port}"
            else:
                if not serial_port:
                    _LOG.warning("Serial port required for RS232 connection")
                    return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
                
                identifier = serial_port.replace("/", "_").replace("\\", "_")
            
            # Store device info for next screen
            self._device_info = {
                "identifier": identifier,
                "name": name or f"NAD {connection_type}",
                "connection_type": connection_type,
                "host": host,
                "port": port,
                "serial_port": serial_port,
            }
            
            # For TCP connections, sources are auto-discovered, skip source configuration
            if connection_type == "TCP":
                _LOG.info("Creating NAD TCP device config: %s", name)
                return NADDeviceConfig(
                    identifier=identifier,
                    name=name or f"NAD {connection_type}",
                    connection_type=connection_type,
                    host=host,
                    port=port,
                    serial_port=serial_port,
                    min_volume=-92,
                    max_volume=-20,
                    volume_step=4,
                    sources=None,  # Auto-discovered for TCP
                )
            
            # For Telnet/RS232, show source configuration screen
            return await self.get_source_configuration_screen()
        
        # Second screen - source configuration (only for Telnet/RS232)
        elif "source_1" in input_values:
            # Build source mapping from user input
            source_map = {}
            
            for i in range(1, 13):  # Sources 1-12
                source_name = input_values.get(f"source_{i}", "").strip()
                if source_name:  # Only add non-empty sources
                    source_map[i] = source_name
            
            if not source_map:
                _LOG.warning("No sources configured")
                return SetupError(error_type=IntegrationSetupError.OTHER)
            
            _LOG.info("Creating NAD device config: %s with %d sources: %s", 
                     self._device_info["name"], len(source_map), source_map)
            
            return NADDeviceConfig(
                identifier=self._device_info["identifier"],
                name=self._device_info["name"],
                connection_type=self._device_info["connection_type"],
                host=self._device_info.get("host"),
                port=self._device_info.get("port", 23),
                serial_port=self._device_info.get("serial_port", "/dev/ttyUSB0"),
                min_volume=-92,
                max_volume=-20,
                volume_step=4,
                sources=source_map,
            )
        
        return SetupError(error_type=IntegrationSetupError.OTHER)
    
    async def get_source_configuration_screen(self) -> RequestUserInput:
        """Get source configuration screen for Telnet/RS232 connections."""
        return RequestUserInput(
            {"en": "Configure Input Sources"},
            [
                {
                    "id": "info",
                    "label": {"en": "📺 Input Source Names"},
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "Enter friendly names for the source inputs you use.\n\n"
                                    "Example: Source 1 = 'Apple TV', Source 2 = 'Fire TV', etc.\n\n"
                                    "Leave unused sources blank. You only need to configure the sources you actually use."
                                )
                            }
                        }
                    },
                },
                {
                    "id": "source_1",
                    "label": {"en": "Source 1"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_2",
                    "label": {"en": "Source 2"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_3",
                    "label": {"en": "Source 3"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_4",
                    "label": {"en": "Source 4"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_5",
                    "label": {"en": "Source 5"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_6",
                    "label": {"en": "Source 6"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_7",
                    "label": {"en": "Source 7"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_8",
                    "label": {"en": "Source 8"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_9",
                    "label": {"en": "Source 9 (Optional)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_10",
                    "label": {"en": "Source 10 (Optional)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_11",
                    "label": {"en": "Source 11 (Optional)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "source_12",
                    "label": {"en": "Source 12 (Optional)"},
                    "field": {"text": {"value": ""}},
                },
            ]
        )
    
    def get_manual_entry_form(self) -> RequestUserInput:
        """Define manual entry fields with user instructions."""
        return RequestUserInput(
            {"en": "Configure NAD Device"},
            [
                {
                    "id": "info",
                    "label": {"en": "⚠️ IMPORTANT - Before Setup"},
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "Please ensure your NAD device is:\n"
                                    "• Powered ON\n"
                                    "• Connected to your network (for TCP/Telnet)\n"
                                    "• Has a static IP or DHCP reservation\n\n"
                                    "The integration will connect when you press 'Next'."
                                )
                            }
                        }
                    },
                },
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "NAD Receiver"}},
                },
                {
                    "id": "connection_type",
                    "label": {"en": "Connection Type"},
                    "field": {
                        "dropdown": {
                            "value": "Telnet",
                            "items": [
                                {"id": "Telnet", "label": {"en": "Telnet (T-Series AVR - Port 23)"}},
                                {"id": "TCP", "label": {"en": "TCP (D-Series Digital Amp - Port 53)"}},
                                {"id": "RS232", "label": {"en": "RS-232 Serial"}},
                            ],
                        }
                    },
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address (for TCP/Telnet)"},
                    "field": {"text": {"value": "192.168.1.100"}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port (Default: 23 for Telnet, 53 for TCP)"},
                    "field": {"number": {"value": 23, "min": 1, "max": 65535}},
                },
                {
                    "id": "serial_port",
                    "label": {"en": "Serial Port (RS232 only)"},
                    "field": {"text": {"value": "/dev/ttyUSB0"}},
                },
            ]
        )
    
    async def discover_devices(self):
        """Discovery not supported for NAD devices."""
        return []
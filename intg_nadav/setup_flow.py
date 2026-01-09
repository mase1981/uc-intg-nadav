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
    
    async def query_device(self, input_values: dict[str, Any]) -> NADDeviceConfig | SetupError:
        """Create device config from user input."""
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
        
        _LOG.info("Creating NAD device config: %s (%s)", name, connection_type)
        
        return NADDeviceConfig(
            identifier=identifier,
            name=name or f"NAD {connection_type}",
            connection_type=connection_type,
            host=host if connection_type in ("TCP", "Telnet") else None,
            port=port,
            serial_port=serial_port,
            min_volume=-92,
            max_volume=-20,
            volume_step=4,
            sources=None,
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
                                    "The integration will connect when you press 'Complete Setup'."
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
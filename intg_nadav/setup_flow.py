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
        """Create device config from user input and validate connection."""
        name = input_values.get("name", "").strip()
        connection_type = input_values.get("connection_type", "TCP")
        host = input_values.get("host", "").strip()
        port = int(input_values.get("port", 53))
        serial_port = input_values.get("serial_port", "/dev/ttyUSB0").strip()
        
        if connection_type in ("TCP", "Telnet"):
            if not host:
                _LOG.warning("Host required for TCP/Telnet connection")
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
            
            identifier = f"{host}_{port}"
        else:
            if not serial_port:
                _LOG.warning("Serial port required for RS232 connection")
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
            
            identifier = serial_port.replace("/", "_").replace("\\", "_")
        
        try:
            await self._test_connection(connection_type, host, port, serial_port)
        except Exception as err:
            _LOG.error("Connection test failed: %s", err)
            return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
        
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
    
    async def _test_connection(
        self, 
        connection_type: str, 
        host: str, 
        port: int, 
        serial_port: str
    ) -> None:
        """Test connection to NAD device."""
        import asyncio
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        try:
            if connection_type == "TCP":
                client = NADReceiverTCP(host)
                # Just verify we can communicate - don't validate the response format
                await asyncio.to_thread(client.status)
                _LOG.info("TCP connection test successful - receiver responded")
                
            elif connection_type == "Telnet":
                client = NADReceiverTelnet(host, port)
                # Just verify we can send command and get response - any response is valid
                response = await asyncio.to_thread(client.main_power, "?")
                _LOG.info("Telnet connection test successful - receiver responded with: %s", response)
                
            else:  # RS232
                client = NADReceiver(serial_port)
                # Just verify we can send command and get response
                response = await asyncio.to_thread(client.main_power, "?")
                _LOG.info("RS232 connection test successful - receiver responded with: %s", response)
            
            # If we got here without exception, connection works!
            _LOG.info("Connection test successful for %s", connection_type)
            
        except Exception as err:
            _LOG.error("Connection test failed: %s", err)
            raise
    
    def get_manual_entry_form(self) -> RequestUserInput:
        """Define manual entry fields."""
        return RequestUserInput(
            {"en": "Configure NAD Device"},
            [
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
                            "value": "TCP",
                            "items": [
                                {"id": "TCP", "label": {"en": "TCP (Digital Amplifiers)"}},
                                {"id": "Telnet", "label": {"en": "Telnet"}},
                                {"id": "RS232", "label": {"en": "RS-232 Serial"}},
                            ],
                        }
                    },
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address (TCP/Telnet)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port (Telnet only)"},
                    "field": {"number": {"value": 53, "min": 1, "max": 65535}},
                },
                {
                    "id": "serial_port",
                    "label": {"en": "Serial Port (RS232)"},
                    "field": {"text": {"value": "/dev/ttyUSB0"}},
                },
            ]
        )
    
    async def discover_devices(self):
        """NAD doesn't support auto-discovery."""
        return []
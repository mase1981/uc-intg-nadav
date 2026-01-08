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
        """Test connection to NAD device and CLOSE it immediately."""
        import asyncio
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet, NADReceiver
        
        client = None
        try:
            if connection_type == "TCP":
                client = NADReceiverTCP(host)
                await asyncio.to_thread(client.status)
                _LOG.info("TCP (Digital Amp) connection test successful")
                
            elif connection_type == "Telnet":
                client = NADReceiverTelnet(host, port)
                
                await asyncio.sleep(0.5)
                
                # Send a benign command
                response = await asyncio.to_thread(client.main_power, "?")
                _LOG.info("Telnet (AVR) connection test successful - response: %s", response)
                
                await asyncio.sleep(0.5)
                
            else:  # RS232
                client = NADReceiver(serial_port)
                await asyncio.sleep(0.5)
                response = await asyncio.to_thread(client.main_power, "?")
                _LOG.info("RS232 connection test successful - response: %s", response)
                await asyncio.sleep(0.5)
            
        except Exception as err:
            _LOG.error("Connection test failed: %s", err)
            raise
        finally:
            # NAD devices often only support 1 active Telnet session.
            if client:
                try:
                    if hasattr(client, "transport") and client.transport:
                        _LOG.info("Closing Telnet transport...")
                        client.transport.close()
                        await asyncio.sleep(1.0)
                        _LOG.info("Telnet transport closed")
                    elif hasattr(client, "close"):
                        _LOG.info("Closing connection...")
                        client.close()
                        await asyncio.sleep(1.0)
                        _LOG.info("Connection closed")
                except Exception as close_err:
                    _LOG.warning("Error closing test connection: %s", close_err)
    
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
                    "label": {"en": "Device Type / Connection"},
                    "field": {
                        "dropdown": {
                            "value": "Telnet",
                            "items": [
                                {"id": "Telnet", "label": {"en": "Network AVR (T-Series) [Telnet]"}},
                                {"id": "TCP", "label": {"en": "Digital Amp (D-Series) [TCP]"}},
                                {"id": "RS232", "label": {"en": "RS-232 Serial"}},
                            ],
                        }
                    },
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port (Default: 23)"},
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
        return []
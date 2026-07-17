"""
NAD setup flow for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import aiohttp
from ucapi import IntegrationSetupError, RequestUserInput, SetupError
from ucapi_framework import BaseSetupFlow

from intg_nadav.config import (
    CONNECTION_BLUOS,
    CONNECTION_RS232,
    CONNECTION_TCP,
    CONNECTION_TELNET,
    DEFAULT_PORTS,
    NADDeviceConfig,
    sanitize_identifier,
)

_LOG = logging.getLogger(__name__)


class NADSetupFlow(BaseSetupFlow[NADDeviceConfig]):
    """Setup flow for the NAD integration."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._device_info: dict[str, Any] = {}

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Configure NAD Device"},
            [
                {
                    "id": "info",
                    "label": {"en": "Before you begin"},
                    "field": {"label": {"value": {"en": (
                        "Ensure the device is powered on and reachable on your network "
                        "(use a static IP or DHCP reservation).\n\n"
                        "• BluOS / Streaming: M10, M33, C700, C658 and other BluOS models "
                        "(default port 11000).\n"
                        "• Telnet: classic T-Series AVRs (default port 23).\n"
                        "• TCP: D-Series digital amps (default port 53).\n"
                        "• RS-232: serial connection."
                    )}}},
                },
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "NAD Receiver"}},
                },
                {
                    "id": "connection_type",
                    "label": {"en": "Connection Type"},
                    "field": {"dropdown": {
                        "value": CONNECTION_TELNET,
                        "items": [
                            {"id": CONNECTION_TELNET, "label": {"en": "Telnet (T-Series AVR - Port 23)"}},
                            {"id": CONNECTION_BLUOS, "label": {"en": "BluOS / Streaming (M10, M33, C700, C658)"}},
                            {"id": CONNECTION_TCP, "label": {"en": "TCP (D-Series Digital Amp - Port 53)"}},
                            {"id": CONNECTION_RS232, "label": {"en": "RS-232 Serial"}},
                        ],
                    }},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address (network models)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port (0 = auto: BluOS 11000, Telnet 23, TCP 53)"},
                    "field": {"number": {"value": 0, "min": 0, "max": 65535}},
                },
                {
                    "id": "serial_port",
                    "label": {"en": "Serial Port (RS-232 only)"},
                    "field": {"text": {"value": "/dev/ttyUSB0"}},
                },
            ],
        )

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> NADDeviceConfig | SetupError | RequestUserInput:
        # Second screen: source configuration (classic Telnet/RS232 only)
        if "source_1" in input_values:
            return self._build_classic_with_sources(input_values)

        name = input_values.get("name", "").strip()
        connection_type = input_values.get("connection_type", CONNECTION_TELNET)
        host = input_values.get("host", "").strip()
        serial_port = input_values.get("serial_port", "/dev/ttyUSB0").strip()
        port = self._resolve_port(input_values.get("port", 0), connection_type)

        if connection_type == CONNECTION_RS232:
            if not serial_port:
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
            identifier = f"nad_{sanitize_identifier(serial_port)}"
            _LOG.info("Testing serial port %s...", serial_port)
            if not await self._test_serial(serial_port):
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
        else:
            if not host:
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
            identifier = f"nad_{sanitize_identifier(host)}_{port}"
            _LOG.info("Testing %s connectivity to %s:%d...", connection_type, host, port)
            if not await self._test_connection(connection_type, host, port):
                _LOG.error("Failed to connect to %s:%d (%s)", host, port, connection_type)
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)

        display_name = name or f"NAD {connection_type}"

        # BluOS and TCP auto-discover sources -> finish setup immediately.
        if connection_type in (CONNECTION_BLUOS, CONNECTION_TCP):
            _LOG.info("Creating NAD %s device config: %s", connection_type, display_name)
            return NADDeviceConfig(
                identifier=identifier,
                name=display_name,
                connection_type=connection_type,
                host=host or None,
                port=port,
                serial_port=serial_port,
            )

        # Telnet / RS232 -> ask for source names.
        self._device_info = {
            "identifier": identifier,
            "name": display_name,
            "connection_type": connection_type,
            "host": host or None,
            "port": port,
            "serial_port": serial_port,
        }
        return self._source_configuration_screen()

    def _resolve_port(self, raw: Any, connection_type: str) -> int:
        try:
            port = int(raw)
        except (ValueError, TypeError):
            port = 0
        if port <= 0:
            return DEFAULT_PORTS.get(connection_type, 0)
        return port

    def _build_classic_with_sources(self, input_values: dict[str, Any]) -> NADDeviceConfig | SetupError:
        source_map: dict[int, str] = {}
        for i in range(1, 13):
            name = input_values.get(f"source_{i}", "").strip()
            if name:
                source_map[i] = name
        if not source_map:
            _LOG.warning("No sources configured")
            return SetupError(error_type=IntegrationSetupError.OTHER)

        info = self._device_info
        _LOG.info("Creating NAD %s config with %d sources", info["connection_type"], len(source_map))
        return NADDeviceConfig(
            identifier=info["identifier"],
            name=info["name"],
            connection_type=info["connection_type"],
            host=info.get("host"),
            port=info.get("port", DEFAULT_PORTS[CONNECTION_TELNET]),
            serial_port=info.get("serial_port", "/dev/ttyUSB0"),
            sources=source_map,
        )

    def _source_configuration_screen(self) -> RequestUserInput:
        fields = [{
            "id": "info",
            "label": {"en": "Input Source Names"},
            "field": {"label": {"value": {"en": (
                "Enter friendly names for the inputs you use (e.g. Source 1 = 'Apple TV'). "
                "Leave unused sources blank."
            )}}},
        }]
        for i in range(1, 13):
            suffix = " (Optional)" if i > 8 else ""
            fields.append({
                "id": f"source_{i}",
                "label": {"en": f"Source {i}{suffix}"},
                "field": {"text": {"value": ""}},
            })
        return RequestUserInput({"en": "Configure Input Sources"}, fields)

    async def discover_devices(self):
        return []

    # ----------------------------------------------------------------- tests
    async def _test_connection(self, connection_type: str, host: str, port: int) -> bool:
        if connection_type == CONNECTION_BLUOS:
            return await self._test_bluos(host, port)
        return await self._test_classic_network(connection_type, host, port)

    async def _test_bluos(self, host: str, port: int) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://{host}:{port}/Status") as resp:
                    if resp.status == 200:
                        _LOG.info("BluOS device responded on %s:%d", host, port)
                        return True
                    _LOG.warning("BluOS device returned HTTP %d", resp.status)
                    return False
        except Exception as err:
            _LOG.error("BluOS connection test failed: %s", err)
            return False

    async def _test_classic_network(self, connection_type: str, host: str, port: int) -> bool:
        from nad_receiver import NADReceiverTCP, NADReceiverTelnet

        try:
            if connection_type == CONNECTION_TCP:
                receiver = NADReceiverTCP(host)
                status = await asyncio.wait_for(asyncio.to_thread(receiver.status), timeout=5.0)
                return status is not None
            receiver = NADReceiverTelnet(host, port)
            power = await asyncio.wait_for(asyncio.to_thread(receiver.main_power, "?"), timeout=5.0)
            return power is not None
        except asyncio.TimeoutError:
            _LOG.warning("%s connection timeout to %s:%d", connection_type, host, port)
            return False
        except Exception as err:
            _LOG.error("%s connection test failed: %s", connection_type, err)
            return False

    async def _test_serial(self, serial_port: str) -> bool:
        try:
            if os.name != "nt" and not os.path.exists(serial_port):
                _LOG.error("Serial port %s does not exist", serial_port)
                return False
            from nad_receiver import NADReceiver

            receiver = NADReceiver(serial_port)
            power = await asyncio.wait_for(asyncio.to_thread(receiver.main_power, "?"), timeout=5.0)
            return power is not None
        except asyncio.TimeoutError:
            _LOG.warning("RS232 connection timeout on %s", serial_port)
            return False
        except Exception as err:
            _LOG.error("Serial connection test failed: %s", err)
            return False

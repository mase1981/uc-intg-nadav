# NAD A/V Receivers & Amplifiers Integration for Unfolded Circle Remote 2/3

Control your NAD A/V receivers and amplifiers (digital amplifiers, classic receivers, and integrated amps) directly from your Unfolded Circle Remote 2 or Remote 3 with comprehensive media player control, **multiple connection types** (TCP/Telnet), **source switching**, and **full volume control**.

![NAD](https://img.shields.io/badge/NAD-A%2FV%20Receivers-blue)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-nadav?style=flat-square)](https://github.com/mase1981/uc-intg-nadav/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-nadav?style=flat-square)](https://github.com/mase1981/uc-intg-nadav/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://community.unfoldedcircle.com/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-nadav/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)


## Features

This integration provides comprehensive control of NAD A/V receivers and amplifiers through multiple connection protocols (TCP, Telnet), delivering seamless integration with your Unfolded Circle Remote for complete home theater control.

---
## 💰 Support Development

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

### 🎵 **Media Player Control**

#### **Power Management**
- **Power On/Off** - Complete power control
- **Power Toggle** - Quick power state switching
- **State Feedback** - Real-time power state monitoring

#### **Volume Control**
- **Volume Up/Down** - Precise volume adjustment (configurable step size)
- **Set Volume** - Direct volume control (-92dB to -20dB by default)
- **Volume Slider** - Visual volume control (0-100 scale)
- **Mute Toggle** - Quick mute/unmute
- **Unmute** - Explicit unmute control
- **Configurable Range** - Customize min/max volume and step size

#### **Source Selection**
Control all available input sources:
- **Source 1-12** - All standard NAD inputs
- **Disc** - CD/DVD player input
- **Video 1-3** - Video inputs
- **Tape 1-2** - Tape deck inputs
- **Tuner** - AM/FM tuner
- **Aux** - Auxiliary input

### 🔌 **Flexible Connection Options**

#### **TCP Connection** (Digital Amplifiers)
- **Port**: 53 (default for NAD digital amps)
- **Protocol**: NAD TCP protocol
- **Use Case**: Modern NAD digital amplifiers with network control
- **Stability**: Most reliable, recommended when available

#### **Telnet Connection** (Network Receivers)
- **Port**: Configurable (default 53)
- **Protocol**: Telnet with NAD commands
- **Use Case**: NAD receivers with Telnet support
- **Flexibility**: Works with various NAD models


### 🎛️ **Multi-Device Support**

- **Multiple Receivers** - Control unlimited NAD devices
- **Mixed Connections** - Use TCP, Telnet simultaneously
- **Individual Configuration** - Each device with independent settings
- **Manual Configuration** - Direct connection setup per device

### **Supported Models**

#### **Digital Amplifiers** (TCP Recommended)
- **D Series** - Digital integrated amplifiers with network control
- **M Series** - Master series amplifiers with IP control
- **C Series** - Classic series with network capability

#### **Classic Receivers** (Telnet)
- **C Series** - Classic integrated amplifiers

#### **Integrated Amplifiers**
- All NAD integrated amps with network control support

### **Connection Requirements**

#### **TCP Connection**
- **Protocol**: NAD TCP Text-Based Control
- **Port**: 53 (default)
- **Network**: Device must be on same local network
- **Models**: NAD digital amplifiers with network support

#### **Telnet Connection**
- **Protocol**: Telnet with NAD commands
- **Port**: Configurable (typically 53 or 23)
- **Network**: Device must be on same local network
- **Models**: NAD receivers with Telnet control


### **Network Requirements** (TCP/Telnet Only)

- **Local Network Access** - Integration requires same network as NAD device
- **TCP Protocol** - Firewall must allow TCP traffic on configured port
- **Static IP Recommended** - Device should have static IP or DHCP reservation
- **IP Control Enabled** - Enable network control in device settings (if applicable)

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-nadav/releases) page
2. Download the latest `uc-intg-nadav-<version>-aarch64.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-nadav:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-nadav:
    image: ghcr.io/mase1981/uc-intg-nadav:latest
    container_name: uc-intg-nadav
    network_mode: host
    volumes:
      - </local/path>:/data
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-nadav --restart unless-stopped --network host -v nadav-config:/app/config -e UC_CONFIG_HOME=/app/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-nadav:latest
```

## Configuration

### Step 1: Prepare Your NAD Device

**IMPORTANT**: NAD device must be powered on and properly connected before adding the integration.

#### For TCP/Telnet Connection:
1. Check that device is connected to network (Ethernet recommended)
2. Note the IP address from device's network settings
3. Ensure network control is enabled (if applicable)
4. Verify firmware is up to date

#### Network Setup (TCP/Telnet):
- **Wired Connection**: Recommended for stability
- **Static IP**: Recommended via DHCP reservation
- **Firewall**: Allow TCP on configured port (default 53)
- **Network Isolation**: Must be on same subnet as Remote

### Step 2: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The NAD integration should appear in **Available Integrations**
3. Click **"Configure"** and enter device details:

#### **Configuration Fields:**

   - **Device Name**: Friendly name (e.g., "Living Room NAD")
   - **Connection Type**: Select from dropdown:
     - **TCP** (Digital Amplifiers) - Port 53, most stable
     - **Telnet** - Custom port, flexible
   
   **For TCP/Telnet:**
   - **IP Address**: Enter device IP (e.g., 192.168.1.100)
   - **Port**: Default 53 (change only if needed)
   
   **Volume Settings (Optional):**
   - **Min Volume**: Minimum volume in dB (default: -92)
   - **Max Volume**: Maximum volume in dB (default: -20)
   - **Volume Step**: Volume adjustment step size (default: 4)
   
   - Click **Complete Setup**
   
   **Connection Test:**
   - Integration verifies device connectivity
   - Sends test command to confirm communication
   - Setup fails if device unreachable

3. Integration will create **media player entity**:
   - Entity ID: `media_player.nad_[device_name]`
   - Example: `media_player.nad_living_room`

## Using the Integration

### Media Player Entity

Each NAD device's media player entity provides complete control:

- **Power Control**: On/Off/Toggle with state feedback
- **Volume Control**: Volume slider (configurable range, default -92dB to -20dB)
- **Volume Buttons**: Up/Down with configurable step size
- **Mute Control**: Toggle, Mute, Unmute
- **Source Selection**: Dropdown with all available NAD inputs
- **State Display**: Current power, volume, source, and mute status

### Available Sources

| Source Name | NAD Code | Description |
|------------|----------|-------------|
| Source 1-12 | 1-12 | Standard NAD inputs |
| Disc | disc | CD/DVD player |
| Video 1-3 | video1-3 | Video inputs |
| Tape 1-2 | tape1-2 | Tape deck inputs |
| Tuner | tuner | AM/FM tuner |
| Aux | aux | Auxiliary input |

*Note: Available sources may vary by model. Integration shows only sources supported by your device.*

### Volume Control Details

**Default Volume Range:**
- **Minimum**: -92dB (very quiet)
- **Maximum**: -20dB (reference level)
- **Step Size**: 4dB (adjustable)

**Remote Interface:**
- Volume displayed as 0-100 percentage
- Automatic conversion between dB and percentage
- Configurable during setup for your listening preferences

**Example Conversions:**
```
Remote Slider → NAD Volume
0%  → -92dB (minimum)
25% → -74dB
50% → -56dB
75% → -38dB
100% → -20dB (maximum)
```

### Multiple Device Control

- **Independent Control**: Each NAD device operates independently
- **Mixed Connections**: Control TCP, Telnet, and RS-232 devices simultaneously
- **Separate Entities**: Each device gets its own media player entity
- **Configuration Management**: Add/update/remove devices individually

## Troubleshooting

### Connection Issues

#### **TCP Connection Fails**
- Verify device IP address is correct
- Check device is powered on
- Ensure device is on same network as Remote
- Verify port 53 is accessible (firewall)
- Try Telnet connection as alternative

#### **Telnet Connection Fails**
- Verify IP address and custom port
- Check Telnet support is enabled on device
- Try standard port 23 if port 53 fails
- Verify network connectivity with ping test

### Device Not Responding

1. **Power Cycle Device**: Turn off, wait 10 seconds, turn back on
2. **Check Connections**: Verify cable connections (network or serial)
3. **Test Manually**: Use telnet or serial terminal to send test command
4. **Update Firmware**: Ensure device firmware is current
5. **Check Configuration**: Verify connection type matches device capabilities

### Remote Can't Find Integration

1. **Check Integration Running**: Look for "Driver is up" in logs
2. **Verify driver.json**: Must exist at project root
3. **Check mDNS**: Integration publishes via mDNS for discovery
4. **Network Issues**: Ensure Remote and integration on same network
5. **Restart Integration**: Stop and restart the integration

### Volume Control Issues

1. **Volume Range**: Adjust min/max volume in configuration
2. **Step Size**: Modify volume step if changes too large/small
3. **Response Lag**: Allow 500ms after commands for device to respond
4. **Mute State**: Check if device is muted

### Source Selection Issues

1. **Sources Not Shown**: Only supported sources appear in dropdown
2. **Source Change Fails**: Verify source is connected to device
3. **Wrong Source Active**: Check device's physical input selection

## Advanced Configuration

### Custom Volume Ranges

Customize volume behavior during setup or device update:
```yaml
min_volume: -80    # Don't go below -80dB
max_volume: -10    # Don't exceed -10dB (safer for speakers)
volume_step: 2     # Finer volume control (2dB steps)
```

### Serial Port Configuration

For RS-232 connections, common serial port paths:

**Linux/Docker:**
- `/dev/ttyUSB0` - First USB serial adapter
- `/dev/ttyUSB1` - Second USB serial adapter
- `/dev/ttyS0` - Built-in serial port

**Docker Serial Access:**
```yaml
devices:
  - "/dev/ttyUSB0:/dev/ttyUSB0"
```

### Network Port Configuration

**Common Ports:**
- `53` - Default NAD TCP/Telnet port
- `23` - Standard Telnet port
- Custom ports as configured on device

## Development

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Required packages
- ucapi>=0.5.1
- ucapi-framework>=1.4.0
- nad-receiver>=0.0.12
```

### Local Development

1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run integration: `python -m intg_nadav`

### Testing with Real Device
```bash
# Set configuration path for local testing
export UC_CONFIG_HOME=./config

# Run integration
python -m intg_nadav
```

### Project Structure
```
uc-intg-nadav/
├── intg_nadav/                # Main package
│   ├── __init__.py            # Package initialization & main entry
│   ├── __main__.py            # Module execution support
│   ├── config.py              # Configuration management
│   ├── device.py              # NAD device implementation
│   ├── driver.py              # Integration driver
│   ├── media_player.py        # Media player entity
│   └── setup_flow.py          # Setup flow handler
├── .github/workflows/         # GitHub Actions CI/CD
│   └── build.yml              # Automated build pipeline
├── .vscode/                   # VS Code configuration
│   └── launch.json            # Debug configuration
├── Dockerfile                 # Container build instructions
├── docker-compose.yml         # Docker deployment
├── driver.json                # Integration metadata
├── requirements.txt           # Dependencies
├── pyproject.toml             # Python project config
└── README.md                  # This file
```

### Key Implementation Details

#### **NAD Protocol**
- Uses `nad-receiver` Python library
- Three connection types: TCP, Telnet, RS-232
- Text-based ASCII protocol
- Commands specific to NAD receivers
- Automatic connection handling per type

#### **Connection Type Detection**
```python
if connection_type == "TCP":
    client = NADReceiverTCP(host)
elif connection_type == "Telnet":
    client = NADReceiverTelnet(host, port)
```

#### **Volume Scaling**
```python
# NAD range: -92dB to -20dB (72 steps default)
# Remote range: 0-100 (percentage)
# Formula: volume_percent = ((db_value - min_vol) / (max_vol - min_vol)) * 100
# Reverse: db_value = (volume_percent * (max_vol - min_vol) / 100) + min_vol
```

#### **Device State Management**
- PollingDevice base class for periodic state updates
- Configurable poll interval (default: 10 seconds)
- Automatic reconnection on connection loss
- Event-driven state propagation to entities

#### **Wake-Up Error Handling**
```python
async def _send_command(self, command: str, value=None):
    """Send command with wake-up retry logic."""
    try:
        result = await self._execute_command(command, value)
        return result
    except OSError as e:
        _LOG.debug("OS error (likely wake-up): %s, retrying...", e)
        await asyncio.sleep(0.5)
        return await self._execute_command(command, value)
```

### NAD Command Reference

Essential nad-receiver library methods used:
```python
# Power Control
client.main_power("on")      # Power on
client.main_power("off")     # Power off
client.main_power("?")       # Query power state

# Volume Control
client.main_volume("+")      # Volume up
client.main_volume("-")      # Volume down
client.main_volume("?")      # Query volume

# Mute Control
client.main_mute("on")       # Mute on
client.main_mute("off")      # Mute off
client.main_mute("?")        # Query mute

# Source Control
client.main_source("disc")   # Select disc input
client.main_source("?")      # Query current source

# Status Query
client.status()              # Get full device status (TCP only)
```

### Testing Protocol

#### **Connection Testing**
```python
# Test TCP connection
from nad_receiver import NADReceiverTCP
client = NADReceiverTCP("192.168.1.100")
status = client.status()
assert status is not None

# Test Telnet connection
from nad_receiver import NADReceiverTelnet
client = NADReceiverTelnet("192.168.1.100", 53)
power = client.main_power("?")
assert power is not None

# Test RS-232 connection
from nad_receiver import NADReceiver
client = NADReceiver("/dev/ttyUSB0")
power = client.main_power("?")
assert power is not None
```

#### **Command Testing**
```python
# Test power control
client.main_power("on")
await asyncio.sleep(0.5)
state = client.main_power("?")
assert state == "On"

# Test volume control
client.main_volume("+")
await asyncio.sleep(0.5)
# Verify volume increased
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test with real NAD device
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Style

- Follow PEP 8 Python conventions
- Use type hints for all functions
- Async/await for all I/O operations
- Comprehensive docstrings
- Descriptive variable names
- Header comments only (no inline comments)

## Credits

- **Developer**: Meir Miyara
- **NAD**: High-performance audio amplifiers and receivers
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **nad-receiver**: Python library for NAD control protocol
- **Community**: Testing and feedback from UC community

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see LICENSE file for details.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-nadav/issues)
- **UC Community Forum**: [General discussion and support](https://community.unfoldedcircle.com/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **NAD Support**: [Official NAD Support](https://nadelectronics.com/support/)

---

**Made with ❤️ for the Unfolded Circle and NAD Communities** 

**Thank You**: Meir Miyara
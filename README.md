# NAD A/V Receivers & Amplifiers Integration for Unfolded Circle Remote 2/3

Control your NAD audio gear directly from your Unfolded Circle Remote 2 or Remote 3 - from **BluOS streaming amplifiers** (M10, M33, C700, C658) to classic **T-Series AVRs**, **D-Series digital amps**, and **RS-232** models. One integration, four connection types, with volume, source/input switching, transport control, now-playing metadata, and media browsing.

![NAD](https://img.shields.io/badge/NAD-A%2FV%20Receivers-blue)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-nadav?style=flat-square)](https://github.com/mase1981/uc-intg-nadav/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-nadav?style=flat-square)](https://github.com/mase1981/uc-intg-nadav/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-nadav/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

---

## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️

---

## What's New in 2.0

- 🆕 **BluOS streaming support** - NAD M10, M33, C700, C658 and other BluOS models are now controllable over the network (port 11000), including a working volume slider, transport controls, now-playing metadata with album art, physical input selection, and a media browser.
- 🆕 **Media browser** for BluOS models - browse and play **Inputs**, **Presets**, and the current **Queue**.
- 🆕 **Select entities** - source/input, preset and repeat (BluOS); speaker A / speaker B (classic).
- 🆕 **Sensor entities** - model, current source, connection status, and firmware version (classic).
- ✅ **Fixed setup for BluOS devices** - previously an M10/M33 could not be set up because it does not speak the classic NAD Telnet protocol.
- ✅ **Reliable entity control** - corrected device identifiers so entities register and respond in activities (volume slider now selectable).
- ⬆️ Rebuilt on `ucapi-framework 1.9.5` / `ucapi 0.7.0`.

> **Upgrading from 1.x?** Existing Telnet / TCP / RS-232 devices are migrated automatically on first start - no need to remove and re-add them. You may need to re-add entities to your activities.

---

## Supported Devices & Connection Types

| Connection | Default Port | Typical Models | Protocol |
|---|---|---|---|
| **BluOS / Streaming** | 11000 | M10 (v1/v2), M33, C700, C658, C399 (with BluOS) and other BluOS players | BluOS Custom Integration API (HTTP) |
| **Telnet** | 23 | Classic T-Series AVRs (T748, T758, T778, T787...) | NAD Telnet (`Main.*` commands) |
| **TCP** | 53 | D-Series digital amps (e.g. D 7050) | NAD TCP |
| **RS-232** | serial | Any NAD model with a DB9 serial port | NAD RS-232 |

> **Not sure which one?** If your unit runs the **BluOS** app (streaming, multi-room), choose **BluOS**. If it's a classic **T-Series** receiver, choose **Telnet**. The setup screen has an auto-port option so you don't need to remember port numbers.

---

## Features by Connection Type

### 🎵 BluOS / Streaming (M10, M33, C700, C658 ...)

- **Media player** - power (play/standby), volume slider (0-100), mute, play/pause, stop, next/previous, seek, shuffle, repeat.
- **Now playing** - title, artist, album, and album art on the Remote.
- **Input selection** - switch between physical inputs (HDMI eARC, Optical, Coaxial, Analog, Phono, Bluetooth) discovered live from the device.
- **Media browser** - browse and play **Inputs**, **Presets**, and the current **Queue**.
- **Select entities** - Source (inputs), Preset, Repeat mode.
- **Sensors** - Model, Current Source, Connection status.

### 🎛️ Classic T-Series / D-Series / RS-232

- **Media player** - power on/off/toggle, volume slider (configurable dB range), volume up/down, mute/unmute, source selection.
- **Select entities** - Source, Speaker A, Speaker B.
- **Sensors** - Model, Firmware Version, Current Source, Connection status.

### 🎚️ General

- **Multiple devices** - control any number of NAD units, mixing BluOS and classic connections.
- **Independent configuration** - each device is set up and stored separately.
- **Reboot & standby survival** - devices reconnect automatically after Remote or device restarts.

---

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Go to the [**Releases**](https://github.com/mase1981/uc-intg-nadav/releases) page.
2. Download the latest `uc-intg-nadav-<version>-aarch64.tar.gz`.
3. Open your Remote's web interface (`http://your-remote-ip`).
4. Go to **Settings -> Integrations -> Add Integration -> Install Custom**.
5. Upload the downloaded `.tar.gz` and follow the setup.

### Option 2: Docker (Advanced)

The integration is available as a pre-built Docker image from GitHub Container Registry.

**Image**: `ghcr.io/mase1981/uc-intg-nadav:latest`

**Docker Run (one-liner):**
```bash
docker run -d --name uc-intg-nadav --restart unless-stopped --network host -v ./data:/data -e UC_CONFIG_HOME=/data -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 ghcr.io/mase1981/uc-intg-nadav:latest
```

**Docker Compose:**
```yaml
services:
  uc-intg-nadav:
    image: ghcr.io/mase1981/uc-intg-nadav:latest
    container_name: uc-intg-nadav
    network_mode: host
    volumes:
      - ./data:/data
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
    restart: unless-stopped
```

---

## Configuration

### Step 1 - Prepare your device
- Power the device on and connect it to your network (Ethernet recommended for classic models).
- Give it a **static IP** or DHCP reservation.
- Note its **IP address**.
- For **BluOS** models, confirm the unit shows up in the BluOS app.

### Step 2 - Add the integration
1. Go to **Settings -> Integrations** and start the NAD setup.
2. Fill in the form:
   - **Device Name** - e.g. "Living Room M10".
   - **Connection Type** - choose **Telnet**, **BluOS / Streaming**, **TCP**, or **RS-232**.
   - **IP Address** - the device IP (network models).
   - **Port** - leave at **0** to auto-select the right port (BluOS 11000 / Telnet 23 / TCP 53), or enter a custom port.
   - **Serial Port** - only for RS-232 (e.g. `/dev/ttyUSB0`).
3. For **Telnet / RS-232**, a second screen lets you name your input **Sources** (Source 1-12). BluOS and TCP discover sources automatically.
4. The integration tests the connection and creates the entities.

### Entities created
Entity IDs follow `{type}.nad_{host}_{port}.{sub}`, for example:
- `media_player.nad_192_168_1_50_11000`
- `select.nad_192_168_1_50_11000.source`
- `sensor.nad_192_168_1_50_11000.model`

Add the media player (and any selects/sensors you want) to your activities and profiles.

---

## Volume Notes

- **BluOS** models report and accept volume as **0-100%** natively - the slider maps 1:1.
- **Classic** models use a **dB range** (default **-92 dB** to **-20 dB**, step **4 dB**), presented on the Remote as **0-100%**:

  | Remote Slider | NAD Volume |
  |---|---|
  | 0% | -92 dB (min) |
  | 50% | -56 dB |
  | 100% | -20 dB (max) |

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| **M10 / M33 / BluOS unit "Connection refused"** | These are BluOS models - choose **BluOS / Streaming**, not Telnet. They do not respond on port 23. |
| **No volume slider in an activity** | Make sure the **media player** entity (not just a button) is added to the activity; the media player exposes the numeric volume feature. |
| **Setup fails immediately** | Verify the IP is correct and the device is powered on and on the same subnet. Leave **Port = 0** to auto-select. |
| **Sources empty (classic)** | Re-run setup and enter names for the inputs you use on the Sources screen. |
| **Inputs empty (BluOS)** | Inputs are read from the device at runtime; ensure the unit is reachable and try reloading the integration. |

---

## Credits

- **Developer**: Meir Miyara
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi / ucapi-framework)
- **BluOS**: BluOS Custom Integration API
- **Community**: Testing and feedback from the UC community

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-nadav/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **NAD Support**: [Official NAD Support](https://nadelectronics.com/support/)

---

**Made with ❤️ for the Unfolded Circle and NAD Communities** - Meir Miyara

# E-Friends Meter Integration

A **custom integration** for [Home Assistant](https://www.home-assistant.io/) that reads or writes data to an [Efriends](https://www.efriends.at/). It allows you to monitor energy consumption/production and (optionally) peer trading information within Home Assistant.

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
   - [Manual Installation](#manual-installation)
   - [Installation via HACS (optional)](#installation-via-hacs-optional)
3. [Setup in Home Assistant](#setup-in-home-assistant)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)
6. [Debug Logging](#debug-logging)
7. [License](#license)

---

## Features

- **Read mode** (default):
  - Connects via Socket.IO to the E-Friends device/server.
  - Retrieves measurements like power (L1, L2, L3, total), voltage, current, etc.
  - Creates Home Assistant sensors for these values.
- **Write mode**:
  - Periodically sends locally measured power data (e.g., from a Home Assistant sensor) to the E-Friends server via HTTP POST.
  - Uses an API key for authentication (you get it from efriends support).
- **Peer Trading (optional)**:
  - Captures trading data (energy balance, order volume, etc.).
  - Dynamically creates sensors for each trader ID.

## Installation

### Manual Installation

1. Download this repository as a ZIP file (or clone it).
2. In your Home Assistant configuration directory (often named `config/`), create a folder called `custom_components` if it does not already exist.
3. Copy the entire `efriends` folder (containing `__init__.py`, `sensor.py`, `manifest.json`, etc.) into `config/custom_components/efriends/`.
4. Restart Home Assistant.

### Installation via HACS (optional)

1. Open the Home Assistant interface and go to **HACS**.
2. Select **Integrations**, then click the three-dot menu (or the plus icon) for **Custom Repositories**.
3. Enter the URL of this GitHub repository and select **Integration** as the category.
4. Click **Add** to add the custom repository.
5. After it’s added, search for “E-Friends Meter” in HACS, and install it.
6. Restart Home Assistant.

## Setup in Home Assistant

1. Go to **Settings > Devices & Services > + Add Integration**.
2. Search for **“E-Friends Meter”** and select it.
3. In the dialog, provide:
   - **Host**: IP address (or hostname) of your E-Friends device/server.
   - **Mode**: `read` (read data) or `write` (send data).
   - **Consumption Entity** (only in write mode): The entity ID that provides local consumption data (e.g., `sensor.my_power_usage`).
   - **API Key** (only in write mode, you get it from efriends support): Required for sending data to the E-Friends server.
4. Save and wait for the integration to set up. The sensors should then appear in Home Assistant.

## Configuration

- **Host**: The E-Friends server IP (e.g., `192.168.0.100`) or hostname.
- **Mode**:
  - `read`: Default mode. Creates sensors for live meter data.
  - `write`: Sends averaged consumption data from a specified Home Assistant sensor.
- **Interval**: The integration posts new data at a fixed interval (e.g., every 5 seconds) in write mode.
- **API Key**: Required for authentication when writing data to the E-Friends server.

## Troubleshooting

- **Connection Refused**:  
  If you see “Connection refused” or “Max retries exceeded,” verify that the IP or hostname is correct, and that the device is reachable on the specified port (default 80).
- **Blocking Call Warning**:  
  In older versions, `requests.post` was called synchronously in an async function. This has been resolved by running it in an executor or using an async HTTP library.
- **Missing Sensors**:  
  If sensors do not appear, check the logs for errors. Ensure you have restarted Home Assistant after installation.

## Debug Logging

If you need more detailed logs, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.efriends: debug

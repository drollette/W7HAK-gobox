# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

W7HAK Go Box Telemetry System — a field-portable ham radio go box running a Python telemetry daemon on a Raspberry Pi Zero W. The Pi reads battery cell voltages (ADS1115 via I2C) and temperatures (DS18B20 via 1-Wire), writes to a local InfluxDB database, and exposes a Grafana dashboard over a USB gadget-mode Ethernet connection (no Wi-Fi required).

## Target Platform

All scripts and service files target **Raspberry Pi Zero W** running Raspberry Pi OS Lite. Python is system Python 3 (`/usr/bin/python3`). Development is done on macOS; deploy via `rsync` or `git clone` onto the Pi.

## Key Files

- `scripts/telemetry.py` — Main daemon. Runs in a `while True` loop with a 10-second sleep. Reads ADS1115 channels, applies resistor-ladder multipliers to recover per-cell voltages, reads DS18B20 sysfs files, and writes an InfluxDB point.
- `scripts/setup_pi.sh` — One-shot provisioning. Installs apt packages, pip packages, and enables the systemd service. Must be run as root on the Pi.
- `systemd/gobox_telemetry.service` — systemd unit. Runs as user `pi`, `Restart=on-failure`, `RestartSec=10`.

## Voltage Measurement Architecture

The ADS1115 measures tap voltages from a resistor ladder (not raw cell voltages). `telemetry.py` recovers actual stack voltages by multiplying each tap reading by a per-channel scalar, then derives individual cell voltages by subtraction:

```
stack_voltage[n] = tap_voltage[n] * multiplier[n]
cell_voltage[n]  = stack_voltage[n] - stack_voltage[n-1]   (cell1 = stack_voltage[0])
```

Multipliers: Cell1=2.0, Cell2=3.2, Cell3=4.3, Cell4=5.7. Changing the resistor network requires updating these constants in `telemetry.py`.

## InfluxDB Schema

- **Database:** `telemetry`
- **Measurement:** `battery`
- **Fields:** `cell1`–`cell4` (float, volts), `temp1_c`–`tempN_c` (float, °C, one per DS18B20 sensor found)
- No tags are written; add tags (e.g., `host`, `location`) if querying multiple nodes.

## Deployment

```bash
# On the Pi
sudo raspi-config   # Enable I2C and 1-Wire first, then reboot
git clone <repo> /home/pi/goBox
sudo bash /home/pi/goBox/scripts/setup_pi.sh
```

The setup script patches `ExecStart` in the service file to match the actual clone path.

## Hardware Constraints

- **Single-core CPU** — keep the telemetry loop lightweight; avoid threading or async unless profiling shows a bottleneck.
- **ADS1115 gain** is set to `1` (±6.144 V range) to safely accommodate divider output voltages. Do not raise gain without recalculating divider ratios.
- **DS18B20** is read via raw sysfs (`/sys/bus/w1/devices/28-*/w1_slave`) rather than a library to minimize dependencies.
- **USB gadget mode** — Pi static IP is `192.168.7.2` on `usb0`. Grafana on port 3000, InfluxDB on port 8086.

## 3D Models

STEP files in `3d_models/` are designed for **ABS only** (compression-frame battery assembly). Tolerances are ABS-specific; do not substitute other filaments without re-evaluating fit.

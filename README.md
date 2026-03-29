# W7HAK Go Box Telemetry System

A field-deployable amateur radio go box (callsign **W7HAK**) with real-time battery telemetry, environmental monitoring, and a local Grafana dashboard accessible over a USB gadget-mode connection.

---

## Hardware Architecture

| Component | Role |
|---|---|
| Raspberry Pi Zero W | Single-board computer running telemetry daemon, InfluxDB, and Grafana |
| 4S3P 45 Ah LiFePO4 pack | Primary power (nominal 12.8 V, 576 Wh) using 33140-format cells |
| ADS1115 (I2C 0x48) | 16-bit ADC reading four cell-tap voltages via resistor ladder |
| INA226 (I2C) | High-side current/power monitor for pack-level current and wattage |
| DS18B20 (GPIO 4, 1-Wire) | Ambient and cell temperature sensors |

### Voltage Measurement — Resistor Ladder

The ADS1115 cannot safely measure the full pack voltage directly. A resistor ladder divides each cell-stack tap down to a range the ADC can read. The `telemetry.py` script applies the following multipliers to recover actual stack voltages, then uses subtraction to isolate each cell:

| Channel | Tap | Multiplier |
|---|---|---|
| AIN0 | Cell 1 top | 2.0 |
| AIN1 | Cell 2 top | 3.2 |
| AIN2 | Cell 3 top | 4.3 |
| AIN3 | Cell 4 top (pack +) | 5.7 |

See `/wiring_diagrams/ads1115_resistor_ladder_schematic.svg` for the full schematic.

### Wiring & Schematics

Complete pin-by-pin wiring instructions — including the 12V fuse block topology, custom USB-C bulkhead wiring, and RFI mitigation techniques — can be found in [wiring_diagrams/WIRING_GUIDE.md](wiring_diagrams/WIRING_GUIDE.md).

---

## Accessing the Dashboard (USB Gadget Mode)

The Pi Zero W is configured as a USB OTG gadget. When connected to a laptop via the data USB port:

1. The Pi enumerates as a USB Ethernet adapter (`usb0`).
2. The Pi's static IP on that interface is `192.168.7.2`.
3. Navigate to `http://192.168.7.2:3000` in a browser to open Grafana.
4. InfluxDB listens on `http://192.168.7.2:8086`.

No Wi-Fi or external network is required in the field.

> **Setup reference:** Search for "Raspberry Pi Zero USB gadget mode" for instructions on enabling `dwc2` and `g_ether` overlays in `/boot/config.txt` and `/etc/modules`.

---

## Installation

### 1. Prepare the Pi

Enable **I2C** and **1-Wire** before running the setup script:

```bash
sudo raspi-config
# Interface Options → I2C → Enable
# Interface Options → 1-Wire → Enable
# Reboot
```

### 2. Clone the repository

```bash
cd /home/pi
git clone https://github.com/W7HAK/goBox.git
cd goBox
```

### 3. Run the setup script

```bash
sudo bash scripts/setup_pi.sh
```

This will:
- Install system packages (`python3-pip`, `i2c-tools`, `python3-smbus`)
- Install Python libraries (`adafruit-circuitpython-ads1x15`, `adafruit-circuitpython-ina226`, `influxdb`)
- Install, enable, and start the `gobox_telemetry` systemd service

### 4. Verify the service

```bash
sudo systemctl status gobox_telemetry.service
sudo journalctl -u gobox_telemetry.service -f
```

---

## Service Management

| Command | Action |
|---|---|
| `sudo systemctl start gobox_telemetry` | Start the telemetry daemon |
| `sudo systemctl stop gobox_telemetry` | Stop the telemetry daemon |
| `sudo systemctl restart gobox_telemetry` | Restart after config changes |
| `sudo systemctl disable gobox_telemetry` | Prevent autostart on boot |

---

## Repository Layout

```
goBox/
├── 3d_models/          # ABS compression-frame parts for the battery pack
├── wiring_diagrams/    # Schematics (resistor ladder, INA226 hookup)
├── scripts/
│   ├── telemetry.py    # Main telemetry daemon
│   └── setup_pi.sh     # One-shot provisioning script
└── systemd/
    └── gobox_telemetry.service   # systemd unit file
```

---

## 3D Models

The files in `/3d_models` are STEP files designed for **ABS filament** and a compression-frame battery assembly. They are specifically engineered for the dimensional tolerances of ABS (higher thermal stability, post-process acetone smoothing). Do not substitute PLA or PETG without re-evaluating clearances and structural load paths.

| File | Description |
|---|---|
| `33140_3S_4P_CENTER.step` | Center compression frame for 3P cell group |
| `33140_3S_4P_END_CAP.step` | End cap for the 4S3P pack assembly |

---

## License

Released for amateur radio and personal use. No warranty. 73 de W7HAK.

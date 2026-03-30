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

### Bill of Materials

For a complete list of hardware, sensors, and passive components required to build this system, please see the [Bill of Materials (BOM)](BOM.md).

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

### Enabling USB Gadget Mode on the Pi Zero W

Perform these steps once on the Pi before first use:

**1. Enable the `dwc2` overlay** — append to `/boot/config.txt`:
```
dtoverlay=dwc2
```

**2. Load the `g_ether` module at boot** — in `/etc/modules`, add a new line:
```
g_ether
```

**3. Assign a static IP to `usb0`** — append to `/etc/dhcpcd.conf`:
```
interface usb0
static ip_address=192.168.7.2/24
```

**4. On your laptop**, configure the USB Ethernet adapter that appears with a manual IP in the same subnet, e.g. `192.168.7.1/24`. No DHCP server is needed.

**5. Reboot the Pi.** The `usb0` interface will come up automatically on every subsequent boot.

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
git clone https://github.com/drollette/W7HAK-gobox.git
cd W7HAK-gobox
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

## Calibration

Because 1% tolerance resistors and shunt components still vary slightly, the default multipliers and correction factor in `telemetry.py` will likely need to be tuned to your specific hardware to get pinpoint accuracy.

### When to Calibrate

- After initial assembly, before first deployment
- After replacing any resistors in the voltage divider ladder
- After replacing the INA226 shunt resistor
- If Grafana cell voltage readings drift from multimeter measurements

### Running the Calibration Script

The interactive `calibrate.py` script automates the entire process:

```bash
cd /home/pi/W7HAK-gobox
python3 scripts/calibrate.py
```

The script will walk you through two steps:

**Step 1 — Cell Voltage Calibration**

You will need a calibrated digital multimeter (DMM).

1. Set your DMM to **DC Voltage (VDC)**, typically the 20V range.
2. For each of the 4 cells, measure the voltage directly across the cell terminals (positive to negative).
3. Enter each reading when prompted. LiFePO4 cells should read between **2.50V and 3.65V**.

The script reads the current ADS1115 tap voltages and computes corrected `CELL_MULTIPLIERS` using:

```
New Multiplier = True Stack Voltage / Raw Tap Voltage
```

**Step 2 — Shunt Resistance Calibration**

1. **Completely disconnect power from the system** before measuring.
2. Set your DMM to the **lowest Ohms/Resistance setting** (milliohms if available).
3. Short the leads together and zero the meter.
4. Measure the resistance directly across the shunt resistor terminals.
5. Enter the reading in Ohms (e.g., `0.0015` for a 1.5 milliohm shunt).

The script computes a new `CORRECTION_FACTOR` based on the nominal 2 milliohm shunt:

```
CORRECTION_FACTOR = 0.002 / Measured Resistance
```

**Step 3 — Apply Changes**

The script writes the updated `CELL_MULTIPLIERS` and `CORRECTION_FACTOR` directly to `scripts/telemetry.py`. Restart the service to apply:

```bash
sudo systemctl restart gobox_telemetry
```

### Manual Calibration

If you prefer to calibrate manually, measure the DC voltage from battery ground (Pack -) to each cell tap, then calculate:

```
New Multiplier = Current Multiplier × (True Voltmeter Voltage ÷ Calculated Stack Voltage)
```

Edit `CELL_MULTIPLIERS` in `scripts/telemetry.py` and restart the service.

---

## Repository Layout

```
goBox/
├── 3d_models/          # ABS compression-frame parts for the battery pack
├── wiring_diagrams/    # Schematics (resistor ladder, INA226 hookup)
├── scripts/
│   ├── telemetry.py    # Main telemetry daemon
│   ├── calibrate.py    # Interactive calibration utility
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

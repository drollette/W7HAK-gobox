# W7HAK Go Box Telemetry System

A field-deployable amateur radio go box (callsign **W7HAK**) with real-time battery telemetry, environmental monitoring, and a local Grafana dashboard accessible over a USB gadget-mode connection.

---

## Hardware Architecture

| Component | Role |
|---|---|
| Raspberry Pi Zero W | Single-board computer running telemetry daemon, InfluxDB, and Grafana |
| 4S3P 45 Ah LiFePO4 pack | Primary power (nominal 12.8 V, 576 Wh) using 33140-format cells |
| ADS1115 (I2C 0x48) | 16-bit ADC reading four cell-tap voltages via resistor ladder |
| 2x INA226 (I2C 0x40, 0x41) | High-side current/power monitors for solar input and system load |
| DS18B20 (GPIO 4, 1-Wire) | Ambient and cell temperature sensors |
| DC Fuse Block (marine-grade) | Central power distribution with individually fused load circuits |
| RF-silent 12V DC fan | Enclosure cooling, activated by hardware thermal switch |
| Normally-open thermal switch | Ambient temperature failsafe — engages fan at ~45 °C without GPIO control |
| DC-DC Buck-Boost Charge Controller | LTC3780 10A converter tuned to 14.6V CV / 5A CC LiFePO4 profile |

### Power Distribution & Charging

All system power flows from the battery through a single monitored path before reaching the fuse block. An **LTC3780 10A Buck-Boost Converter** allows charging from any unconditioned DC source (12V automotive charger, vehicle accessory port, generic power supply) via an Anderson Powerpole input connector. The LTC3780 is physically calibrated to a **14.6V CV / 5A CC** LiFePO4 charging profile using its onboard potentiometers (see [Charging Calibration](#charging-calibration) below).

```text
                        [External Universal DC Input Port]
                                       |
                                  [15A Fuse]
                                       |
                      (Mix 31 Ferrite Choke on Input Wires)
                                       |
                +---------------------------------------------+
                |     LTC3780 10A Buck-Boost Converter        |
                |   (Tuned to 14.6V CV / 5A CC via Pots)      |
                |         [Shielded 3D Printed Case]          |
                +---------------------------------------------+
                           |                       |
                     (Positive Out)          (Negative Out)
                           |                       |
                      (Mix 31 Ferrite Choke on Output Wires)
                           |                       |
                       [15A Fuse]                  |
                           |                       |
                           v                       |
[4S LiFePO4 Battery] -> [BMS] -> [Main Shunt] <----+ (Negative connects here)
                                       |
                               [25A Main Fuse]
                                       |
    =========================================================================
    ||                        12V DC FUSE BLOCK                            ||
    =========================================================================
          |              |              |                 |
     (10A G90)     (3A Buck/Pi)    (1A Fan)         (1A Telemetry)
```

| Circuit | Fuse | Notes |
|---|---|---|
| Xiegu G90 Transceiver | 10A blade | ~8A peak at 20W transmit |
| Raspberry Pi (12V-to-5V buck converter) | 3A blade | Protects 12V input side of converter |
| RF-silent fan + thermal switch | 1A blade | Fan draws < 0.3A; thermal switch in series |
| Telemetry sensors / microcontrollers | 1A blade | ADS1115, INA226, DS18B20 circuits |

All loads **must** be individually fused on this block. See [wiring_diagrams/WIRING_GUIDE.md](wiring_diagrams/WIRING_GUIDE.md) for complete routing details.

### Universal DC Charging

The system accepts a wide range of DC inputs (10–30V) via an external **Anderson Powerpole** connection on the enclosure panel. This input is routed through a **15A inline fuse** and **Mix 31 ferrite toroids** (input lines wrapped 5–7 turns) to an **LTC3780 10A Buck-Boost Converter** physically calibrated to a **14.6V CV / 5A CC** LiFePO4 charging profile.

Key design points:

- The LTC3780 **positive output** passes through a second **15A inline fuse** and **Mix 31 ferrite toroids** (output lines wrapped 5–7 turns) before connecting to the main positive bus (battery side of the 25A main fuse).
- The LTC3780 **negative output** connects to the **system/load side of the main current shunt** — not directly to the battery terminal. This ensures the System INA226 sees bidirectional current (positive = discharge, negative = charge), enabling the telemetry system to track charge current.
- The LTC3780 is housed in a **3D-printed protective enclosure** lined with **copper foil tape** on the inside surfaces to form a Faraday cage, suppressing broadband switching noise before it reaches the Xiegu G90.

**The negative output of the LTC3780 must pass through the main shunt. Do not wire it directly to the battery's negative terminal, or the telemetry script will not register the incoming charging current.**

### Thermal Management — RF-Silent Fan & Thermal Switch

An RF-silent 12V DC fan provides enclosure cooling. The fan is controlled entirely in hardware by a **normally-open (NO) thermal switch** wired in series on a dedicated 1A fused circuit from the DC fuse block. When the ambient enclosure temperature reaches approximately **45 °C**, the thermal switch closes and the fan runs.

This design is intentional: the thermal switch acts as an automatic hardware-level failsafe that does **not** require Raspberry Pi GPIO control or any software switching logic. This keeps RF noise from PWM or digital switching to an absolute minimum — critical for a ham radio go box operating on HF.

The DS18B20 ambient temperature sensor (read by `telemetry.py`) monitors the same enclosure environment. When telemetry readings approach 45 °C, the fan should be observed activating independently via the thermal switch.

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

### Analog Signal Filtering

Each resistor ladder output passes through a hardware RC low-pass filter before reaching the ADS1115 ADC input. This eliminates switching noise from the LTC3780 charger and other RF sources at the hardware level, producing clean readings without aggressive software filtering.

```text
[Battery Cell Tap] or [Shunt Sensor Out]
         |
         | (Raw, noisy analog signal)
         |
         +-----[ 1kΩ Resistor ]-----+---------> To ADC Input Pin / GPIO
                                    |
                                    +---[ 10µF Capacitor ]---+
                                    |                        |
                                    +---[ 0.1µF Ceramic ]----+
                                                             |
                                                             v
                                                    [ Telemetry Ground ]
```

The 1kΩ / 10µF filter provides a -3dB cutoff at ~16 Hz — well above the 0.1 Hz sample rate but far below the LTC3780 switching frequency (~300 kHz). The parallel 0.1µF ceramic capacitor extends high-frequency rejection. All capacitors must be rated **25V minimum** (the pack reaches 14.6V at full charge). See [wiring_diagrams/WIRING_GUIDE.md](wiring_diagrams/WIRING_GUIDE.md) Section 6a for detailed construction instructions.

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
2. Connect the **BLACK (negative) probe to the battery's main negative terminal** (Pack -). Leave it there for all four measurements.
3. Move the **RED (positive) probe** to each successive BMS cell tap, from Cell 1 through Cell 4 (Pack +), entering each cumulative stack voltage when prompted.
4. Readings should increase with each tap — roughly 3.3V, 6.6V, 9.9V, and 13.2V for a healthy 4S LiFePO4 pack.

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

## Charging Calibration

The LTC3780 buck-boost converter must be physically calibrated with a multimeter **before the battery is ever connected to the output**. This sets the constant-voltage (CV) ceiling and constant-current (CC) limit for a safe 4S LiFePO4 charge profile.

You will need:
- A 12V DC power source (bench supply, automotive battery, or wall adapter)
- A digital multimeter (DMM) with a **10A DC current range**
- A small flathead or Phillips screwdriver for the trimpots

### Step 1: Constant Voltage (CV) Tuning

1. **Do not connect the battery to the LTC3780 output.**
2. Connect a 12V power source to the LTC3780 **IN** terminals (observe polarity).
3. Set the multimeter to **DC Voltage** and connect the probes to the LTC3780 **OUT** terminals.
4. Slowly turn the **CV potentiometer** with a small screwdriver until the multimeter reads exactly **14.6V**.
5. This sets the voltage ceiling for 4S LiFePO4 (3.65V per cell).

### Step 2: Constant Current (CC) Tuning

1. Disconnect the multimeter from voltage mode.
2. Turn the **CC potentiometer counter-clockwise approximately 20 turns** to lower the current limit to its minimum.
3. Switch the multimeter to the **10A DC Current** setting and move the red probe to the **10A jack** on the meter.
4. Touch the multimeter probes directly to the LTC3780 **OUT** terminals (this creates a short circuit through the meter's internal shunt — this is safe because the CC limit is set to minimum).
5. Slowly turn the **CC potentiometer clockwise** until the multimeter reads exactly **5.00A**.
6. This limits the charge current to 5A, preventing overload on small external power supplies and keeping the charge rate within safe bounds for the battery pack.

### Step 3: Verify and Install

1. Disconnect the 12V source.
2. Reconfigure the multimeter back to standard DC Voltage mode.
3. The LTC3780 is now locked to a **14.6V / 5A** LiFePO4 CC/CV charging profile.
4. Install the module in its shielded 3D-printed enclosure and connect per the [Wiring Guide](wiring_diagrams/WIRING_GUIDE.md).

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

The files in `/3d_models` are STEP files designed for **ABS filament** and printed on a Bambu Lab printer. They are specifically engineered for the dimensional tolerances of ABS (higher thermal stability, post-process acetone smoothing). Do not substitute PLA or PETG without re-evaluating clearances and structural load paths.

| File | Description |
|---|---|
| `33140_3S_4P_CENTER.step` | Center compression frame for 3P cell group |
| `33140_3S_4P_END_CAP.step` | End cap for the 4S3P pack assembly |

A custom protective enclosure for the bare LTC3780 PCB should be 3D printed on the Bambu Lab printer in ABS. **Line the inside of the enclosure with copper foil tape** (with conductive adhesive) to form a Faraday cage that suppresses switching noise before it radiates into the HF environment. Ground the copper lining to the system negative bus.

---

## License

Released for amateur radio and personal use. No warranty. 73 de W7HAK.

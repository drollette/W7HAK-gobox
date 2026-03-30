# W7HAK Go Box: Master Wiring Guide (Pi Zero W Direct Telemetry)

## 1. 12V Power Distribution & Fuse Block

All system power originates from the 4S LiFePO4 battery and is routed through a single monitored path before reaching a central DC fuse block. Every load is individually fused.

### Power Flow Path

```
Battery Pack (+) → BMS Output (+) → Main Current Shunt → 25A Main Inline Fuse → System INA226 (IN+)
System INA226 (IN-) → DC Fuse Block Positive (+) Feed

Battery Pack (-) → BMS Output (-) → DC Fuse Block Negative (-) Bus
```

The System INA226 sits between the main fuse and the fuse block so it captures **all** downstream current draw (radio, Pi, fan, sensors).

### Fuse Block Circuit Assignments

Wire each load to its own fused circuit on the DC fuse block:

| Fuse Block Circuit | Fuse | Load |
|---|---|---|
| Circuit 1 | **10A** blade | Xiegu G90 Transceiver (~8A peak at 20W TX) |
| Circuit 2 | **3A** blade | 12V-to-5V Buck Converter (Pi + sensors on 5V rail) |
| Circuit 3 | **1A** blade | RF-silent fan + thermal switch (see Section 7) |
| Circuit 4 | **1A** blade | Telemetry sensors / microcontrollers (direct 12V devices) |

**Important:** All loads must be individually fused on the distribution block. Do not bypass the fuse block by wiring loads directly to the battery or shunt output.

---

## 2. 5V Power Foundation (Pi & Sensors)

The Raspberry Pi Zero W and all sensors operate on 3.3V logic. Power is supplied via a 12V-to-5V Buck Converter, which acts as an accessory on the fuse block.

* **Buck Converter Input:** Wire to a low-amp (e.g., 3A) circuit on the 12V Fuse Block.
* **Pi Pin 2 (5V):** Connect to Buck Converter Positive (+) Output.
* **Pi Pin 6 (GND):** Connect to Buck Converter Negative (-) Output.
* **RFI Protection:** Snap a Mix 31 ferrite bead on the 5V line near the Pi. Wrap the buck converter in grounded copper tape.

---

## 3. I2C Bus (Power & Cell Monitoring)

Daisy-chain the ADS1115 and both INA226 modules to the Pi's I2C pins.

* **Pi Pin 3 (SDA):** Connect to SDA on ADS1115, INA226 (Solar), and INA226 (System).
* **Pi Pin 5 (SCL):** Connect to SCL on ADS1115, INA226 (Solar), and INA226 (System).
* **ADS1115 Power:** VDD to Pi Pin 1 (3.3V), GND to Pi Pin 9. **Critical:** Solder a 0.1µF ceramic decoupling capacitor directly across VDD and GND on the ADS1115 to filter RF noise.
* **INA226 Addressing:**
  * Solar INA226: Address 0x40 (Default).
  * System INA226: Address 0x41 (Solder the A0 pad).

---

## 4. 1-Wire Bus (Temperature Sensors)

Wire all DS18B20 sensors in parallel.

* **Sensor GND (Pin 1):** Connect to Pi Pin 14 (GND).
* **Sensor DQ / Data (Pin 2):** Connect to Pi Pin 7 (GPIO 4).
* **Sensor VDD (Pin 3):** Connect to Pi Pin 1 (3.3V).
* **Pull-Up Resistor:** Solder a 4.7kΩ resistor between Pin 1 (3.3V) and Pin 7 (GPIO 4).

---

## 5. Custom USB-C Bulkhead (Gadget Mode)

To use a panel-mount USB-C connection instead of the fragile micro-USB port, solder to the test pads on the bottom of the Pi Zero W.

* **PP1 (5V):** USB-C VBUS
* **PP6 (GND):** USB-C GND
* **PP22 (D+):** USB-C D+ (Must be twisted with D- to reject RFI)
* **PP23 (D-):** USB-C D- (Must be twisted with D+ to reject RFI)

---

## 6. Cell Voltage Resistor Ladder

(See `ads1115_resistor_ladder_schematic.svg` for the visual diagram.)

Use 1% precision resistors. Build the ladder on a MakerSpot Protoboard HAT.

* **Cell 1 (3.6V):** To ADS1115 A0 via 10k/10k divider.
* **Cell 2 (7.2V):** To ADS1115 A1 via 22k/10k divider.
* **Cell 3 (10.8V):** To ADS1115 A2 via 33k/10k divider.
* **Cell 4 (14.4V):** To ADS1115 A3 via 47k/10k divider.

---

## 7. RF-Silent Fan & Thermal Switch Circuit

An RF-silent 12V DC fan provides enclosure cooling, controlled entirely by a hardware thermal switch (no GPIO, no software PWM). This keeps RF switching noise off the HF bands.

### Circuit Wiring

The fan and thermal switch are wired in series on a dedicated 1A fused circuit from the DC fuse block:

```
DC Fuse Block (Circuit 3, 1A fuse) ──(+)──→ Thermal Switch (NO) ──→ Fan (+)
Fan (-) ──→ DC Fuse Block Negative (-) Bus
```

### Component Details

* **Fan:** RF-silent 12V DC brushless fan. Mount on the enclosure wall or lid for maximum airflow across the battery pack and electronics. Typical draw < 0.3A.
* **Thermal Switch:** Normally-open (NO) bimetallic switch (e.g., KSD9700 series, 45 °C activation, rated for 12V DC). Mount inside the enclosure near the battery pack or warmest zone.

### How It Works

1. At ambient temperatures below ~45 °C, the thermal switch is **open** and the fan is off.
2. When enclosure temperature reaches ~45 °C, the thermal switch **closes**, completing the circuit and powering the fan.
3. When temperature drops below the switch's hysteresis point (typically ~35 °C), the switch opens and the fan stops.

### Design Rationale

* **No GPIO control:** The thermal switch is a passive hardware failsafe. It does not depend on the Raspberry Pi being operational or any software running. If the Pi crashes or the telemetry daemon hangs, the fan still activates.
* **No RF noise:** Bimetallic switches produce no switching transients. Unlike PWM or relay-based fan control, this approach introduces zero RF interference — critical for HF operation on the Xiegu G90.

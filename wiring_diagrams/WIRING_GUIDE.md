# W7HAK Go Box: Master Wiring Guide (Pi Zero W Direct Telemetry)

## 1. 12V Power Distribution & Fuse Block

All system power originates from the 4S LiFePO4 battery and is routed through a single monitored path before reaching a central DC fuse block. Every load is individually fused.

### Power Flow Path (Discharge)

```
Battery Pack (+) → BMS Output (+) → 25A Main Inline Fuse → System INA226 (IN+)
System INA226 (IN-) → DC Fuse Block Positive (+) Feed

Battery Pack (-) → BMS Output (-) → Main Current Shunt → DC Fuse Block Negative (-) Bus
```

The Main Current Shunt sits on the negative rail between the BMS output and the fuse block negative bus. All load current and charge current flows through this shunt, enabling the System INA226 to read **bidirectional current** (positive values = discharge/load, negative values = incoming charge).

### Charging Path (DC Input)

```
External Anderson Powerpole (+) → 15A Input Fuse → LTC3780 IN (+)
External Anderson Powerpole (-) → LTC3780 IN (-)

LTC3780 OUT (+/−) → LC Pi-Filter (see Section 8) → 15A Output Fuse (positive) → Main Positive Bus
                                                   → (negative) System/Load side of Main Current Shunt
```

**The negative output of the LTC3780 must pass through the main shunt. Do not wire it directly to the battery's negative terminal, or the telemetry script will not register the incoming charging current.**

The LTC3780 10A Buck-Boost Converter is physically calibrated to **14.6V CV / 5A CC** (4S LiFePO4 profile) using its onboard potentiometers. It accepts 10–30V DC input from automotive chargers, vehicle accessory ports, or generic power supplies. See the Charging Calibration section in the README for the calibration procedure.

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

Each divider output passes through an RC low-pass filter before reaching the ADS1115 input pin. See Section 6a below.

---

## 6a. Telemetry RC Low-Pass Filters

All analog signal lines between the resistor ladder and the ADS1115 ADC inputs must be filtered with hardware-level RC low-pass filters. These smooth sensor data and shunt RF noise before it reaches the ADC, eliminating high-frequency interference that would otherwise corrupt voltage readings — especially when the LTC3780 charger or other switching converters are active.

### Filter Topology

```text
=== TELEMETRY RC LOW-PASS FILTER TOPOLOGY ===

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

### Wiring Rules

1. **Resistor placement:** The 1kΩ resistor must be wired **in series** with the signal wire, as close to the ADS1115 input pin as physically possible. Solder it directly on the protoboard HAT at the ADC end of the trace, not at the battery tap end.
2. **Capacitor placement:** The 10µF capacitor must be wired **in parallel**, bridging the ADS1115 input pin directly to the telemetry common ground. Use a **minimum 25V rated** capacitor — the 4S LiFePO4 pack reaches 14.6V at full charge, which would stress standard 16V capacitors.
3. **RF decoupling:** Wire the 0.1µF ceramic capacitor **in parallel with the 10µF capacitor** (also bridging the ADC input pin to ground). The ceramic cap handles high-frequency RF noise that the larger electrolytic cannot absorb due to its parasitic inductance.
4. **Repeat for each channel:** Build one RC filter per ADS1115 input (A0–A3), for a total of 4 filters.

### Design Notes

* **Cutoff frequency:** The 1kΩ / 10µF combination yields a -3dB cutoff at approximately **16 Hz** (`f = 1 / (2π × R × C)`). This is well above the 0.1 Hz telemetry sample rate (10-second loop) but aggressively attenuates switching noise from the LTC3780 (~300 kHz) and other RF sources.
* **The 0.1µF ceramic** in parallel extends high-frequency rejection beyond what the 10µF electrolytic alone provides, creating a two-stage roll-off.
* **Ground reference:** All filter capacitors must connect to the same telemetry ground node used by the ADS1115 GND pin. Do not use separate ground points, or ground loops will introduce the noise the filter is designed to eliminate.

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

---

## 8. Universal DC Charging Circuit (LTC3780)

The LTC3780 10A Buck-Boost Converter allows the battery to be charged from any unconditioned DC source (10–30V) via an external Anderson Powerpole connector on the enclosure panel.

### Circuit Wiring

```
Panel Anderson Powerpole (+) ──→ [15A Input Fuse] ──→ LTC3780 IN (+)
Panel Anderson Powerpole (-) ──────────────────────→ LTC3780 IN (-)

LTC3780 OUT (+) ──┬──[ 1000µF Cap ]──┬── OUT (-)
                  └──[ 0.1µF Cap  ]──┘
                  |                  |
              =============================
             || Solid Ferrite Bead(s)     ||  (Both wires pass through together!)
              =============================
                  |                  |
             [15A Output Fuse]      |
                  |                  └──→ System/Load side of Main Current Shunt
                  └──→ Main Positive Bus (battery side of 25A main fuse)
```

**The negative output of the LTC3780 must pass through the main shunt. Do not wire it directly to the battery's negative terminal, or the telemetry script will not register the incoming charging current.**

### Component Details

* **Charge Controller:** LTC3780 10A DC-DC Buck-Boost Converter, physically calibrated to **14.6V CV / 5A CC** via onboard potentiometers (see Charging Calibration in README). Accepts 10–30V input to support automotive 12V, vehicle accessory 13.8V, and bench supply sources.
* **Input Fuse:** 15A inline ATC/ATO fuse on the positive input lead. Protects the external source and wiring from a charger fault.
* **Output Fuse:** 15A inline ATC/ATO fuse on the positive output lead (after the LC filter). Protects the battery and wiring from overcurrent.
* **Panel Connector:** Anderson Powerpole connector pair mounted on the enclosure panel. Use 30A-rated contacts with 10 AWG wire for the input run.

### Output LC Pi-Filter Construction

The LTC3780 is a high-frequency switching converter and **will** radiate broadband noise across HF without proper output filtering. The LC Pi-Filter below eliminates both differential-mode and common-mode noise before it reaches the Xiegu G90.

#### Stage 1: Differential Noise Filter (Capacitors)

Solder both capacitors **in parallel** directly across the LTC3780 **OUT** terminals (positive to positive, negative to negative):

1. **1000µF electrolytic capacitor** (minimum 25V rating) — absorbs low-frequency voltage ripple and current spikes from the switching converter.
2. **0.1µF ceramic capacitor** — bypasses high-frequency RF noise that the electrolytic cannot absorb due to its parasitic inductance.

**Warning:** Observe correct polarity on the electrolytic capacitor. The positive (longer) lead connects to the LTC3780 OUT (+) terminal, and the negative (marked with a stripe) connects to OUT (−). Reversed polarity can cause the capacitor to fail or vent.

#### Stage 2: Common-Mode Filter (Ferrite Beads)

Take the positive and negative wires leaving the capacitor stage and pass them **TOGETHER** through the solid ferrite bead(s):

1. Thread both the positive and negative output wires through the center hole of a small solid ferrite bead (approx. 1cm inner diameter).
2. If the bead is too tight for multiple wraps, string **2 or 3 beads back-to-back** on the wire pair to increase impedance.

**Both the positive and negative power wires MUST pass through the exact same ferrite bead together. If you pass only one wire through, the 5A of DC charging current will instantly magnetically saturate the core, rendering it completely useless for RF filtering.** When both wires pass through together, the DC currents cancel (they flow in opposite directions), leaving only the common-mode RF noise for the ferrite to absorb.

### Additional RFI Shielding

1. **Faraday cage enclosure:** House the bare LTC3780 PCB in a 3D-printed ABS enclosure (Bambu Lab printer). Line the interior with **copper foil tape** (conductive adhesive). Ground the copper lining to the system negative bus.
2. **Snap-on ferrites:** Add Mix 31 snap-on ferrite beads to any remaining exposed leads as close to the LTC3780 as possible.
3. If interference persists during charging, disconnect the charger while operating the Xiegu G90 on receive-sensitive modes (FT8, CW, SSB).

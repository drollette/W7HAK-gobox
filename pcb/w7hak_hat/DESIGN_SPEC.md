# W7HAK Telemetry HAT — PCB Design Specification

Custom Pi Zero W HAT implementing the 4-channel cell voltage monitor with RC filters from the project schematic.

## Board Specifications

| Parameter | Value |
|---|---|
| Board dimensions | 65mm × 30mm |
| Layers | 2 (F.Cu / B.Cu) |
| Board thickness | 1.6mm (standard) |
| Copper weight | 1 oz (35µm) |
| Min trace width | 0.25mm (10 mil) |
| Min clearance | 0.2mm (8 mil) |
| Min drill | 0.3mm |
| Surface finish | HASL or ENIG |
| Solder mask | Both sides (green) |
| Silkscreen | Front side |

## Mounting Holes

4x M2.5 through-holes matching the Pi Zero W mounting pattern:

| Hole | X (mm) | Y (mm) |
|---|---|---|
| MH1 | 3.5 | 3.5 |
| MH2 | 61.5 | 3.5 |
| MH3 | 3.5 | 26.5 |
| MH4 | 61.5 | 26.5 |

Drill: 2.7mm, annular ring: 5.5mm pad.

## Connectors

### J1 — BMS Battery Taps (JST-XH 5-pin, right-angle or vertical)

**Footprint:** JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical

| Pin | Signal | Wire Color (suggested) |
|---|---|---|
| 1 | Cell 4 tap (14.4V nominal) | Red |
| 2 | Cell 3 tap (10.8V nominal) | Orange |
| 3 | Cell 2 tap (7.2V nominal) | Yellow |
| 4 | Cell 1 tap (3.6V nominal) | Green |
| 5 | Telemetry Ground (Node B) | Black |

**Placement:** Left edge of board, centered vertically (~Y=15mm).

### J2 — ADS1115 ADC Module (JST-XH 6-pin, right-angle or vertical)

**Footprint:** JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical

| Pin | Signal |
|---|---|
| 1 | A0 (from Cell 1 RC filter output) |
| 2 | A1 (from Cell 2 RC filter output) |
| 3 | A2 (from Cell 3 RC filter output) |
| 4 | A3 (from Cell 4 RC filter output) |
| 5 | VDD (3.3V from Pi Pin 1) |
| 6 | GND (Telemetry Ground) |

**Placement:** Right edge of board, centered vertically (~Y=15mm).

### J3 — Raspberry Pi GPIO Header (2×20 pin female header)

**Footprint:** PinSocket_2x20_P2.54mm_Vertical

**Placement:** Bottom edge, centered horizontally. Pin 1 at left side (X≈11.5mm, Y≈26mm).

## Circuit — Resistor Ladder + RC Filters

### Per-Channel Signal Path

For each of the 4 channels (Cell 1 through Cell 4):

```
J1 pin ──→ [Rs: Series Resistor] ──┬── [Rf: 1kΩ Filter Resistor] ──┬──→ J2 pin (ADC input)
                                    │                                │
                                  [Rsh: 10kΩ Shunt]                [C1: 10µF 25V]
                                    │                                │
                                    └── GND                        [C2: 0.1µF]
                                                                     │
                                                                    GND
```

### Component Values Per Channel

| Channel | Cell Tap | Series R (Rs) | Shunt R (Rsh) | Filter R (Rf) | C1 | C2 | ADC Pin |
|---|---|---|---|---|---|---|---|
| CH4 | Cell 4 (14.4V) | Rs1 = 47kΩ 1% | Rsh1 = 10kΩ 1% | Rf1 = 1kΩ 1% | C1 = 10µF/25V | C5 = 0.1µF | A3 |
| CH3 | Cell 3 (10.8V) | Rs2 = 33kΩ 1% | Rsh2 = 10kΩ 1% | Rf2 = 1kΩ 1% | C2 = 10µF/25V | C6 = 0.1µF | A2 |
| CH2 | Cell 2 (7.2V) | Rs3 = 22kΩ 1% | Rsh3 = 10kΩ 1% | Rf3 = 1kΩ 1% | C3 = 10µF/25V | C7 = 0.1µF | A1 |
| CH1 | Cell 1 (3.6V) | Rs4 = 10kΩ 1% | Rsh4 = 10kΩ 1% | Rf4 = 1kΩ 1% | C4 = 10µF/25V | C8 = 0.1µF | A0 |

### Additional Components

| Ref | Value | Purpose | Connection |
|---|---|---|---|
| C9 | 0.1µF ceramic | ADS1115 VDD decoupling | Between J2 pin 5 (VDD) and J2 pin 6 (GND) |
| R_PU | 4.7kΩ | DS18B20 1-Wire pull-up | Between Pi Pin 1 (3.3V) and Pi Pin 7 (GPIO 4) |

## Resistor Footprints

All resistors: **0805 SMD** (2012 metric) or **through-hole axial** (choose one consistently).

- For easier hand-soldering: use through-hole axial (Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal)
- For compact layout: use 0805 SMD (Resistor_SMD:R_0805_2012Metric)

## Capacitor Footprints

- **10µF / 25V:** Through-hole radial electrolytic (Capacitor_THT:CP_Radial_D5.0mm_P2.50mm) or ceramic 1206 SMD if available at 25V.
- **0.1µF ceramic:** 0805 SMD (Capacitor_SMD:C_0805_2012Metric) or through-hole (Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm).

## GPIO Pin Usage

| Pi Pin | GPIO | Function | Connection |
|---|---|---|---|
| 1 | 3.3V Power | VDD | J2 pin 5 (ADS1115 VDD), R_PU (pull-up) |
| 3 | GPIO 2 (SDA) | I2C Data | Route to J2 (connect externally to ADS1115 SDA) |
| 5 | GPIO 3 (SCL) | I2C Clock | Route to J2 (connect externally to ADS1115 SCL) |
| 7 | GPIO 4 | 1-Wire | R_PU pull-up to 3.3V (for DS18B20) |
| 9 | GND | Ground | Telemetry ground plane, J1 pin 5, J2 pin 6 |

All other GPIO pins are passed through (directly connected pin-to-pin on the 2×20 header).

## Layout Guidelines

1. **Ground plane:** Pour a ground fill on the back copper layer (B.Cu) tied to the telemetry ground net. This provides a low-impedance return path and RF shielding.
2. **RC filter placement:** Place Rf and the capacitor pair (C1 + C2) as close to the J2 (ADC) connector as physically possible. Short traces between the filter caps and the ADC input minimize noise pickup.
3. **Divider placement:** Place Rs and Rsh in the middle zone between J1 and J2.
4. **Decoupling cap C9:** Place directly adjacent to J2 pins 5 and 6.
5. **Keep analog traces away from the GPIO header** to minimize digital noise coupling.
6. **Trace widths:** 0.25mm for signal traces, 0.5mm for power (3.3V, GND).

## Generating Gerber Files

After completing the layout in KiCad:

1. Open the PCB editor
2. File → Plot (or Fabrication → Plot)
3. Select layers: F.Cu, B.Cu, F.SilkS, B.SilkS, F.Mask, B.Mask, Edge.Cuts
4. Output format: Gerber
5. Output directory: `gerbers/`
6. Click "Plot"
7. Then click "Generate Drill Files" → Excellon format
8. Upload the `gerbers/` folder to your PCB fab (JLCPCB, PCBWay, OSH Park, etc.)

## Bill of Materials (PCB-specific)

| Qty | Reference | Value | Package | Notes |
|---|---|---|---|---|
| 1 | Rs1 | 47kΩ 1% | 0805 or axial | Series divider, Cell 4 |
| 1 | Rs2 | 33kΩ 1% | 0805 or axial | Series divider, Cell 3 |
| 1 | Rs3 | 22kΩ 1% | 0805 or axial | Series divider, Cell 2 |
| 1 | Rs4 | 10kΩ 1% | 0805 or axial | Series divider, Cell 1 |
| 4 | Rsh1–Rsh4 | 10kΩ 1% | 0805 or axial | Shunt resistors |
| 4 | Rf1–Rf4 | 1kΩ 1% | 0805 or axial | RC filter series |
| 1 | R_PU | 4.7kΩ | 0805 or axial | 1-Wire pull-up |
| 4 | C1–C4 | 10µF / 25V | Radial 5mm or 1206 | RC filter bulk |
| 5 | C5–C9 | 0.1µF | 0805 or disc | RF bypass + decoupling |
| 1 | J1 | JST-XH 5-pin | B5B-XH-A | BMS battery taps |
| 1 | J2 | JST-XH 6-pin | B6B-XH-A | ADS1115 interface |
| 1 | J3 | 2×20 female header | 2.54mm pitch | Pi GPIO |
| 4 | MH1–MH4 | M2.5 mounting hole | 2.7mm drill | Board mounting |

**Total: 14 resistors, 9 capacitors, 3 connectors, 4 mounting holes**

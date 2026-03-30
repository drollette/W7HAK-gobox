# W7HAK Go Box: Bill of Materials (BOM)

This is the complete parts list required to build the Pi Zero W telemetry system and the 4S LiFePO4 power distribution network.

## 1. Enclosure & Mounting

* **Enclosure:** Weatherproof rugged hard case (Size to fit your specific battery and radio dimensions. Ensure adequate depth for 33140 cells).
* **Faceplate/Deck:** ABS or Aluminum sheet, cut to fit the internal lip of the enclosure.
* **Stand-offs & Hardware:** M2.5 brass standoffs (for the Pi) and assorted M3/M4 stainless steel hardware for structural mounting.

## 2. Compute & Telemetry Brain

* **Microcontroller:** Raspberry Pi Zero W (Original, single-core is sufficient).
* **Prototyping Board:** MakerSpot Protoboard Breadboard HAT (or similar Pi Zero footprint proto-board).
* **Storage:** High-endurance MicroSD Card (16GB or 32GB).
* **ADC Module:** Adafruit ADS1115 (16-bit I2C).
* **Power Monitors:** 2x INA226 High-Side Current/Power Sensors (I2C).
* **Temperature Sensors:** 2x DS18B20 (TO-92 package, 1-Wire).

## 3. Power Storage & Distribution

* **Battery Cells:** 12x 33140-format LiFePO4 cells (Configured as 4S3P for ~45Ah).
* **BMS:** Daly 4S 12V 60A LiFePO4 Battery Protection Board (Hardware/Common Port version).
* **Main Fuse:** 25A Inline ATC/ATO blade fuse holder (between main current shunt and DC fuse block).
* **DC Fuse Block:** 12V Marine-grade Blade Fuse Block with negative bus (minimum 4 circuits).
* **Blade Fuses (ATC/ATO):** 1x 10A (G90), 1x 3A (buck converter), 2x 1A (fan circuit, telemetry sensors).
* **Step-Down Converter:** 12V to 5V Buck Converter (Minimum 3A output).
* **DC Charge Controller:** LTC3780 10A DC-DC Buck-Boost Converter, adjustable output, physically calibrated to 14.6V CV / 5A CC (4S LiFePO4 profile). Accepts 10–30V input.
* **LTC3780 Enclosure:** Custom 3D-printed protective case (ABS, Bambu Lab printer). Line interior with copper foil tape to form a Faraday cage for RFI suppression.
* **Charger Input Fuse:** 15A Inline ATC/ATO blade fuse holder (on charger positive input lead).
* **Charger Output Fuse:** 15A Inline ATC/ATO blade fuse holder (on charger positive output lead).
* **Wire:** 10 AWG silicone wire (Main power runs), 22 AWG solid-core wire (Telemetry).

## 4. Thermal Management

* **Cooling Fan:** RF-silent 12V DC brushless fan (sized for enclosure; typical draw < 0.3A).
* **Thermal Switch:** Normally-open (NO) bimetallic thermal switch, ~45 °C activation (KSD9700 series or equivalent, rated for 12V DC).
* **Note:** The thermal switch is wired in series with the fan on a dedicated 1A fused circuit. No GPIO or software control is used — the switch engages automatically at ambient temperature threshold.

## 5. Passive Components & RFI Mitigation

* **Resistor Ladder (1% Precision Metal Film):**
  * 4x 10kΩ
  * 1x 22kΩ
  * 1x 33kΩ
  * 1x 47kΩ
* **Pull-up Resistor:** 1x 4.7kΩ (For DS18B20 1-Wire bus).
* **Decoupling Capacitor:** 1x 0.1µF (104) Ceramic Capacitor (ADS1115 VDD/GND decoupling).
* **RC Low-Pass Filters (per analog signal line):**
  * 4x 1kΩ Resistors (1/4 Watt) — one per cell tap line to ADS1115 inputs A0–A3.
  * 4x 10µF Capacitors (minimum **25V rating**, ceramic or electrolytic). The 25V+ rating is critical because the 4S LiFePO4 pack reaches 14.6V at full charge, which would stress standard 16V capacitors.
  * 4x 0.1µF (104) Ceramic Capacitors — high-frequency RF decoupling, wired in parallel with the 10µF capacitors.
* **LTC3780 Output LC Filter:**
  * 1x 1000µF Electrolytic Capacitor (minimum **25V rating**). Differential noise filter soldered across LTC3780 OUT terminals.
  * 1x 0.1µF (104) Ceramic Capacitor. High-frequency bypass soldered in parallel with the 1000µF cap across LTC3780 OUT terminals.
  * 2–3x Small Solid Ferrite Beads (approx. 1cm inner diameter). Common-mode choke — both positive and negative output wires pass through together. Use multiple beads back-to-back if a single bead is too tight for the wire pair.
* **RFI Chokes (Snap-on):** Mix 31 Snap-on Ferrite Beads (Sized for 5V Pi power line and solar input).
* **Shielding:** Copper foil tape with conductive adhesive.

## 6. Panel Connectors

* **Gadget Mode Data:** USB-C Panel Mount / Bulkhead Connector (with breakout pads for D+/D-).
* **DC Charge Input:** Anderson PowerPole panel mount connector pair (30A-rated contacts) for external DC charging.
* **Power Outputs:** Anderson PowerPole panel mounts and/or 12V Marine "Cigarette" sockets.

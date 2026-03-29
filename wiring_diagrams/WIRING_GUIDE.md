# W7HAK Go Box: Master Wiring Guide (Pi Zero W Direct Telemetry)

## 1. 12V Power Distribution & Fuse Block

All system power originates from the 4S LiFePO4 battery and is routed through a central fuse block. To ensure the INA226 captures all power draw (including the Pi and the radio), wire it in this order:

* **Battery Positive (+):** Route to an inline main fuse (e.g., 30A), then to the **IN+** terminal of the "System" INA226.
* **System INA226 (IN-):** Connect to the Positive (+) feed terminal of your 12V Fuse Block.
* **Battery Negative (-):** Route directly to the Negative (-) bus of the 12V Fuse Block.
* **Accessories:** Wire your Xiegu G90 and any 12V sockets to individual fused circuits on this block.

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

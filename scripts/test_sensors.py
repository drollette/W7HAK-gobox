#!/usr/bin/env python3
"""
W7HAK Go Box - Live Sensor Test & Calibration Utility
Prints live data from ADS1115, INA226, and DS18B20 to the console every second.
"""

import time
import glob
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ina226 import INA226

# --- Configuration (Must match telemetry.py) ---
CELL_MULTIPLIERS = {"cell1": 2.0, "cell2": 3.2, "cell3": 4.3, "cell4": 5.7}
CORRECTION_FACTOR = 1.025
W1_BASE = "/sys/bus/w1/devices"

def read_ds18b20_temps():
    temps = {}
    for path in glob.glob(f"{W1_BASE}/28-*/w1_slave"):
        sensor_id = path.split("/")[-2]
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            if len(lines) >= 2 and "YES" in lines[0]:
                raw = lines[1].strip().split("t=")[-1]
                temps[sensor_id] = round(float(raw) / 1000.0, 2)
        except Exception:
            pass
    return temps

def main():
    print("Initializing I2C bus...")
    i2c = busio.I2C(board.SCL, board.SDA)

    print("Initializing ADS1115 at 0x48...")
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.gain = 1

    print("Initializing INA226 Solar (0x40) and System (0x41)...")
    ina_solar = INA226(i2c, address=0x40)
    ina_system = INA226(i2c, address=0x41)

    print("\nStarting Live Sensor Read... (Press Ctrl+C to quit)")
    time.sleep(2)

    try:
        while True:
            # ADS1115 cell voltages
            taps = [
                AnalogIn(ads, ADS.P0).voltage,
                AnalogIn(ads, ADS.P1).voltage,
                AnalogIn(ads, ADS.P2).voltage,
                AnalogIn(ads, ADS.P3).voltage,
            ]
            stack = [tap * mult for tap, mult in zip(taps, CELL_MULTIPLIERS.values())]

            # INA226 data (library returns mA, convert to A)
            sys_v = ina_system.bus_voltage
            sys_a = (ina_system.current * CORRECTION_FACTOR) / 1000.0
            sol_v = ina_solar.bus_voltage
            sol_a = ina_solar.current / 1000.0

            # Temps
            temps = read_ds18b20_temps()

            # Clear console and print
            print("\033[H\033[J", end="")
            print("=== W7HAK Go Box Live Telemetry ===")
            print(f"Pack Voltage:  {stack[3]:.2f} V")
            print(f"Cell 1: {stack[0]:.3f} V | Cell 2: {stack[1]-stack[0]:.3f} V | Cell 3: {stack[2]-stack[1]:.3f} V | Cell 4: {stack[3]-stack[2]:.3f} V")
            print(f"System Load:   {sys_v:.2f} V @ {sys_a:.3f} A ({sys_v * sys_a:.1f} W)")
            print(f"Solar Input:   {sol_v:.2f} V @ {sol_a:.3f} A ({sol_v * sol_a:.1f} W)")
            print("Temperatures:")
            if not temps:
                print("  No DS18B20 sensors found.")
            for sid, t in temps.items():
                print(f"  {sid}: {t} °C")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting calibration tool.")

if __name__ == "__main__":
    main()

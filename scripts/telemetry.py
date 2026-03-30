#!/usr/bin/env python3
"""
W7HAK Go Box Telemetry Script
Reads cell voltages from ADS1115 via I2C and temperature from DS18B20 via 1-Wire,
then writes data to a local InfluxDB instance every 10 seconds.

Hardware:
  - Raspberry Pi Zero W
  - ADS1115 ADC at I2C address 0x48
  - DS18B20 temperature sensor on GPIO 4 (1-Wire)
  - 4S3P LiFePO4 battery pack with resistor ladder voltage dividers

Resistor ladder multipliers (to recover actual cell stack voltages from divider output):
  Cell 1 (bottom): 2.0
  Cell 2:          3.2
  Cell 3:          4.3
  Cell 4 (top):    5.7
"""

import time
import glob
import logging
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ina226
from influxdb import InfluxDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# --- Configuration ---
INFLUX_HOST = "localhost"
INFLUX_PORT = 8086
INFLUX_DB   = "telemetry"
MEASUREMENT = "battery"

# Resistor ladder multipliers to recover actual cell-stack voltage
CELL_MULTIPLIERS = {
    "cell1": 2.0,
    "cell2": 3.2,
    "cell3": 4.3,
    "cell4": 5.7,
}

# Shunt resistor correction factor — compensates for component tolerances
CORRECTION_FACTOR = 1.025

# 1-Wire sysfs base path for DS18B20
W1_BASE = "/sys/bus/w1/devices"


# --- Helpers ---

def read_ds18b20_temps() -> dict:
    """
    Read all DS18B20 sensors found in the 1-Wire sysfs tree.
    Returns a dict keyed by sensor ID with temperature in Celsius.

    Note: The enclosure contains a hardware thermal switch (~45 °C normally-open)
    wired in series with an RF-silent fan on the DC fuse block.  When DS18B20
    ambient readings approach 45 °C the fan should be observed activating
    independently — no software action is required.
    """
    temps = {}
    sensor_dirs = glob.glob(f"{W1_BASE}/28-*/w1_slave")
    for path in sensor_dirs:
        sensor_id = path.split("/")[-2]
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            if len(lines) >= 2 and "YES" in lines[0]:
                raw = lines[1].strip().split("t=")[-1]
                temps[sensor_id] = round(float(raw) / 1000.0, 2)
            else:
                log.warning("DS18B20 %s: CRC check failed", sensor_id)
        except (OSError, ValueError) as exc:
            log.error("DS18B20 %s read error: %s", sensor_id, exc)
    return temps


def read_cell_voltages(ads) -> dict:
    """
    Read all four single-ended ADS1115 channels and apply resistor ladder
    multipliers to recover actual per-cell stack voltages.

    The ADS1115 measures the voltage at each tap on the resistor ladder;
    subtractive logic gives the voltage contribution of each individual cell.
    """
    # Raw tap voltages (single-ended, referenced to GND)
    taps = [
        AnalogIn(ads, ADS.P0).voltage,
        AnalogIn(ads, ADS.P1).voltage,
        AnalogIn(ads, ADS.P2).voltage,
        AnalogIn(ads, ADS.P3).voltage,
    ]

    # Recover actual stack voltages using the divider multipliers
    stack = [tap * mult for tap, mult in zip(taps, CELL_MULTIPLIERS.values())]

    # Individual cell voltages via subtraction
    cells = {
        "cell1": round(stack[0], 4),
        "cell2": round(stack[1] - stack[0], 4),
        "cell3": round(stack[2] - stack[1], 4),
        "cell4": round(stack[3] - stack[2], 4),
    }
    return cells


def read_ina226_data(ina_solar, ina_system) -> dict:
    """
    Read bus voltage, corrected current, and power from both INA226 sensors.
    Current is multiplied by CORRECTION_FACTOR to account for shunt resistor tolerances.
    """
    return {
        "solar_voltage_v":  round(ina_solar.bus_voltage, 4),
        "solar_current_a":  round(ina_solar.current * CORRECTION_FACTOR, 4),
        "solar_power_w":    round(ina_solar.power, 4),
        "system_voltage_v": round(ina_system.bus_voltage, 4),
        "system_current_a": round(ina_system.current * CORRECTION_FACTOR, 4),
        "system_power_w":   round(ina_system.power, 4),
    }


def build_influx_payload(cells: dict, temps: dict, power: dict) -> list:
    fields = {**cells, **power}
    for idx, (sensor_id, temp_c) in enumerate(temps.items(), start=1):
        fields[f"temp{idx}_c"] = temp_c

    return [
        {
            "measurement": MEASUREMENT,
            "fields": fields,
        }
    ]


# --- Main loop ---

def main():
    # Set up I2C bus (shared by all sensors)
    i2c = busio.I2C(board.SCL, board.SDA)

    # ADS1115 — cell voltage measurement
    ads = ADS.ADS1115(i2c, address=0x48)
    # Set gain to ±6.144 V to accommodate resistor-ladder outputs
    ads.gain = 1

    # INA226 — current/power monitors
    ina_solar  = adafruit_ina226.INA226(i2c, address=0x40)
    ina_system = adafruit_ina226.INA226(i2c, address=0x41)

    # Connect to InfluxDB
    client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
    client.create_database(INFLUX_DB)
    client.switch_database(INFLUX_DB)

    log.info("W7HAK telemetry started. Writing to InfluxDB '%s'.", INFLUX_DB)

    while True:
        try:
            cells = read_cell_voltages(ads)
            temps = read_ds18b20_temps()
            power = read_ina226_data(ina_solar, ina_system)
            payload = build_influx_payload(cells, temps, power)
            client.write_points(payload)
            log.debug("Written: %s", payload)
        except Exception as exc:
            log.error("Telemetry loop error: %s", exc)

        time.sleep(10)


if __name__ == "__main__":
    main()

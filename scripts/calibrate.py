#!/usr/bin/env python3
"""
W7HAK Go Box Calibration Script

Calibrates the battery monitoring system by comparing user-measured multimeter
readings against the ADS1115 tap voltages, then computing corrected multipliers
and shunt correction factor. Updates telemetry.py in place.

Usage:
    python3 scripts/calibrate.py

Requirements:
    - System must be powered on with the battery connected
    - A calibrated digital multimeter (DMM)
    - Run from the repository root directory
"""

import os
import re
import sys

# ADS1115 imports — only needed when reading live tap voltages
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    HAS_HARDWARE = True
except (ImportError, NotImplementedError):
    HAS_HARDWARE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TELEMETRY_PATH = os.path.join(SCRIPT_DIR, "telemetry.py")

NUM_CELLS = 4
CELL_VOLTAGE_MIN = 2.50
CELL_VOLTAGE_MAX = 3.65
SHUNT_MIN = 0.0001
SHUNT_MAX = 0.01
NOMINAL_SHUNT_OHMS = 0.002  # Standard INA226 shunt resistor value


def print_banner():
    print()
    print("=" * 60)
    print("   W7HAK Go Box  —  Calibration Utility")
    print("=" * 60)
    print()


def print_section(title):
    print()
    print("-" * 60)
    print(f"  {title}")
    print("-" * 60)
    print()


def prompt_float(prompt_text, min_val, max_val, unit_label):
    """Prompt the user for a float within the given range, retrying on bad input."""
    while True:
        raw = input(prompt_text).strip()
        try:
            value = float(raw)
        except ValueError:
            print(f"  [!] Invalid input. Please enter a numeric value.\n")
            continue

        if value < min_val or value > max_val:
            print(f"  [!] Value {value} {unit_label} is outside the expected range")
            print(f"      of {min_val} to {max_val} {unit_label}.")
            print(f"      Please re-measure and try again.\n")
            continue

        return value


def read_tap_voltages():
    """Read raw ADS1115 tap voltages from hardware."""
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.gain = 1  # +/-6.144 V range

    taps = [
        AnalogIn(ads, ADS.P0).voltage,
        AnalogIn(ads, ADS.P1).voltage,
        AnalogIn(ads, ADS.P2).voltage,
        AnalogIn(ads, ADS.P3).voltage,
    ]
    return taps


def prompt_tap_voltages():
    """Prompt user to manually enter the raw tap voltages (fallback when no hardware)."""
    print("  Hardware not detected. Enter the raw ADS1115 tap voltages")
    print("  from the telemetry log or Grafana debug panel.\n")

    taps = []
    for i in range(NUM_CELLS):
        val = prompt_float(
            f"  Enter raw tap voltage for Channel {i} (e.g., 1.65): ",
            0.01, 6.0, "V"
        )
        taps.append(val)
    return taps


def calibrate_cells(taps):
    """
    Prompt user for individual cell voltages measured with a DMM,
    compute cumulative stack voltages, and derive new multipliers.
    """
    print_section("STEP 1: Cell Voltage Calibration")

    print("  Set your multimeter to DC Voltage (VDC), typically the 20V range.")
    print()
    print("  For each cell, place the RED probe on the cell's POSITIVE terminal")
    print("  and the BLACK probe on the cell's NEGATIVE terminal.")
    print()
    print("  LiFePO4 cells should read between 2.50V and 3.65V.")
    print()

    cell_voltages = []
    for i in range(1, NUM_CELLS + 1):
        voltage = prompt_float(
            f"  Enter voltage for Cell {i} (e.g., 3.32): ",
            CELL_VOLTAGE_MIN, CELL_VOLTAGE_MAX, "V"
        )
        cell_voltages.append(voltage)
        print()

    # Compute cumulative stack voltages from individual cells
    stack_voltages = []
    running = 0.0
    for v in cell_voltages:
        running += v
        stack_voltages.append(running)

    # Compute new multipliers: multiplier = stack_voltage / tap_voltage
    new_multipliers = {}
    for i in range(NUM_CELLS):
        key = f"cell{i + 1}"
        if taps[i] <= 0:
            print(f"  [!] Warning: Tap {i} reads 0V — cannot compute multiplier.")
            print(f"      Keeping existing multiplier for {key}.")
            new_multipliers[key] = None
        else:
            new_multipliers[key] = round(stack_voltages[i] / taps[i], 4)

    return cell_voltages, new_multipliers


def calibrate_shunt():
    """Prompt user for measured shunt resistance and compute correction factor."""
    print_section("STEP 2: Shunt Resistance Calibration")

    print("  *** SAFETY: Completely disconnect power from the system ***")
    print("  *** before measuring the shunt resistor.                ***")
    print()
    print("  Set your multimeter to the LOWEST Ohms/Resistance setting")
    print("  (milliohms if available). Zero/short the leads first.")
    print()
    print("  Place probes directly across the shunt resistor terminals.")
    print()

    measured = prompt_float(
        "  Enter measured shunt resistance in Ohms (e.g., 0.0015 for 1.5m\u03a9): ",
        SHUNT_MIN, SHUNT_MAX, "\u03a9"
    )

    correction_factor = round(NOMINAL_SHUNT_OHMS / measured, 4)

    return measured, correction_factor


def update_telemetry(new_multipliers, correction_factor):
    """Rewrite CELL_MULTIPLIERS and CORRECTION_FACTOR in telemetry.py."""
    with open(TELEMETRY_PATH, "r") as f:
        content = f.read()

    # Build replacement CELL_MULTIPLIERS block
    mult_lines = [
        "CELL_MULTIPLIERS = {",
    ]
    for key, val in new_multipliers.items():
        mult_lines.append(f'    "{key}": {val},')
    mult_lines.append("}")
    mult_block = "\n".join(mult_lines)

    # Replace CELL_MULTIPLIERS dict
    pattern_mult = re.compile(
        r"CELL_MULTIPLIERS\s*=\s*\{[^}]+\}",
        re.DOTALL,
    )
    if not pattern_mult.search(content):
        print("  [!] Could not locate CELL_MULTIPLIERS in telemetry.py")
        return False

    content = pattern_mult.sub(mult_block, content)

    # Replace CORRECTION_FACTOR
    pattern_cf = re.compile(r"CORRECTION_FACTOR\s*=\s*[\d.]+")
    if not pattern_cf.search(content):
        print("  [!] Could not locate CORRECTION_FACTOR in telemetry.py")
        return False

    content = pattern_cf.sub(f"CORRECTION_FACTOR = {correction_factor}", content)

    with open(TELEMETRY_PATH, "w") as f:
        f.write(content)

    return True


def print_summary(cell_voltages, new_multipliers, measured_shunt, correction_factor):
    """Print a summary of all calibration values."""
    print_section("Calibration Complete")

    print("  Cell Voltages (measured):")
    for i, v in enumerate(cell_voltages, start=1):
        print(f"    Cell {i}:  {v:.4f} V")
    print()

    print("  New Multipliers (written to telemetry.py):")
    for key, val in new_multipliers.items():
        print(f"    {key}:  {val}")
    print()

    print(f"  Measured Shunt Resistance:  {measured_shunt} \u03a9")
    print(f"  New Correction Factor:      {correction_factor}")
    print()

    print("  Restart the telemetry service to apply changes:")
    print()
    print("    sudo systemctl restart gobox_telemetry")
    print()


def main():
    print_banner()

    if not os.path.isfile(TELEMETRY_PATH):
        print(f"  [!] Cannot find telemetry.py at: {TELEMETRY_PATH}")
        print("      Run this script from the repository root directory.")
        sys.exit(1)

    # Read current tap voltages from ADS1115 (or prompt if no hardware)
    print("  Reading ADS1115 tap voltages...")
    print()

    if HAS_HARDWARE:
        try:
            taps = read_tap_voltages()
            print("  Current raw tap readings:")
            for i, t in enumerate(taps):
                print(f"    Channel {i}: {t:.4f} V")
            print()
        except Exception as exc:
            print(f"  [!] Could not read ADS1115: {exc}")
            print("      Falling back to manual entry.\n")
            taps = prompt_tap_voltages()
    else:
        taps = prompt_tap_voltages()

    # Step 1: Cell voltage calibration
    cell_voltages, new_multipliers = calibrate_cells(taps)

    # Read existing multipliers as fallback for any channels that failed
    with open(TELEMETRY_PATH, "r") as f:
        content = f.read()
    existing = re.findall(r'"(cell\d)":\s*([\d.]+)', content)
    existing_map = {k: float(v) for k, v in existing}

    for key in new_multipliers:
        if new_multipliers[key] is None:
            new_multipliers[key] = existing_map.get(key, 1.0)

    # Step 2: Shunt resistance calibration
    measured_shunt, correction_factor = calibrate_shunt()

    # Write updated values to telemetry.py
    print()
    print("  Writing updated values to telemetry.py...")

    if update_telemetry(new_multipliers, correction_factor):
        print("  Done.")
        print_summary(cell_voltages, new_multipliers, measured_shunt, correction_factor)
    else:
        print("  [!] Failed to update telemetry.py. Please edit manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()

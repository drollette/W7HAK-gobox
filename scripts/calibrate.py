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

# Expected stack voltage bounds at each tap (cumulative LiFePO4 cells)
STACK_MIN = [CELL_VOLTAGE_MIN * n for n in range(1, NUM_CELLS + 1)]
STACK_MAX = [CELL_VOLTAGE_MAX * n for n in range(1, NUM_CELLS + 1)]


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
    Prompt user for cumulative stack voltages measured with a DMM from the
    battery negative to each successive BMS tap, then derive new multipliers.

    The user keeps the BLACK (negative) probe on the battery's main negative
    terminal and moves only the RED (positive) probe to each tap in order.
    This yields cumulative stack voltages that map directly to what the
    resistor ladder measures, making the multiplier math straightforward.
    """
    print_section("STEP 1: Cell Voltage Calibration")

    print("  Set your multimeter to DC Voltage (VDC), typically the 20V range.")
    print()
    print("  Connect the BLACK (negative) probe to the battery's MAIN")
    print("  NEGATIVE terminal (Pack -). Leave it there for all four")
    print("  measurements.")
    print()
    print("  You will move only the RED (positive) probe to each successive")
    print("  BMS cell tap, from Cell 1 (bottom) through Cell 4 (top/Pack +).")
    print()
    print("  Each reading is cumulative — the voltage should increase with")
    print("  each tap. A healthy 4S LiFePO4 pack reads roughly 3.3V, 6.6V,")
    print("  9.9V, and 13.2V at the four taps.")
    print()

    tap_labels = [
        "Tap 1  (Cell 1 top)",
        "Tap 2  (Cell 2 top)",
        "Tap 3  (Cell 3 top)",
        "Tap 4  (Pack +)   ",
    ]
    tap_examples = ["3.32", "6.65", "9.98", "13.31"]

    stack_voltages = []
    for i in range(NUM_CELLS):
        voltage = prompt_float(
            f"  {tap_labels[i]} — enter voltage (e.g., {tap_examples[i]}): ",
            STACK_MIN[i], STACK_MAX[i], "V"
        )

        # Each tap must be higher than the previous
        if stack_voltages and voltage <= stack_voltages[-1]:
            print(f"  [!] Tap {i + 1} ({voltage:.4f}V) must be higher than")
            print(f"      Tap {i} ({stack_voltages[-1]:.4f}V). Please re-measure.")
            print()
            # Re-prompt via recursion-free retry
            while voltage <= stack_voltages[-1]:
                voltage = prompt_float(
                    f"  {tap_labels[i]} — enter voltage (e.g., {tap_examples[i]}): ",
                    STACK_MIN[i], STACK_MAX[i], "V"
                )
                if voltage <= stack_voltages[-1]:
                    print(f"  [!] Must be higher than the previous tap ({stack_voltages[-1]:.4f}V).\n")

        stack_voltages.append(voltage)
        print()

    # Derive individual cell voltages by subtraction (for summary display)
    cell_voltages = [stack_voltages[0]]
    for i in range(1, NUM_CELLS):
        cell_voltages.append(round(stack_voltages[i] - stack_voltages[i - 1], 4))

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

    return cell_voltages, stack_voltages, new_multipliers


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


def print_summary(cell_voltages, stack_voltages, new_multipliers,
                   measured_shunt, correction_factor):
    """Print a summary of all calibration values."""
    print_section("Calibration Complete")

    print("  Stack Voltages (measured from Pack -):")
    for i, v in enumerate(stack_voltages, start=1):
        print(f"    Tap {i}:   {v:.4f} V")
    print()

    print("  Individual Cell Voltages (derived by subtraction):")
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
    cell_voltages, stack_voltages, new_multipliers = calibrate_cells(taps)

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
        print_summary(cell_voltages, stack_voltages, new_multipliers,
                       measured_shunt, correction_factor)
    else:
        print("  [!] Failed to update telemetry.py. Please edit manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()

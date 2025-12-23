#!/usr/bin/env python3
"""
runtime_minimal.py - Paper Parity Sanity Check Example

A minimal example that runs without hardware, using the existing Spaxiom runtime.
This verifies the paper parity harness is wired correctly.

This example:
1. Creates a RandomSensor
2. Defines a simple condition
3. Registers a callback with @on
4. Runs briefly to show the system works

This is NOT a paper parity example - it uses the current implementation.
It exists to prove the examples/paper/ folder is importable and runnable.
"""

import sys
import time
import asyncio

# Import from spaxiom
from spaxiom import RandomSensor, Condition, on, SensorRegistry


def main():
    print("=" * 60)
    print("runtime_minimal.py - Sanity Check")
    print("=" * 60)
    print()
    print("This example verifies the paper parity harness is wired correctly.")
    print("It uses EXISTING functionality, not paper-specified features.")
    print()

    # Clear registry for clean state
    SensorRegistry().clear()

    # Create a simple random sensor
    sensor = RandomSensor(
        name="test_sensor",
        location=(0, 0, 0),
        hz=10.0,
    )
    print(f"Created sensor: {sensor}")

    # Create a simple condition
    high_value = Condition(lambda: sensor.read() > 0.7)
    print(f"Created condition: {high_value}")

    # Track if callback was triggered
    callback_count = [0]

    @on(high_value)
    def on_high_value():
        callback_count[0] += 1
        print(f"  -> Callback triggered! (count: {callback_count[0]})")

    print(f"Registered callback: on_high_value")
    print()

    # Read sensor a few times to show it works
    print("Reading sensor 10 times:")
    for i in range(10):
        value = sensor.read()
        is_high = high_value()
        print(f"  Read {i+1}: value={value:.3f}, condition={is_high}")
        time.sleep(0.1)

    print()
    print("SUCCESS: Sanity check passed!")
    print(f"  - Sensor created and readable")
    print(f"  - Condition created and evaluable")
    print(f"  - Callback registered (would fire in runtime loop)")
    print()
    print("The paper parity harness is correctly wired.")

    # Clean up
    SensorRegistry().clear()

    return 0


if __name__ == "__main__":
    sys.exit(main())

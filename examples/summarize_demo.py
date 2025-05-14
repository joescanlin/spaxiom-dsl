#!/usr/bin/env python3
"""
Sensor Summarization Demo using Spaxiom DSL.

This demonstrates:
1. Creating a RollingSummary to monitor the last N readings from a sensor
2. Getting statistical information and trend indicators
3. Using the to_text() method to get a human-readable summary
"""

import os
import sys
import time
import random

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import RollingSummary
from spaxiom.sensor import RandomSensor


def simulate_temperature_sensor():
    """Simulate a temperature sensor with some random variation."""
    base_temp = 22.0  # Base temperature in Celsius
    return base_temp + (random.random() * 2 - 1)  # +/- 1 degree


def simulate_rising_temp():
    """Simulate a rising temperature pattern."""
    base_temp = 22.0
    for i in range(10):
        yield base_temp + (i * 0.5) + (random.random() * 0.2 - 0.1)


def simulate_falling_temp():
    """Simulate a falling temperature pattern."""
    base_temp = 27.0
    for i in range(10):
        yield base_temp - (i * 0.5) + (random.random() * 0.2 - 0.1)


def main():
    """Run the summarization demo."""
    print("\nSpaxiom RollingSummary Demo")
    print("==========================")
    print(
        "This demo shows how to monitor and summarize sensor readings in real-time.\n"
    )

    # Create a temperature sensor
    temp_sensor = RandomSensor(name="temp_sensor", location=(0, 0, 0))

    # Create a rolling summary with a window of 5 readings
    temp_summary = RollingSummary(window=5)

    # Demo 1: Showing random fluctuations
    print("Part 1: Random temperature variations")
    print("------------------------------------")
    for i in range(10):
        # Override random sensor with our simulated temperature
        temp_value = simulate_temperature_sensor()

        # Add to the summary
        temp_summary.add(temp_value)

        # Print the reading and current summary
        print(f"Reading #{i+1}: {temp_value:.2f}°C - Summary: {temp_summary.to_text()}")
        time.sleep(0.5)

    # Demo 2: Showing rising trend
    print("\nPart 2: Rising temperature trend")
    print("------------------------------")
    temp_summary.clear()

    for i, temp_value in enumerate(simulate_rising_temp()):
        # Add to the summary
        temp_summary.add(temp_value)

        # Print the reading and current summary
        print(f"Reading #{i+1}: {temp_value:.2f}°C - Summary: {temp_summary.to_text()}")
        time.sleep(0.5)

    # Demo 3: Showing falling trend
    print("\nPart 3: Falling temperature trend")
    print("--------------------------------")
    temp_summary.clear()

    for i, temp_value in enumerate(simulate_falling_temp()):
        # Add to the summary
        temp_summary.add(temp_value)

        # Print the reading and current summary
        print(f"Reading #{i+1}: {temp_value:.2f}°C - Summary: {temp_summary.to_text()}")
        time.sleep(0.5)

    # Demo 4: Monitoring a random sensor directly
    print("\nPart 4: Using with a live sensor")
    print("------------------------------")
    temp_summary.clear()

    for i in range(8):
        # Get a reading from the sensor
        value = temp_sensor.read()

        # Add to the summary
        temp_summary.add(value)

        # Print the reading and current summary
        print(f"Sensor reading #{i+1}: {value:.2f} - Summary: {temp_summary.to_text()}")
        time.sleep(0.5)

    print("\nDemo completed!")


if __name__ == "__main__":
    main()

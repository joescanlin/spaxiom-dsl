#!/usr/bin/env python3
"""
Sensor Summarization Demo for Spaxiom DSL.

This example demonstrates:
1. Creating a RandomSensor for temperature data
2. Using the summary() method to track statistics over time
3. Printing summary statistics every minute with a window of 60 readings
"""

import os
import sys
import time
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Condition, RandomSensor


def main():
    """Run the sensor summarization demo."""
    print("\nSpaxiom Sensor Summarization Demo")
    print("=================================")
    print("This demo shows how to:")
    print("1. Use RandomSensor for temperature readings")
    print("2. Track statistics with the summary() method")
    print("3. Print summaries every minute with a window of 60 readings\n")

    # Create a random temperature sensor
    # Location parameters are (x, y, z) coordinates
    temp_sensor = RandomSensor(name="temp_sensor", location=(5, 5, 1))

    # Create a condition that returns the temperature value
    # Scale the random value (0-1) to a realistic temperature range (20-30°C)
    def get_temperature():
        random_value = temp_sensor.read()
        return 20.0 + (random_value * 10.0)  # Scale to 20-30°C range

    temp_condition = Condition(get_temperature)

    # Create a summarizer with a window of 60 readings
    temp_summary = temp_condition.summary(window=60)

    print("Starting temperature monitoring...")
    print("Summary will be printed every minute (or every 60 readings)")
    print("Press Ctrl+C to exit\n")

    # Start the simulation loop
    try:
        reading_count = 0
        start_time = time.time()

        while True:
            # Get current time
            current_time = datetime.now().strftime("%H:%M:%S")

            # Read temperature
            reading = get_temperature()

            # Add to the summary
            temp_summary.add(reading)
            reading_count += 1

            # Print current reading
            print(
                f"[{current_time}] Reading #{reading_count}: {reading:.2f}°C", end="\r"
            )

            # Print summary every 60 readings (simulating every minute)
            if reading_count % 60 == 0:
                summary_text = temp_summary.to_text()
                elapsed_minutes = int((time.time() - start_time) / 60)
                print(
                    f"\n[Minute {elapsed_minutes}] Temperature summary: {summary_text}"
                )

            # Wait a bit (adjust this to control how fast readings are collected)
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")

    # Print final statistics
    print("\nFinal Statistics:")
    print("================")
    print(f"Total readings: {reading_count}")
    print(f"Temperature summary: {temp_summary.to_text()}")
    print(f"Average: {temp_summary.get_average():.2f}°C")
    print(f"Max: {temp_summary.get_max():.2f}°C")
    print(f"Min: {temp_summary.get_min():.2f}°C")
    print(f"Trend: {temp_summary.get_trend() or 'insufficient data'}")


if __name__ == "__main__":
    main()

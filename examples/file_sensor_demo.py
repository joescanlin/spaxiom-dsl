#!/usr/bin/env python3
"""
File Sensor Demo for Spaxiom DSL.

This demonstrates:
1. Creating a FileSensor that reads data from a CSV file
2. Reading values one at a time, simulating a real-time stream
3. Using the FileSensor with conditions and event handlers
"""

import os
import sys
import csv
import time
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import FileSensor, Condition, on, within


def create_sample_csv():
    """Create a sample CSV file for demonstration."""
    # Create a temporary file
    fd, filepath = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    # Write sample data to the file
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temperature", "humidity"])
        writer.writerow(["2023-01-01 00:00:00", "19.5", "40.0"])
        writer.writerow(["2023-01-01 00:01:00", "20.0", "41.0"])
        writer.writerow(["2023-01-01 00:02:00", "21.0", "42.0"])
        writer.writerow(["2023-01-01 00:03:00", "22.5", "43.0"])
        writer.writerow(["2023-01-01 00:04:00", "24.0", "44.0"])
        writer.writerow(["2023-01-01 00:05:00", "25.5", "45.0"])
        writer.writerow(["2023-01-01 00:06:00", "26.0", "46.0"])
        writer.writerow(["2023-01-01 00:07:00", "25.0", "47.0"])
        writer.writerow(["2023-01-01 00:08:00", "23.5", "46.5"])
        writer.writerow(["2023-01-01 00:09:00", "22.0", "46.0"])

    return filepath


def main():
    """Run the file sensor demo."""
    # Create a sample CSV file
    csv_path = create_sample_csv()

    try:
        print("\nSpaxiom File Sensor Demo")
        print("-----------------------")
        print(f"Reading from: {csv_path}")
        print()

        # Create temperature and humidity sensors
        temp_sensor = FileSensor(
            name="temperature",
            file_path=csv_path,
            column_name="temperature",
            unit="degC",  # Specify the unit for temperature
            location=(0, 0, 0),
        )

        humidity_sensor = FileSensor(
            name="humidity",
            file_path=csv_path,
            column_name="humidity",
            unit="%",  # Specify the unit for humidity
            location=(0, 0, 0),
        )

        # Define conditions that handle None values
        high_temp = Condition(
            lambda: (temp_raw := temp_sensor.read(unit="degC")) is not None
            and temp_raw.magnitude > 24.0
        )

        high_humidity = Condition(
            lambda: (humidity_raw := humidity_sensor.read(unit="%")) is not None
            and humidity_raw.magnitude > 45.0
        )

        # Create a combined condition
        uncomfortable = high_temp & high_humidity

        # Create a sustained condition (must be true for at least 2 iterations)
        sustained_uncomfortable = within(2, uncomfortable)

        # Register event handlers
        @on(high_temp)
        def alert_high_temp():
            print("\033[1;33m⚠️  High temperature detected!\033[0m")

        @on(high_humidity)
        def alert_high_humidity():
            print("\033[1;34m💧 High humidity detected!\033[0m")

        @on(sustained_uncomfortable)
        def alert_uncomfortable():
            print("\033[1;31m🔥 Uncomfortable conditions sustained!\033[0m")

        # Reset sensors to ensure they're synchronized
        temp_sensor.reset()
        humidity_sensor.reset()

        # Process data row by row
        print("Reading data from CSV:")
        print("----------------------")
        print()

        from spaxiom.events import process_events

        row = 0
        while True:
            # Read temperature and humidity with units
            temp_value = temp_sensor.read(unit="degC")

            # If we've reached the end of the file, break
            if temp_value is None:
                break

            # Manually read humidity (just for display - the conditions read their own values)
            humidity_value = humidity_sensor.read(unit="%")

            # Print current values
            print(
                f"Row {row+1}: Temperature: {temp_value:.1f}, Humidity: {humidity_value:.1f}"
            )

            # Process events
            process_events()

            # Increment row counter
            row += 1

            # Pause for readability
            time.sleep(0.5)

        print("\nEnd of data reached")

    finally:
        # Clean up the temporary file
        os.unlink(csv_path)


if __name__ == "__main__":
    main()

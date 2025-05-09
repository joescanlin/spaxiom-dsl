#!/usr/bin/env python3
"""
File Feed Demo for Spaxiom DSL.

This demonstrates:
1. Using FileSensor to read temperature data from a CSV file
2. Processing each reading and printing the values
"""

import os
import sys
import csv
import time
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import FileSensor


def create_temperature_csv():
    """Create a sample temperature CSV file for demonstration."""
    # Create a temporary file
    fd, filepath = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    # Write sample temperature data to the file
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temp_c", "humidity"])
        writer.writerow(["2023-06-01 08:00:00", "18.5", "55.0"])
        writer.writerow(["2023-06-01 08:15:00", "19.2", "56.0"])
        writer.writerow(["2023-06-01 08:30:00", "20.1", "57.0"])
        writer.writerow(["2023-06-01 08:45:00", "21.0", "58.0"])
        writer.writerow(["2023-06-01 09:00:00", "22.3", "59.0"])
        writer.writerow(["2023-06-01 09:15:00", "23.5", "60.0"])
        writer.writerow(["2023-06-01 09:30:00", "24.8", "62.0"])
        writer.writerow(["2023-06-01 09:45:00", "26.0", "64.0"])
        writer.writerow(["2023-06-01 10:00:00", "27.2", "63.0"])
        writer.writerow(["2023-06-01 10:15:00", "28.5", "61.0"])
        writer.writerow(["2023-06-01 10:30:00", "29.7", "60.0"])
        writer.writerow(["2023-06-01 10:45:00", "30.0", "59.0"])

    return filepath


def main():
    """Run the file feed demo that reads temperature data."""
    # Create a sample temperature CSV file
    csv_path = create_temperature_csv()
    print(f"Created temperature CSV file at: {csv_path}")

    try:
        print("\nSpaxiom Temperature Feed Demo")
        print("----------------------------")
        print(f"Reading temperature data from: {csv_path}")
        print()

        # Create a temperature sensor that reads from the CSV file
        temp_sensor = FileSensor(
            name="temperature_sensor",
            file_path=csv_path,
            column_name="temp_c",  # Specified column name
            unit="degC",           # Specify unit for temperature
            location=(0, 0, 0),    # Default location
        )

        # Reset sensor to ensure we start from the beginning
        temp_sensor.reset()

        # Process temperature data row by row
        print("Temperature readings from CSV:")
        print("-----------------------------")
        
        reading_num = 1
        while True:
            # Read temperature with unit
            temp_value = temp_sensor.read(unit="degC")

            # If we've reached the end of the file, break
            if temp_value is None:
                break

            # Print current temperature reading
            print(f"Reading #{reading_num}: Temperature: {temp_value:.1f}")

            # Increment reading counter
            reading_num += 1

            # Pause for readability
            time.sleep(0.5)

        print("\nEnd of temperature data reached")

    finally:
        # Clean up the temporary file
        os.unlink(csv_path)
        print(f"Removed temporary CSV file: {csv_path}")


if __name__ == "__main__":
    main() 
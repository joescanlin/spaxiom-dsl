#!/usr/bin/env python3
"""
Units Demo for Spaxiom DSL.

This demonstrates:
1. Creating sensors that return values with units
2. Using the Quantity helper to create quantities with units
3. Performing calculations that automatically handle unit conversions
"""

import os
import sys
import time

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Sensor, Quantity


class TemperatureSensor(Sensor):
    """
    A sensor that simulates temperature readings.
    """

    def __init__(self, name, location, base_temp=20.0, variation=5.0):
        """
        Initialize the temperature sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            base_temp: Base temperature in Celsius
            variation: Maximum random variation in temperature
        """
        super().__init__(name=name, sensor_type="temperature", location=location)
        self.base_temp = base_temp
        self.variation = variation

    def _read_raw(self):
        """
        Generate a simulated temperature reading.

        Returns:
            Temperature in Celsius
        """
        # Generate a random temperature around the base temperature
        import random

        temp = self.base_temp + (random.random() * 2 - 1) * self.variation
        return temp


class DistanceSensor(Sensor):
    """
    A sensor that simulates distance readings.
    """

    def __init__(self, name, location, max_distance=100.0):
        """
        Initialize the distance sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            max_distance: Maximum distance in meters
        """
        super().__init__(name=name, sensor_type="distance", location=location)
        self.max_distance = max_distance

    def _read_raw(self):
        """
        Generate a simulated distance reading.

        Returns:
            Distance in meters
        """
        # Generate a random distance
        import random

        distance = random.random() * self.max_distance
        return distance


def main():
    """Run the units demo."""
    # Create sensors
    temp_sensor = TemperatureSensor(
        name="temp1",
        location=(0, 0, 0),
        base_temp=25.0,  # 25°C base temperature
        variation=3.0,  # ±3°C variation
    )

    distance_sensor = DistanceSensor(
        name="dist1", location=(1, 0, 0), max_distance=50.0  # 50m maximum
    )

    # Print header
    print("Spaxiom Units Demo")
    print("-----------------")
    print("This demo demonstrates using physical quantities with units.")
    print(
        "It shows conversion between different unit systems and physical calculations."
    )
    print()

    # Take some readings
    for i in range(5):
        # Read sensors with specific units
        temp_c = temp_sensor.read(unit="degC")
        temp_f = temp_sensor.read(unit="degF")

        dist_m = distance_sensor.read(unit="m")
        dist_feet = distance_sensor.read(unit="ft")

        # Print readings
        print(f"Reading {i+1}:")
        print(f"  Temperature: {temp_c:.2f} = {temp_f:.2f}")
        print(f"  Distance: {dist_m:.2f} = {dist_feet:.2f}")

        # Create some additional quantities
        speed = Quantity(5, "m/s")
        time_to_target = dist_m / speed

        # Print calculation results
        print(f"  Time to reach target at {speed}: {time_to_target:.2f}")

        # Convert to different units
        time_minutes = time_to_target.to("minutes")
        print(f"  Time in minutes: {time_minutes:.2f}")

        # Demonstrate compatible units
        area = Quantity(10, "m²")
        volume = area * dist_m
        print(f"  Volume for area of {area} with height {dist_m}: {volume:.2f}")

        # Temperature differences (delta)
        temp_diff = Quantity(5, "delta_degC")
        new_temp = temp_c + temp_diff
        print(f"  Temperature + 5°C: {new_temp:.2f}")

        print()
        time.sleep(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fusion Mixin Demo script for Spaxiom DSL.

This demonstrates:
1. Using the fuse_with method to combine sensors
2. Different fusion strategies (average and weighted)
3. Custom naming and location configuration
"""

import time
import numpy as np
from spaxiom.sensor import Sensor


class ConstantSensor(Sensor):
    """A sensor that returns a constant value with optional noise."""

    def __init__(self, name, value, location, noise_stddev=0.0):
        """
        Initialize a constant sensor with optional noise.

        Args:
            name: Unique name for the sensor
            value: The constant value to return
            location: (x, y, z) coordinates
            noise_stddev: Standard deviation of Gaussian noise to add (default: 0.0)
        """
        super().__init__(
            name=name,
            sensor_type="constant",
            location=location,
            metadata={"base_value": value, "noise_level": noise_stddev},
        )
        self.value = value
        self.noise_stddev = noise_stddev

    def _read_raw(self):
        """
        Read the constant value with optional noise.

        Returns:
            The constant value plus optional noise
        """
        if self.noise_stddev > 0:
            return self.value + np.random.normal(0, self.noise_stddev)
        return self.value

    def __repr__(self):
        noise_info = f", noise={self.noise_stddev}" if self.noise_stddev > 0 else ""
        return f"ConstantSensor(name='{self.name}', value={self.value}{noise_info})"


def print_readings(sensors, fusion=None, rounds=1):
    """Print readings from sensors and optional fusion."""
    for _ in range(rounds):
        readings = [s.read() for s in sensors]

        line = " | ".join([f"{s.name}: {v:.2f}" for s, v in zip(sensors, readings)])

        if fusion:
            fusion_value = fusion.read()
            line += f" | {fusion.name}: {fusion_value:.2f}"

        print(line)

        if rounds > 1:
            time.sleep(0.5)


def main():
    print("Spaxiom Sensor Fusion Mixin Demo")
    print("--------------------------------")

    # Create two constant sensors with different values
    s1 = ConstantSensor(
        "temperature1", value=22.5, location=(0, 0, 0), noise_stddev=0.5
    )
    s2 = ConstantSensor(
        "temperature2", value=24.5, location=(10, 0, 0), noise_stddev=1.0
    )

    print("\n1. Simple averaging fusion:")
    print("--------------------------")
    print(f"Sensor 1: {s1}")
    print(f"Sensor 2: {s2}")

    # Create fusion with average strategy
    avg_fusion = s1.fuse_with(s2, strategy="average", name="temp_avg")

    print(f"Fusion: {avg_fusion}")
    print("\nReadings:")
    print_readings([s1, s2], avg_fusion, rounds=3)

    print("\n2. Weighted fusion (favoring more reliable sensor):")
    print("------------------------------------------------")

    # Create fusion with weighted strategy - s1 has lower noise so give it higher weight
    weighted_fusion = s1.fuse_with(
        s2,
        strategy="weighted",
        weights=[0.8, 0.2],  # Higher weight to s1 (more reliable)
        name="temp_weighted",
    )

    print(f"Fusion with weights {weighted_fusion.weights}: {weighted_fusion}")
    print("\nReadings:")
    print_readings([s1, s2], weighted_fusion, rounds=3)

    print("\n3. Fusion with custom location:")
    print("-----------------------------")

    # Create fusion with custom location
    custom_location = (5, 5, 5)
    custom_fusion = s1.fuse_with(
        s2, strategy="average", name="temp_custom_loc", location=custom_location
    )

    print(f"Fusion: {custom_fusion}")
    print(f"Location: {custom_fusion.location}")
    print("\nReadings:")
    print_readings([s1, s2], custom_fusion, rounds=1)

    print("\n4. Chaining fusions:")
    print("------------------")

    # Create a third sensor
    s3 = ConstantSensor(
        "temperature3", value=23.0, location=(0, 10, 0), noise_stddev=0.3
    )
    print(f"Sensor 3: {s3}")

    # Fuse s1 and s2, then fuse the result with s3
    intermediate_fusion = s1.fuse_with(s2, strategy="average", name="temp_12")
    final_fusion = intermediate_fusion.fuse_with(
        s3, strategy="weighted", weights=[0.5, 0.5], name="temp_all"
    )

    print(f"Final fusion: {final_fusion}")
    print("\nReadings:")
    print_readings([s1, s2, s3], final_fusion, rounds=3)


if __name__ == "__main__":
    main()

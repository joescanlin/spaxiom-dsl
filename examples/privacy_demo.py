#!/usr/bin/env python3
"""
Privacy Demo for Spaxiom DSL.

This example demonstrates:
1. Creating sensors with different privacy levels
2. Using the SensorRegistry to list public and private sensors
3. Creating fusion sensors that inherit privacy from component sensors
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import SensorRegistry, RandomSensor


def main():
    """Run the privacy demo."""
    print("\nSpaxiom Sensor Privacy Demo")
    print("==========================")
    print("This demo shows how to:")
    print("1. Create sensors with different privacy levels")
    print("2. Use SensorRegistry to list sensors by privacy level")
    print("3. Create fusion sensors that inherit privacy settings\n")

    # Clear the registry to start fresh
    SensorRegistry().clear()

    # Create sensors with different privacy levels
    print("Creating sensors...")

    # Public sensors (default)
    temp_public = RandomSensor(
        name="temp_living_room",
        location=(0, 0, 0),
        # privacy="public" is default
    )

    humidity_public = RandomSensor(
        name="humidity_living_room",
        location=(0, 0, 0),
        privacy="public",  # explicit
    )

    # Private sensors
    temp_private = RandomSensor(
        name="temp_bedroom",
        location=(5, 0, 0),
        privacy="private",
    )

    motion_private = RandomSensor(
        name="motion_bedroom",
        location=(5, 0, 0),
        privacy="private",
    )

    # Create some fusion sensors
    print("\nCreating fusion sensors...")

    # Public + Public = Public
    public_fusion = temp_public.fuse_with(
        humidity_public,
        strategy="weighted",
        name="climate_living_room",
        weights=[0.6, 0.4],
    )

    # Public + Private = Private (automatically elevated)
    mixed_fusion = temp_public.fuse_with(
        temp_private,
        strategy="average",
        name="avg_temperature",
    )

    # Private + Private = Private
    private_fusion = temp_private.fuse_with(
        motion_private,
        strategy="weighted",
        name="bedroom_activity",
        weights=[0.3, 0.7],
    )

    # Access the registry
    registry = SensorRegistry()

    # Get all sensors
    all_sensors = registry.list_all()
    public_sensors = registry.list_public()
    private_sensors = registry.list_private()

    # Print results
    print(f"\nTotal sensors: {len(all_sensors)}")
    print(f"Public sensors: {len(public_sensors)}")
    print(f"Private sensors: {len(private_sensors)}")

    print("\nPublic sensors:")
    for name, sensor in public_sensors.items():
        print(f"  - {sensor}")

    print("\nPrivate sensors:")
    for name, sensor in private_sensors.items():
        print(f"  - {sensor}")

    # Demonstrate that mixed fusion was automatically set to private
    print("\nPrivacy inheritance:")
    print(f"  Public + Public = {public_fusion.privacy}")
    print(f"  Public + Private = {mixed_fusion.privacy}")
    print(f"  Private + Private = {private_fusion.privacy}")


if __name__ == "__main__":
    main()

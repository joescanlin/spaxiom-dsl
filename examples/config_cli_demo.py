#!/usr/bin/env python3
"""
Demo script for Spaxiom CLI configuration loading.

This script demonstrates how to use sensors loaded from a YAML configuration file
through the CLI's --config option.

Run this script with:
    spax-run examples/config_cli_demo.py --config examples/sensors_config.yaml
"""

import logging
from spaxiom import Condition, on, within, SensorRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Spaxiom configuration CLI demo."""
    # Get the registry and retrieve sensors loaded from the configuration file
    registry = SensorRegistry()

    print("\nSpaxiom CLI Configuration Demo")
    print("===============================")

    # List all sensors that have been loaded
    all_sensors = registry.list_all()
    print(f"\nLoaded {len(all_sensors)} sensors from configuration:")
    for name, sensor in all_sensors.items():
        print(f"  - {sensor}")

    # Try to access specific sensors by name
    try:
        temp_sensor = registry.get("temperature_sensor")
        print(f"\nFound temperature sensor: {temp_sensor}")

        # Create a condition based on the temperature sensor
        temp_high = Condition(lambda: temp_sensor.read() > 0.7)

        # Create a temporal condition
        sustained_high = within(2.0, temp_high)

        # Register event handlers
        @on(temp_high)
        def on_high_temp():
            value = temp_sensor.read()
            print(f"HIGH TEMPERATURE DETECTED: {value:.2f}")

        @on(sustained_high)
        def on_sustained_high_temp():
            value = temp_sensor.read()
            print(f"SUSTAINED HIGH TEMPERATURE: {value:.2f} for at least 2 seconds")

    except KeyError:
        print("\nWarning: temperature_sensor not found in registry")

    try:
        motion_sensor = registry.get("motion_sensor")
        print(f"Found motion sensor: {motion_sensor}")

        # Create a condition for motion detection
        motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

        @on(motion_detected)
        def on_motion():
            print("MOTION DETECTED!")

    except KeyError:
        print("\nWarning: motion_sensor not found in registry")

    print("\nRunning with sensors from configuration...")
    print("Press Ctrl+C to exit\n")

    # The runtime will be started by the CLI
    # No need to call start_blocking() here


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Demo script for Spaxiom configuration loading.

This demonstrates:
1. Creating a YAML configuration file
2. Loading the configuration with load_yaml
3. Creating sensors from the configuration with create_sensor_from_cfg
4. Using load_sensors_from_yaml to do both steps at once
"""

import os
from spaxiom import (
    Condition,
    on,
    within,
    load_yaml,
    create_sensor_from_cfg,
    load_sensors_from_yaml,
)
from spaxiom.runtime import start_blocking

# Example configuration (would normally be in a YAML file)
EXAMPLE_CONFIG = """
sensors:
  - name: random_sensor1
    type: random
    location: [1.0, 2.0, 0.0]
    hz: 5.0
    privacy: public
    
  - name: toggle_sensor1
    type: toggle
    location: [3.0, 4.0, 0.0]
    toggle_interval: 3.0
    high_value: 10.0
    low_value: 0.0
    hz: 10.0
    
  # This will only work on Linux systems with gpiozero
  - name: gpio_sensor1
    type: gpio_digital
    pin: 17
    location: [0.0, 0.0, 0.0]
    pull_up: true
"""


def create_config_file():
    """Create a temporary YAML configuration file."""
    config_path = "example_config.yaml"
    with open(config_path, "w") as f:
        f.write(EXAMPLE_CONFIG)
    return config_path


def cleanup_config_file(path):
    """Remove the temporary YAML configuration file."""
    if os.path.exists(path):
        os.remove(path)


def main():
    """Run the configuration demo."""
    print("Spaxiom Configuration Demo")
    print("=========================")

    # Create a temporary configuration file
    config_path = create_config_file()
    print(f"Created example configuration file: {config_path}")

    # Method 1: Load config and create sensors manually
    print("\nMethod 1: Load config and create sensors manually")
    config = load_yaml(config_path)
    print(f"Loaded configuration with {len(config['sensors'])} sensor entries")

    # Create the first sensor
    if config["sensors"]:
        first_sensor_config = config["sensors"][0]
        print(f"Creating sensor from first entry: {first_sensor_config['name']}")
        sensor = create_sensor_from_cfg(first_sensor_config)
        print(f"Created sensor: {sensor}")

    # Method 2: Load sensors directly from YAML file
    print("\nMethod 2: Load sensors directly from YAML file")
    sensors = load_sensors_from_yaml(config_path)
    print(f"Loaded {len(sensors)} sensors from configuration file:")
    for sensor in sensors:
        print(f"  - {sensor}")

    # Setup a condition and callback for the first sensor (if loaded)
    if sensors:
        first_sensor = sensors[0]
        print(f"\nSetting up condition for sensor: {first_sensor.name}")

        # Define a condition that is true when the sensor value is > 0.7
        high_value = Condition(lambda: first_sensor.read() > 0.7)

        # Define a temporal condition that is true when the sensor value is high for 2 seconds
        sustained_high = within(2.0, high_value)

        # Register callbacks
        @on(high_value)
        def on_high_value():
            print(f"HIGH VALUE - {first_sensor.name} exceeded threshold!")

        @on(sustained_high)
        def on_sustained_high():
            print(
                f"SUSTAINED HIGH - {first_sensor.name} exceeded threshold for 2+ seconds!"
            )

        # Run for a short time to demonstrate
        print("\nRunning sensors for 10 seconds...")
        try:
            # Start in blocking mode with a 20ms polling interval
            start_blocking(poll_ms=20)
        except KeyboardInterrupt:
            print("\nStopped.")

    # Cleanup
    cleanup_config_file(config_path)
    print("\nDemo completed. Configuration file removed.")


if __name__ == "__main__":
    main()

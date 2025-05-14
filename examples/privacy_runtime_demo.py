#!/usr/bin/env python3
"""
Privacy Runtime Demo for Spaxiom DSL.

This example demonstrates:
1. Setting up sensors with different privacy levels
2. Showing how the runtime handles private sensors
3. Demonstrating how private sensor values are redacted in logs
"""

import os
import sys
import logging
import time

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import RandomSensor, SensorRegistry, Condition, on
from spaxiom.runtime import format_sensor_value

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PrivacyRuntime")


def main():
    """Run the privacy runtime demo."""
    print("\nSpaxiom Privacy Runtime Demo")
    print("===========================")
    print("This demo shows how sensor privacy affects the runtime:")
    print("1. Public sensors show their actual values")
    print("2. Private sensors have their values redacted (***)")
    print("3. Runtime logs warn about private sensors once per run\n")

    # Clear the registry to start fresh
    SensorRegistry().clear()

    # Create two sensors - one public, one private
    print("Creating sensors...")
    public_sensor = RandomSensor(
        name="living_room_temp",
        location=(0, 0, 0),
        # privacy="public" is default
    )

    private_sensor = RandomSensor(
        name="bedroom_motion",
        location=(5, 0, 0),
        privacy="private",  # mark as private
    )

    # Create conditions to monitor the sensors
    public_high = Condition(lambda: public_sensor.read() > 0.7)
    private_high = Condition(lambda: private_sensor.read() > 0.7)

    # Register callbacks
    @on(public_high)
    def alert_public_high():
        value = public_sensor.read()
        formatted = format_sensor_value(public_sensor, value)
        logger.info(f"Public sensor reading: {formatted}")

    @on(private_high)
    def alert_private_high():
        value = private_sensor.read()
        formatted = format_sensor_value(private_sensor, value)
        logger.info(f"Private sensor reading: {formatted}")

    # Manually read and log
    print("\nDirectly reading sensors:")
    for _ in range(3):
        # Read public sensor
        public_value = public_sensor.read()
        print(f"Public sensor raw value: {public_value}")
        print(
            f"Public sensor formatted value: {format_sensor_value(public_sensor, public_value)}"
        )

        # Read private sensor
        private_value = private_sensor.read()
        print(
            f"Private sensor raw value: {private_value}"
        )  # We can access the value directly
        print(
            f"Private sensor formatted value: {format_sensor_value(private_sensor, private_value)}"
        )

        print("---")
        time.sleep(1)

    print(
        "\nNote that we only see the warning once per sensor, even with multiple reads."
    )

    print("\nNow starting the runtime loop for event processing...")
    print("Press Ctrl+C after a few seconds to exit.\n")

    # Start runtime loop (will process events in the background)
    from spaxiom.runtime import start_blocking

    try:
        # Use a higher polling frequency for demo purposes
        start_blocking(poll_ms=500)
    except KeyboardInterrupt:
        print("\nDemo stopped by user")


if __name__ == "__main__":
    main()

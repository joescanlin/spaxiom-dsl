#!/usr/bin/env python3
"""
Demo script for Spaxiom plugin system.

This script demonstrates how to use a plugin by manually importing it
before starting the Spaxiom runtime. Alternatively, if the plugin is in
the spaxiom_site_plugins namespace, it will be loaded automatically.

Run with:
    spax-run examples/plugin_demo.py
"""

import logging
import importlib
from spaxiom import Condition, on, within, SensorRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Spaxiom plugin demo."""
    print("\nSpaxiom Plugin System Demo")
    print("==========================")

    # Manually import the plugin
    # In a real application, you could place this in the spaxiom_site_plugins namespace
    # and it would be loaded automatically when the runtime starts
    print("\nManually importing custom plugin...")
    try:
        # Import the plugin module to trigger registration
        importlib.import_module("examples.custom_plugin_demo")
    except ImportError:
        print("Error importing custom plugin, please make sure it exists.")
        return

    # Get the registry to access the demo sensor created by the plugin
    registry = SensorRegistry()

    try:
        # Get the demo sine sensor that was created by the plugin
        sine_sensor = registry.get("demo_sine_sensor")
        print(f"\nFound sensor from plugin: {sine_sensor}")

        # Create conditions based on the sine wave
        # Since it oscillates between positive and negative values,
        # we can create conditions for when it's positive or negative
        positive_value = Condition(lambda: sine_sensor.read() > 0)
        negative_value = Condition(lambda: sine_sensor.read() < 0)

        # Create temporal conditions
        sustained_positive = within(1.0, positive_value)
        sustained_negative = within(1.0, negative_value)

        # Register event handlers
        @on(sustained_positive)
        def on_positive_phase():
            value = sine_sensor.read()
            print(f"[Event] Positive phase detected: {value:.2f}")

        @on(sustained_negative)
        def on_negative_phase():
            value = sine_sensor.read()
            print(f"[Event] Negative phase detected: {value:.2f}")

        print("\nRegistered event handlers for sine wave phases")
        print("\nRunning with plugin sensor...")
        print("Press Ctrl+C to exit\n")

    except KeyError:
        print("\nWarning: demo_sine_sensor not found in registry.")
        print("This likely means the plugin was not properly loaded or registered.")

    # The runtime will be started by the CLI
    # No need to call start_blocking() here


if __name__ == "__main__":
    main()

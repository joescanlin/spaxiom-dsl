#!/usr/bin/env python3
"""
CO2 monitoring application using the Spaxiom plugin system.

This application demonstrates how to use a custom CO2 sensor plugin
to monitor carbon dioxide levels in different rooms and trigger
alerts when levels exceed thresholds.

Run this script with:
    python co2_monitor.py

or:
    spax-run examples/co2_monitor.py
"""

import logging
import importlib
from spaxiom import Condition, on, within, SensorRegistry
from spaxiom.runtime import start_blocking

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Run the CO2 monitoring application."""
    print("\nCO2 Monitoring with Spaxiom")
    print("===========================")

    # Manually import the plugin
    # (Alternative: place it in the spaxiom_site_plugins package for auto-loading)
    try:
        importlib.import_module("examples.co2_plugin")
    except ImportError:
        print(
            "Error importing CO2 plugin, please make sure it exists at examples/co2_plugin.py"
        )
        return

    # Get the registry to access the CO2 sensors
    registry = SensorRegistry()

    try:
        # Get the CO2 sensors
        living_room_co2 = registry.get("living_room_co2")
        bedroom_co2 = registry.get("bedroom_co2")

        print("\nDetected CO2 sensors:")
        print(f"  - {living_room_co2}")
        print(f"  - {bedroom_co2}")

        # Define CO2 level conditions
        living_room_high = Condition(lambda: living_room_co2.read() > 800)
        bedroom_high = Condition(lambda: bedroom_co2.read() > 800)

        # Define sustained conditions
        sustained_high_living = within(10.0, living_room_high)
        # Also define sustained condition for bedroom (for completeness)
        within(10.0, bedroom_high)  # Not used directly but registered with the system

        # Define a condition for when both rooms have high CO2
        all_rooms_high = living_room_high & bedroom_high

        # Register event handlers
        @on(living_room_high)
        def on_living_room_high():
            value = living_room_co2.read()
            print(f"[Alert] Living room CO2 level high: {value:.0f} ppm")

        @on(bedroom_high)
        def on_bedroom_high():
            value = bedroom_co2.read()
            print(f"[Alert] Bedroom CO2 level high: {value:.0f} ppm")

        @on(all_rooms_high)
        def on_all_rooms_high():
            living = living_room_co2.read()
            bed = bedroom_co2.read()
            print(
                f"[Alert] All rooms have high CO2 levels! Living: {living:.0f} ppm, Bedroom: {bed:.0f} ppm"
            )
            print("        You should open some windows for ventilation!")

        @on(sustained_high_living)
        def on_sustained_living_room_high():
            value = living_room_co2.read()
            print(
                f"[Warning] Living room CO2 has been high ({value:.0f} ppm) for over 10 seconds!"
            )

        # Also use the custom is_high method to define another condition
        very_high_bedroom = Condition(lambda: bedroom_co2.is_high(threshold=1200))

        @on(very_high_bedroom)
        def on_very_high_bedroom():
            value = bedroom_co2.read()
            print(f"[Danger] Bedroom CO2 level very high: {value:.0f} ppm!")
            print("         This exceeds 1200 ppm and may cause drowsiness.")

        print("\nCO2 monitoring active. Press Ctrl+C to exit...\n")

        # Start the Spaxiom runtime - this will automatically poll the sensors
        # and trigger the event handlers when conditions are met
        start_blocking(poll_ms=500)

    except KeyError as e:
        print(f"\nError: Could not find CO2 sensor: {e}")
        print("Make sure the plugin was properly loaded.")


if __name__ == "__main__":
    main()

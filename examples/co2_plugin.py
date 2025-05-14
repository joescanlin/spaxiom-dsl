#!/usr/bin/env python3
"""
Example CO2Sensor plugin for Spaxiom DSL.

This example demonstrates how to create a plugin that extends the Spaxiom DSL
with a custom CO2 sensor type. The plugin is registered using the @register_plugin
decorator and will be automatically loaded and initialized at runtime.
"""

import random
import time
from typing import Optional, Dict, Any, Tuple

from spaxiom import register_plugin, Sensor
from spaxiom.core import SensorRegistry


class CO2Sensor(Sensor):
    """
    A custom CO2 sensor that simulates carbon dioxide readings in parts per million (ppm).

    Features:
    - Baseline CO2 level with random fluctuations
    - Configurable sensor sensitivity and range
    - Simulates real-world CO2 concentration patterns
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        baseline_ppm: float = 400.0,  # Typical outdoor CO2 level
        fluctuation: float = 50.0,  # Amount of random fluctuation
        max_ppm: float = 2000.0,  # Maximum possible reading
        hz: float = 1.0,  # Polling frequency
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the CO2 sensor with the given parameters."""
        # Calculate sample period from frequency
        sample_period = 1.0 / hz if hz > 0 else 0.0

        # Set up metadata if not provided
        if metadata is None:
            metadata = {}
        metadata.update({"unit": "ppm", "type": "carbon_dioxide"})

        super().__init__(
            name=name,
            sensor_type="co2",
            location=location,
            privacy=privacy,
            sample_period_s=sample_period,
            metadata=metadata,
        )

        self.baseline_ppm = baseline_ppm
        self.fluctuation = fluctuation
        self.max_ppm = max_ppm
        self.last_reading_time = time.time()
        self.current_value = baseline_ppm

    def _read_raw(self) -> float:
        """
        Generate a simulated CO2 reading in parts per million (ppm).

        Returns:
            A CO2 concentration value in ppm
        """
        now = time.time()
        time_diff = now - self.last_reading_time
        self.last_reading_time = now

        # Simulate CO2 fluctuations
        drift = random.uniform(-self.fluctuation, self.fluctuation) * time_diff
        self.current_value += drift

        # Ensure values stay within reasonable bounds
        self.current_value = max(300.0, min(self.current_value, self.max_ppm))

        return self.current_value

    def is_high(self, threshold: float = 1000.0) -> bool:
        """
        Check if CO2 levels are above a threshold.

        Args:
            threshold: The CO2 concentration threshold in ppm

        Returns:
            True if current CO2 level exceeds the threshold
        """
        return self.read() > threshold

    def __repr__(self) -> str:
        """Return a string representation of the CO2 sensor."""
        return f"CO2Sensor(name='{self.name}', location={self.location}, baseline={self.baseline_ppm}ppm)"


@register_plugin
def setup_co2_sensors():
    """
    Register the CO2 sensor type with Spaxiom.

    This function is decorated with @register_plugin, which means it will be
    automatically called when the Spaxiom runtime starts.
    """
    print("[Plugin] Registering CO2Sensor plugin")

    # Create a demonstration CO2 sensor
    CO2Sensor(
        name="living_room_co2",
        location=(1.0, 2.0, 0.0),
        baseline_ppm=450.0,  # Slightly elevated indoor level
        hz=2.0,
        metadata={"room": "living_room"},
    )

    # Create another CO2 sensor with different parameters
    CO2Sensor(
        name="bedroom_co2",
        location=(5.0, 3.0, 0.0),
        baseline_ppm=420.0,
        fluctuation=30.0,
        hz=1.0,
        metadata={"room": "bedroom"},
    )

    print("[Plugin] CO2Sensor plugin registered with 2 sensors")


# If this file is run directly, demonstrate the plugin functionality
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    # Manually run the plugin function
    setup_co2_sensors()

    # Check if the sensors were registered
    registry = SensorRegistry()

    # Get the CO2 sensors
    try:
        living_room = registry.get("living_room_co2")
        bedroom = registry.get("bedroom_co2")

        print("\nRegistered CO2 sensors:")
        print(f"  - {living_room}")
        print(f"  - {bedroom}")

        # Read some values
        print("\nReading from sensors:")
        for _ in range(5):
            living_val = living_room.read()
            bed_val = bedroom.read()
            print(f"  Living room: {living_val:.1f} ppm, Bedroom: {bed_val:.1f} ppm")
            time.sleep(0.5)

    except KeyError as e:
        print(f"Error: Could not find CO2 sensor: {e}")

    print("\nTo use this as a plugin, import it in your application or place it in")
    print("the spaxiom_site_plugins namespace for automatic loading.")

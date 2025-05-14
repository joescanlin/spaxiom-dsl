#!/usr/bin/env python3
"""
Example plugin for Spaxiom DSL.

This example demonstrates how to create a plugin that extends the Spaxiom DSL
with a custom sensor type. The plugin is registered using the @register_plugin
decorator and will be automatically loaded and initialized at runtime.

To use this plugin:
1. Create a Python package named 'spaxiom_site_plugins'
2. Place this file (or similar) in that package
3. Install the package where Spaxiom can find it

Alternatively, you can import this file directly in your application before
starting the Spaxiom runtime.
"""

import logging
import random
from typing import Optional, Dict, Any, Tuple

from spaxiom import register_plugin, Sensor
from spaxiom.core import SensorRegistry

logger = logging.getLogger(__name__)


class CustomSensor(Sensor):
    """
    A custom sensor type that demonstrates how to extend Spaxiom with plugins.

    This sensor generates values following a sinusoidal pattern with random noise.
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        amplitude: float = 1.0,
        frequency: float = 0.1,
        phase: float = 0.0,
        noise_level: float = 0.1,
        hz: float = 1.0,
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the custom sensor.

        Args:
            name: Unique identifier for the sensor
            location: (x, y, z) coordinates of the sensor
            amplitude: Amplitude of the sine wave
            frequency: Frequency of the sine wave
            phase: Phase offset of the sine wave
            noise_level: Amount of random noise to add
            hz: Polling frequency in Hz
            privacy: Privacy level ('public' or 'private')
            metadata: Optional metadata dictionary
        """
        # Calculate sample period from frequency
        sample_period = 1.0 / hz if hz > 0 else 0.0

        super().__init__(
            name=name,
            sensor_type="custom_sine",
            location=location,
            privacy=privacy,
            sample_period_s=sample_period,
            metadata=metadata or {},
        )

        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
        self.noise_level = noise_level
        self.time_offset = random.random() * 100  # Random starting point

    def _read_raw(self) -> float:
        """
        Generate a value based on a sine wave with some random noise.

        Returns:
            A sensor value following a sinusoidal pattern with noise
        """
        import time
        import math

        # Get current time with offset to create different patterns for each sensor
        t = time.time() + self.time_offset

        # Generate sine wave value
        base_value = self.amplitude * math.sin(
            2 * math.pi * self.frequency * t + self.phase
        )

        # Add random noise
        noise = random.uniform(-self.noise_level, self.noise_level)

        # Combine signal and noise
        return base_value + noise

    def __repr__(self) -> str:
        """Return a string representation of the custom sensor."""
        return (
            f"CustomSensor(name='{self.name}', "
            f"amplitude={self.amplitude}, frequency={self.frequency}, "
            f"location={self.location})"
        )


@register_plugin
def setup_custom_sensor_type():
    """
    Register the custom sensor type with Spaxiom.

    This function is decorated with @register_plugin, which means it will be
    automatically called when the Spaxiom runtime starts.
    """
    logger.info("Registering CustomSensor type plugin")

    # You could do any setup here needed for your custom components
    # For example, registering factory functions, adding custom validation, etc.

    # Create a demonstration sensor
    CustomSensor(
        name="demo_sine_sensor",
        location=(10.0, 10.0, 0.0),
        amplitude=5.0,
        frequency=0.2,
        hz=10.0,
        metadata={"description": "Sine wave demonstration sensor"},
    )

    logger.info("CustomSensor plugin registered successfully")
    print("[Plugin] CustomSensor type registered and demo_sine_sensor created")


# If this file is run directly, demonstrate the plugin functionality
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Manually run the plugin function
    setup_custom_sensor_type()

    # Check if the sensor was registered
    registry = SensorRegistry()
    sensor = registry.get("demo_sine_sensor")

    # Read some values
    print(f"\nReading from {sensor}:")
    for _ in range(5):
        value = sensor.read()
        print(f"  Value: {value:.4f}")
        import time

        time.sleep(0.2)

    print("\nTo use this as a plugin, run a Spaxiom application with:")
    print("  spax-run your_script.py")
    print(
        "The plugin will be automatically loaded if it's in the spaxiom_site_plugins namespace."
    )

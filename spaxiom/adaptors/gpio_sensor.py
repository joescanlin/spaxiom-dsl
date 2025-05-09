"""
GPIO Sensor module for interfacing with GPIO pins on Linux systems using gpiozero.
"""

import sys
from typing import Optional, Dict, Any, Tuple

from spaxiom.sensor import Sensor


# Check if we're on a Linux system and if gpiozero is available
GPIOZERO_AVAILABLE = False
if sys.platform.startswith("linux"):
    try:
        import gpiozero

        GPIOZERO_AVAILABLE = True
    except ImportError:
        pass


class GPIODigitalSensor(Sensor):
    """
    A sensor that reads from a GPIO pin on Linux systems using gpiozero.

    This sensor connects to a specified BCM pin and provides a boolean read()
    operation that returns True when the pin is HIGH and False when LOW.

    Attributes:
        name: Unique identifier for the sensor
        pin: BCM pin number to read from
        pull_up: Whether to enable pull-up resistor (True) or pull-down (False)
        active_state: The state (True/False) that is considered "active"
    """

    def __init__(
        self,
        name: str,
        pin: int,
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        pull_up: bool = False,
        active_state: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a GPIO digital sensor.

        Args:
            name: Unique name for the sensor
            pin: BCM pin number to connect to
            location: Spatial coordinates (x, y, z) of the sensor
            pull_up: Whether to enable pull-up resistor (True) or pull-down (False)
            active_state: The state (True/False) that is considered "active"
            metadata: Optional metadata dictionary

        Raises:
            ImportError: If not on a Linux system or gpiozero is not installed
            RuntimeError: If unable to initialize the GPIO pin
        """
        if not GPIOZERO_AVAILABLE:
            raise ImportError(
                "GPIODigitalSensor requires gpiozero, which is only available on Linux systems. "
                "Please install gpiozero: pip install gpiozero"
            )

        # First call the parent constructor to register the sensor
        super().__init__(
            name=name, sensor_type="gpio_digital", location=location, metadata=metadata
        )

        self.pin = pin
        self.pull_up = pull_up
        self.active_state = active_state

        # Initialize the GPIO input device
        try:
            self._input_device = gpiozero.DigitalInputDevice(
                pin=pin, pull_up=pull_up, active_state=active_state
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GPIO pin {pin}: {str(e)}")

    def _read_raw(self) -> bool:
        """
        Read the current state of the GPIO pin.

        Returns:
            True if the pin is in the active state, False otherwise
        """
        return self._input_device.value == 1

    def is_active(self) -> bool:
        """
        Check if the GPIO pin is in the active state.

        Returns:
            True if the pin is active, False otherwise
        """
        return self._read_raw()

    def __del__(self):
        """Clean up resources when the object is deleted."""
        if hasattr(self, "_input_device"):
            try:
                self._input_device.close()
            except Exception:
                pass  # Ignore cleanup errors

    def __repr__(self) -> str:
        """Return a string representation of the GPIO sensor."""
        return (
            f"GPIODigitalSensor(name='{self.name}', pin={self.pin}, "
            f"pull_up={self.pull_up}, active_state={self.active_state})"
        )

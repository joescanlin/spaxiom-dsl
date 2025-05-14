"""
Sensor module for Spaxiom DSL.
"""

from typing import Optional, Dict, Any, Tuple
import numpy as np
import time

from spaxiom.core import Sensor


class RandomSensor(Sensor):
    """
    A sensor that returns random values when read.

    Attributes:
        hz: Frequency in Hz at which the sensor should be polled (sets sample_period_s)
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        hz: float = 1.0,
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        # Calculate sample period from frequency
        sample_period = 1.0 / hz if hz > 0 else 0.0

        super().__init__(
            name=name,
            sensor_type="random",
            location=location,
            privacy=privacy,
            sample_period_s=sample_period,
            metadata=metadata,
        )

    def _read_raw(self) -> float:
        """
        Generate a random float value between 0 and 1.

        Returns:
            A random float between 0 and 1.
        """
        return float(np.random.random())

    def __repr__(self):
        return f"RandomSensor(name='{self.name}', location={self.location}, privacy='{self.privacy}')"


class TogglingSensor(Sensor):
    """
    A sensor that toggles between high and low states at regular intervals.

    Attributes:
        toggle_interval: Time in seconds between toggles
        high_value: The "high" value
        low_value: The "low" value
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        toggle_interval: float = 2.0,
        high_value: float = 1.0,
        low_value: float = 0.0,
        hz: float = 10.0,
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the toggling sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            toggle_interval: Time in seconds between toggles
            high_value: The "high" value
            low_value: The "low" value
            hz: Frequency in Hz at which the sensor should be polled
            privacy: Privacy level ('public' or 'private')
            metadata: Optional metadata dictionary
        """
        # Calculate sample period from frequency - should be faster than toggle interval
        # to properly capture the transitions
        sample_period = 1.0 / hz if hz > 0 else 0.0

        super().__init__(
            name=name,
            sensor_type="toggle",
            location=location,
            privacy=privacy,
            sample_period_s=sample_period,
            metadata=metadata,
        )
        self.toggle_interval = toggle_interval
        self.high_value = high_value
        self.low_value = low_value
        self.last_toggle = time.time()
        self.current_state = False
        self.current_value = low_value

    def _read_raw(self) -> float:
        """
        Read the current value, toggling if enough time has passed.

        Returns:
            The current sensor value (high or low)
        """
        now = time.time()
        if now - self.last_toggle >= self.toggle_interval:
            self.current_state = not self.current_state
            self.current_value = (
                self.high_value if self.current_state else self.low_value
            )
            self.last_toggle = now
            # Print toggle event
            state_name = "HIGH" if self.current_state else "LOW"
            print(f"Sensor toggled to {state_name} ({self.current_value})")

        return self.current_value

    def __repr__(self):
        return f"TogglingSensor(name='{self.name}', location={self.location}, privacy='{self.privacy}')"

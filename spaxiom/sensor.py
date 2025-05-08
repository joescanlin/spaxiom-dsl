"""
Sensor module for Spaxiom DSL.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import numpy as np
import time


@dataclass
class Sensor:
    """
    A sensor in the spatial system.

    Attributes:
        name: Unique identifier for the sensor
        sensor_type: Type of sensor (e.g., "lidar", "camera", "radar")
        location: Spatial coordinates (x, y, z) of the sensor
    """

    name: str
    sensor_type: str
    location: Tuple[float, float, float]
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Register sensor automatically
        from spaxiom.registry import SensorRegistry

        SensorRegistry().add(self)

    def read(self):
        """
        Read data from the sensor.

        Returns:
            Sensor data in an appropriate format for the sensor type.
        """
        raise NotImplementedError("Sensor subclasses must implement read()")

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.sensor_type}', location={self.location})"


class RandomSensor(Sensor):
    """
    A sensor that returns random values when read.
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name, sensor_type="random", location=location, metadata=metadata
        )

    def read(self) -> float:
        """
        Generate a random float value between 0 and 1.

        Returns:
            A random float between 0 and 1.
        """
        return float(np.random.random())

    def __repr__(self):
        return f"RandomSensor(name='{self.name}', location={self.location})"


class TogglingSensor(Sensor):
    """
    A sensor that toggles between high and low states at regular intervals.
    """

    def __init__(
        self, 
        name: str, 
        location: Tuple[float, float, float], 
        toggle_interval: float = 2.0, 
        high_value: float = 1.0, 
        low_value: float = 0.0,
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
            metadata: Optional metadata dictionary
        """
        super().__init__(
            name=name, sensor_type="toggle", location=location, metadata=metadata
        )
        self.toggle_interval = toggle_interval
        self.high_value = high_value
        self.low_value = low_value
        self.last_toggle = time.time()
        self.current_state = False
        self.current_value = low_value

    def read(self) -> float:
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
        return f"TogglingSensor(name='{self.name}', location={self.location})"

"""
Sensor module for Spaxiom DSL.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import numpy as np


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

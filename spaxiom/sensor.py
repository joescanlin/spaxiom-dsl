"""
Sensor module for Spaxiom DSL.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Union
import numpy as np
import time
import uuid

from spaxiom.units import Quantity, QuantityType


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

    def read(self, unit: Optional[str] = None) -> Union[Any, QuantityType, None]:
        """
        Read data from the sensor.

        Args:
            unit: Optional unit string to return the value as a Quantity with units.
                  If None, returns the raw value without units.

        Returns:
            Sensor data in an appropriate format for the sensor type,
            optionally wrapped in a Quantity object if unit is specified.
            Returns None if the sensor has no more data to provide.
        """
        value = self._read_raw()
        if value is None:
            return None

        if unit is not None:
            return Quantity(value, unit)
        return value

    def _read_raw(self) -> Any:
        """
        Read raw data from the sensor.

        Subclasses should implement this method rather than overriding read().

        Returns:
            Raw sensor data in an appropriate format for the sensor type.
            May return None if the sensor has no more data to provide.
        """
        raise NotImplementedError("Sensor subclasses must implement _read_raw()")

    def fuse_with(
        self, other: "Sensor", strategy: str = "average", **kwargs
    ) -> "Sensor":
        """
        Create a fusion sensor that combines this sensor with another.

        Args:
            other: Another sensor to fuse with
            strategy: Fusion strategy to use ('average', 'weighted')
            **kwargs: Additional arguments for the fusion strategy:
                      - For 'weighted': 'weights' can be provided as [w1, w2]
                      - For all strategies: 'name' and 'location' can be customized

        Returns:
            A fusion sensor that combines readings from both sensors

        Raises:
            ValueError: If an invalid strategy is specified
        """
        from spaxiom.fusion import WeightedFusion

        # Generate a unique name if not provided
        name = kwargs.get("name", f"fusion_{uuid.uuid4().hex[:8]}")

        # Use sensors' locations to determine fusion location if not provided
        location = kwargs.get("location", None)

        if strategy == "average":
            # Simple averaging with equal weights
            return WeightedFusion(
                name=name,
                sensors=[self, other],
                weights=[1.0, 1.0],
                location=location,
            )
        elif strategy == "weighted":
            # Weighted fusion with custom weights
            weights = kwargs.get("weights", [0.5, 0.5])

            # Ensure we have exactly two weights
            if len(weights) != 2:
                raise ValueError(
                    f"Expected 2 weights for fusing 2 sensors, got {len(weights)}"
                )

            return WeightedFusion(
                name=name,
                sensors=[self, other],
                weights=weights,
                location=location,
            )
        else:
            raise ValueError(f"Unknown fusion strategy: {strategy}")

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

    def _read_raw(self) -> float:
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
        return f"TogglingSensor(name='{self.name}', location={self.location})"

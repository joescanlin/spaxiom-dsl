"""
Core module for Spaxiom DSL containing base classes and registry functionality.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Union, Literal
import threading
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
        privacy: Privacy level of the sensor data ('public' or 'private')
        sample_period_s: Sampling period in seconds (0 means use global polling)
        metadata: Optional metadata dictionary
    """

    name: str
    sensor_type: str
    location: Tuple[float, float, float]
    privacy: Literal["public", "private"] = "public"
    sample_period_s: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Register sensor automatically
        from spaxiom.core import SensorRegistry

        SensorRegistry().add(self)

        # Initialize last_value field
        self.last_value = None

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
        self.last_value = value

        if value is None:
            return None

        if unit is not None:
            return Quantity(value, unit)
        return value

    def get_last_value(
        self, unit: Optional[str] = None
    ) -> Union[Any, QuantityType, None]:
        """
        Get the cached last value from the sensor without triggering a new read.

        Args:
            unit: Optional unit string to return the value as a Quantity with units.
                  If None, returns the raw value without units.

        Returns:
            The last sensor reading, optionally wrapped in a Quantity object if unit is specified.
            Returns None if no reading has been made yet.
        """
        if self.last_value is None:
            return None

        if unit is not None:
            return Quantity(self.last_value, unit)
        return self.last_value

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
                      - For all strategies: 'name', 'location', and 'privacy' can be customized

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

        # Use default privacy if not provided (will be overridden if component sensors are private)
        privacy = kwargs.get("privacy", "public")

        if strategy == "average":
            # Simple averaging with equal weights
            return WeightedFusion(
                name=name,
                sensors=[self, other],
                weights=[1.0, 1.0],
                location=location,
                privacy=privacy,
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
                privacy=privacy,
            )
        else:
            raise ValueError(f"Unknown fusion strategy: {strategy}")

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.sensor_type}', location={self.location}, privacy='{self.privacy}')"


class SensorRegistry:
    """
    Singleton registry for all sensors in the system.

    Tracks sensor privacy levels and provides methods to access sensors
    based on their privacy settings.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SensorRegistry, cls).__new__(cls)
                cls._instance._sensors = {}
                cls._instance._public_sensors = set()
                cls._instance._private_sensors = set()
            return cls._instance

    def add(self, sensor: Sensor) -> None:
        """
        Add a sensor to the registry.

        Args:
            sensor: The sensor to add

        Raises:
            ValueError: If a sensor with the same name already exists
        """
        if sensor.name in self._sensors:
            raise ValueError(f"Sensor with name '{sensor.name}' already exists")

        self._sensors[sensor.name] = sensor

        # Track privacy level
        if sensor.privacy == "public":
            self._public_sensors.add(sensor.name)
        elif sensor.privacy == "private":
            self._private_sensors.add(sensor.name)
        else:
            # This shouldn't happen due to type constraints, but just in case
            raise ValueError(f"Invalid privacy level: {sensor.privacy}")

    def get(self, name: str) -> Sensor:
        """
        Get a sensor by name.

        Args:
            name: The name of the sensor to retrieve

        Returns:
            The sensor with the given name

        Raises:
            KeyError: If no sensor with the given name exists
        """
        if name not in self._sensors:
            raise KeyError(f"No sensor with name '{name}' found")

        return self._sensors[name]

    def list_all(self) -> Dict[str, Sensor]:
        """
        List all registered sensors.

        Returns:
            A dictionary mapping sensor names to sensors
        """
        return self._sensors.copy()

    def list_public(self) -> Dict[str, Sensor]:
        """
        List all public sensors.

        Returns:
            A dictionary mapping sensor names to public sensors
        """
        return {name: self._sensors[name] for name in self._public_sensors}

    def list_private(self) -> Dict[str, Sensor]:
        """
        List all private sensors.

        Returns:
            A dictionary mapping sensor names to private sensors
        """
        return {name: self._sensors[name] for name in self._private_sensors}

    def clear(self) -> None:
        """
        Clear all registered sensors.
        """
        self._sensors.clear()
        self._public_sensors.clear()
        self._private_sensors.clear()

"""
Registry module for managing sensors in Spaxiom DSL.
"""

from typing import Dict
import threading

# Forward reference to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spaxiom.sensor import Sensor


class SensorRegistry:
    """
    Singleton registry for all sensors in the system.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SensorRegistry, cls).__new__(cls)
                cls._instance._sensors = {}
            return cls._instance

    def add(self, sensor) -> None:
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

    def get(self, name: str):
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

    def list_all(self) -> Dict[str, "Sensor"]:
        """
        List all registered sensors.

        Returns:
            A dictionary mapping sensor names to sensors
        """
        return self._sensors.copy()

    def clear(self) -> None:
        """
        Clear all registered sensors.
        """
        self._sensors.clear()

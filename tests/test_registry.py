"""
Tests for the Sensor Registry module.
"""

import unittest
from unittest.mock import MagicMock

from spaxiom.registry import SensorRegistry
from spaxiom.core import Sensor


class TestSensorRegistry(unittest.TestCase):
    """Test the SensorRegistry singleton class."""

    def setUp(self):
        """Set up for each test."""
        # Clear the registry before each test
        SensorRegistry().clear()

    def test_singleton_nature(self):
        """Test that SensorRegistry is a singleton."""
        registry1 = SensorRegistry()
        registry2 = SensorRegistry()
        self.assertIs(registry1, registry2, "SensorRegistry should be a singleton")

    def test_add_sensor(self):
        """Test adding a sensor to the registry."""
        registry = SensorRegistry()

        # Create a mock sensor
        sensor = MagicMock(spec=Sensor)
        sensor.name = "test_sensor"

        # Add the sensor
        registry.add(sensor)

        # Verify it was added
        self.assertIn("test_sensor", registry.list_all())
        self.assertEqual(sensor, registry.get("test_sensor"))

    def test_add_duplicate_sensor(self):
        """Test that adding a duplicate sensor raises ValueError."""
        registry = SensorRegistry()

        # Create two sensors with the same name
        sensor1 = MagicMock(spec=Sensor)
        sensor1.name = "duplicate_name"

        sensor2 = MagicMock(spec=Sensor)
        sensor2.name = "duplicate_name"

        # Add the first sensor
        registry.add(sensor1)

        # Adding the second should raise ValueError
        with self.assertRaises(ValueError):
            registry.add(sensor2)

    def test_get_sensor(self):
        """Test getting a sensor from the registry."""
        registry = SensorRegistry()

        # Create and add a mock sensor
        sensor = MagicMock(spec=Sensor)
        sensor.name = "get_test"
        registry.add(sensor)

        # Get the sensor
        retrieved = registry.get("get_test")
        self.assertEqual(sensor, retrieved)

    def test_get_nonexistent_sensor(self):
        """Test that getting a nonexistent sensor raises KeyError."""
        registry = SensorRegistry()

        with self.assertRaises(KeyError):
            registry.get("nonexistent_sensor")

    def test_list_all(self):
        """Test listing all sensors in the registry."""
        registry = SensorRegistry()

        # Create and add multiple mock sensors
        sensors = {}
        for i in range(3):
            sensor = MagicMock(spec=Sensor)
            sensor.name = f"list_test_{i}"
            sensors[sensor.name] = sensor
            registry.add(sensor)

        # Get all sensors
        all_sensors = registry.list_all()

        # Verify all were returned
        self.assertEqual(3, len(all_sensors))
        for name, sensor in sensors.items():
            self.assertIn(name, all_sensors)
            self.assertEqual(sensor, all_sensors[name])

    def test_clear(self):
        """Test clearing all sensors from the registry."""
        registry = SensorRegistry()

        # Add a few sensors
        for i in range(3):
            sensor = MagicMock(spec=Sensor)
            sensor.name = f"clear_test_{i}"
            registry.add(sensor)

        # Verify they were added
        self.assertEqual(3, len(registry.list_all()))

        # Clear the registry
        registry.clear()

        # Verify it's empty
        self.assertEqual(0, len(registry.list_all()))


if __name__ == "__main__":
    unittest.main()

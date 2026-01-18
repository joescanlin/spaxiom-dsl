"""Tests for spaxiom.edge.sensor_registry module."""

import os
import tempfile
import pytest

from spaxiom.core import SensorRegistry
from spaxiom.edge.database import EdgeDatabase
from spaxiom.edge.sensor_registry import (
    PersistentSensorRegistry,
    SensorHealth,
)
from spaxiom.sensor import RandomSensor


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = EdgeDatabase(db_path)
    db.init()

    yield db

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def registry(temp_db):
    """Create a persistent sensor registry for testing."""
    # Clear the global singleton registry to avoid test pollution
    core_registry = SensorRegistry()
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()

    yield PersistentSensorRegistry(temp_db)

    # Clean up after test
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()


class TestPersistentSensorRegistry:
    """Tests for PersistentSensorRegistry class."""

    def test_register_sensor(self, registry):
        """Test registering a new sensor."""
        sensor_id = registry.register(
            name="test_sensor",
            sensor_type="random",
            location=(1.0, 2.0, 0.0),
            config={"min_val": 0, "max_val": 100},
        )

        assert sensor_id is not None

        # Check sensor is in registry
        sensor = registry.get(sensor_id)
        assert sensor is not None
        assert sensor.name == "test_sensor"

    def test_register_duplicate_name(self, registry):
        """Test that duplicate names are rejected."""
        registry.register(name="unique_name", sensor_type="random")

        # Try to register with same name
        result = registry.register(name="unique_name", sensor_type="random")

        assert result is None

    def test_unregister_sensor(self, registry):
        """Test unregistering a sensor."""
        sensor_id = registry.register(name="to_delete", sensor_type="random")

        deleted = registry.unregister(sensor_id)

        assert deleted is True
        assert registry.get(sensor_id) is None

    def test_get_by_name(self, registry):
        """Test getting sensor by name."""
        registry.register(name="named_sensor", sensor_type="random")

        sensor = registry.get_by_name("named_sensor")

        assert sensor is not None
        assert sensor.name == "named_sensor"

    def test_list_all(self, registry):
        """Test listing all sensors."""
        registry.register(name="sensor1", sensor_type="random")
        registry.register(name="sensor2", sensor_type="random")

        all_sensors = registry.list_all()

        assert len(all_sensors) == 2

    def test_update_sensor(self, registry):
        """Test updating sensor configuration."""
        sensor_id = registry.register(
            name="update_sensor",
            sensor_type="random",
            config={"min_val": 0},
        )

        record = registry.update(
            sensor_id,
            config={"min_val": 10, "max_val": 50},
        )

        assert record is not None
        assert record.config["min_val"] == 10

    def test_disable_sensor(self, registry):
        """Test disabling a sensor."""
        sensor_id = registry.register(name="disable_test", sensor_type="random")

        # Sensor should be active
        assert registry.get(sensor_id) is not None

        # Disable it
        registry.update(sensor_id, enabled=False)

        # Should no longer be in active sensors
        assert registry.get(sensor_id) is None

        # But should still be in records
        records = registry.list_records()
        assert any(r.name == "disable_test" for r in records)

    def test_enable_disabled_sensor(self, registry):
        """Test re-enabling a disabled sensor."""
        sensor_id = registry.register(
            name="reenable_test",
            sensor_type="random",
            enabled=False,
        )

        # Should not be active
        assert registry.get(sensor_id) is None

        # Enable it
        registry.update(sensor_id, enabled=True)

        # Now should be active
        assert registry.get(sensor_id) is not None

    def test_test_sensor(self, registry):
        """Test testing a sensor."""
        sensor_id = registry.register(
            name="test_me",
            sensor_type="random",
            config={"min_val": 0, "max_val": 1},
        )

        health = registry.test_sensor(sensor_id)

        assert health.status == "ok"
        assert health.last_value is not None
        assert health.last_read is not None

    def test_test_missing_sensor(self, registry):
        """Test testing a non-existent sensor."""
        health = registry.test_sensor("nonexistent_id")

        assert health.status == "error"
        assert "not found" in health.error.lower()

    def test_check_health(self, registry):
        """Test checking health of all sensors."""
        registry.register(name="health1", sensor_type="random")
        registry.register(name="health2", sensor_type="random")

        health = registry.check_health()

        assert len(health) == 2
        for sensor_id, status in health.items():
            assert status["status"] == "ok"

    def test_count(self, registry):
        """Test counting sensors."""
        assert registry.count() == 0

        registry.register(name="count1", sensor_type="random")
        registry.register(name="count2", sensor_type="random")

        assert registry.count() == 2

    def test_count_all_includes_disabled(self, registry):
        """Test that count_all includes disabled sensors."""
        registry.register(name="enabled", sensor_type="random", enabled=True)
        registry.register(name="disabled", sensor_type="random", enabled=False)

        assert registry.count() == 1  # Active only
        assert registry.count_all() == 2  # All

    def test_supported_types(self):
        """Test getting supported sensor types."""
        types = PersistentSensorRegistry.get_supported_types()

        assert "random" in types
        assert "toggling" in types
        assert "base" in types

    def test_load_sensors(self, temp_db):
        """Test loading sensors from database."""
        # Clear global registry
        core_registry = SensorRegistry()
        core_registry._sensors.clear()
        core_registry._private_sensors.clear()

        # Create registry and add sensors
        registry1 = PersistentSensorRegistry(temp_db)
        registry1.register(name="persistent1", sensor_type="random", location=(0, 0, 0))
        registry1.register(name="persistent2", sensor_type="random", location=(1, 1, 0))

        # Clear global registry again to simulate restart
        core_registry._sensors.clear()
        core_registry._private_sensors.clear()

        # Create new registry instance and load
        registry2 = PersistentSensorRegistry(temp_db)
        loaded = registry2.load()

        assert loaded == 2
        assert registry2.get_by_name("persistent1") is not None
        assert registry2.get_by_name("persistent2") is not None

    def test_instantiate_random_sensor(self, registry):
        """Test that random sensor is properly instantiated."""
        sensor_id = registry.register(
            name="random_test",
            sensor_type="random",
            location=(1.0, 2.0, 0.0),
            config={"hz": 10.0},
        )

        sensor = registry.get(sensor_id)

        assert isinstance(sensor, RandomSensor)
        # Read should return value in range 0-1
        value = sensor.read()
        assert 0 <= value <= 1


class TestSensorHealth:
    """Tests for SensorHealth class."""

    def test_to_dict(self):
        """Test SensorHealth serialization."""
        health = SensorHealth(
            sensor_id="test_id",
            status="ok",
            last_read=1234567890.0,
            last_value=42.5,
        )

        d = health.to_dict()

        assert d["sensor_id"] == "test_id"
        assert d["status"] == "ok"
        assert d["last_value"] == 42.5

    def test_error_health(self):
        """Test error health status."""
        health = SensorHealth(
            sensor_id="error_id",
            status="error",
            error="Connection refused",
        )

        assert health.status == "error"
        assert health.error == "Connection refused"

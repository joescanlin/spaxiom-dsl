"""
test_harness_sanity.py - Paper Parity Sanity Check Test

This test verifies the paper parity test harness is correctly wired.
It uses EXISTING functionality that works today, not paper-specified features.

All tests in this file should PASS, proving:
1. pytest discovers tests in tests/paper_parity/
2. spaxiom imports work correctly
3. Basic sensor/condition/callback mechanisms function
"""

import pytest
from spaxiom import (
    RandomSensor,
    Condition,
    SensorRegistry,
    Zone,
    on,
    within,
    exists,
)
from spaxiom.events import EVENT_HANDLERS
from spaxiom.entities import ENTITY_SETS


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear sensor registry before and after each test."""
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    ENTITY_SETS.clear()
    yield
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    ENTITY_SETS.clear()


class TestHarnessSanity:
    """Sanity checks proving the test harness works."""

    def test_imports_work(self):
        """Verify spaxiom imports work correctly."""
        # These imports should not raise
        assert RandomSensor is not None
        assert Condition is not None
        assert SensorRegistry is not None
        assert Zone is not None
        assert on is not None
        assert within is not None
        assert exists is not None

    def test_sensor_creation(self):
        """Verify sensor can be created and registered."""
        sensor = RandomSensor(
            name="harness_test_sensor",
            location=(1, 2, 3),
            hz=10.0,
        )
        assert sensor is not None
        assert sensor.name == "harness_test_sensor"
        assert sensor.location == (1, 2, 3)

        # Verify registered
        registry = SensorRegistry()
        assert "harness_test_sensor" in registry.list_all()

    def test_sensor_read(self):
        """Verify sensor can be read."""
        sensor = RandomSensor(
            name="readable_sensor",
            location=(0, 0, 0),
            hz=10.0,
        )
        value = sensor.read()
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_condition_creation(self):
        """Verify condition can be created."""
        sensor = RandomSensor(
            name="cond_sensor",
            location=(0, 0, 0),
        )
        cond = Condition(lambda: sensor.read() > 0.5)
        assert cond is not None
        # Condition should be callable
        result = cond()
        assert isinstance(result, bool)

    def test_condition_operators(self):
        """Verify condition operators work."""
        cond_a = Condition(lambda: True)
        cond_b = Condition(lambda: False)

        # AND
        cond_and = cond_a & cond_b
        assert not cond_and()

        # OR
        cond_or = cond_a | cond_b
        assert cond_or()

        # NOT
        cond_not = ~cond_b
        assert cond_not()

    def test_zone_creation(self):
        """Verify zone can be created."""
        zone = Zone(0, 0, 10, 10)
        assert zone is not None
        assert zone.contains((5, 5))
        assert not zone.contains((15, 15))

    def test_on_decorator_registers_handler(self):
        """Verify @on decorator registers event handler."""
        sensor = RandomSensor(
            name="event_sensor",
            location=(0, 0, 0),
        )
        cond = Condition(lambda: sensor.read() > 0.5)

        @on(cond)
        def my_handler():
            pass

        # Handler should be registered
        assert len(EVENT_HANDLERS) == 1
        assert EVENT_HANDLERS[0][0] is cond
        # Note: @on returns a wrapper, so we check the name instead of identity
        assert EVENT_HANDLERS[0][1].__name__ == "my_handler"

    def test_paper_parity_directory_accessible(self):
        """Verify tests/paper_parity/ is a valid test directory."""
        import os

        test_dir = os.path.dirname(__file__)
        assert os.path.basename(test_dir) == "paper_parity"
        assert os.path.isfile(os.path.join(test_dir, "__init__.py"))


class TestTemporalOperators:
    """Sanity checks for temporal operators."""

    def test_within_creates_condition(self):
        """Verify within() creates a condition."""
        sensor = RandomSensor(
            name="temporal_sensor",
            location=(0, 0, 0),
        )
        base_cond = Condition(lambda: sensor.read() > 0.5)
        temporal_cond = within(5.0, base_cond)
        assert temporal_cond is not None
        # within() returns a Condition - verify it's callable and returns bool
        assert callable(temporal_cond)
        result = temporal_cond()
        assert isinstance(result, bool)


class TestExistsOperator:
    """Sanity checks for exists() operator."""

    def test_exists_with_entity_set(self):
        """Verify exists() works with EntitySet."""
        from spaxiom import EntitySet, Entity

        # Create entity set (requires a name)
        entities = EntitySet("test_entities")
        entities.add(Entity(id="e1", attrs={"value": 10}))
        entities.add(Entity(id="e2", attrs={"value": 20}))

        # exists with predicate
        cond = exists(entities, lambda e: e.attrs.get("value", 0) > 15)
        assert cond()  # e2 has value 20

        cond2 = exists(entities, lambda e: e.attrs.get("value", 0) > 100)
        assert not cond2()  # No entity with value > 100

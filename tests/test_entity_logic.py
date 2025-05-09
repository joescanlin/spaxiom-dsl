"""
Tests for the entity-related logic functions.
"""

import pytest

from spaxiom.entities import Entity, EntitySet, clear_entity_sets
from spaxiom.logic import exists


@pytest.fixture
def clean_registry():
    """Clear the entity sets registry before and after each test."""
    clear_entity_sets()
    yield
    clear_entity_sets()


@pytest.fixture
def sample_entity_set(clean_registry):
    """Create a sample entity set with test entities."""
    entity_set = EntitySet("test-entities")

    # Add entities with different attributes
    entity_set.add(Entity(id="e1", attrs={"type": "sensor", "value": 10}))
    entity_set.add(Entity(id="e2", attrs={"type": "sensor", "value": 25}))
    entity_set.add(Entity(id="e3", attrs={"type": "actuator", "value": 5}))
    entity_set.add(Entity(id="e4", attrs={"type": "actuator", "value": 30}))

    return entity_set


def test_exists_any_entity(sample_entity_set):
    """Test that exists() returns True if the entity set has any entities."""
    has_entities = exists(sample_entity_set)
    assert has_entities() is True

    # Create an empty entity set and test that exists returns False
    empty_set = EntitySet("empty-set")
    no_entities = exists(empty_set)
    assert no_entities() is False


def test_exists_with_predicate(sample_entity_set):
    """Test that exists() with a predicate returns True if at least one entity satisfies it."""
    # Check if any entity has value > 20
    high_value = exists(sample_entity_set, lambda e: e.attrs.get("value", 0) > 20)
    assert high_value() is True

    # Check if any entity has value > 50 (none should)
    very_high_value = exists(sample_entity_set, lambda e: e.attrs.get("value", 0) > 50)
    assert very_high_value() is False

    # Check if any entity has type = "sensor"
    is_sensor = exists(sample_entity_set, lambda e: e.attrs.get("type") == "sensor")
    assert is_sensor() is True

    # Check if any entity has type = "unknown" (none should)
    is_unknown = exists(sample_entity_set, lambda e: e.attrs.get("type") == "unknown")
    assert is_unknown() is False


def test_exists_combined_conditions(sample_entity_set):
    """Test that exists() can be combined with other conditions using logical operators."""
    # Create simple conditions
    has_sensors = exists(sample_entity_set, lambda e: e.attrs.get("type") == "sensor")
    has_high_value = exists(sample_entity_set, lambda e: e.attrs.get("value", 0) > 20)
    has_low_value = exists(sample_entity_set, lambda e: e.attrs.get("value", 0) < 15)

    # Combine with AND
    has_sensors_and_high_value = has_sensors & has_high_value
    assert has_sensors_and_high_value() is True

    # Combine with OR
    has_low_or_high_value = has_low_value | has_high_value
    assert has_low_or_high_value() is True

    # Combine with NOT
    no_high_value = ~has_high_value
    assert no_high_value() is False


def test_exists_with_empty_set():
    """Test exists() with an empty entity set."""
    empty_set = EntitySet("empty-set")

    # Without predicate
    has_any = exists(empty_set)
    assert has_any() is False

    # With predicate
    has_with_predicate = exists(empty_set, lambda e: True)
    assert has_with_predicate() is False


def test_exists_chained_filtering(sample_entity_set):
    """Test exists() with entity sets created from filtering."""
    # Filter to only sensors
    sensors = sample_entity_set.filter(lambda e: e.attrs.get("type") == "sensor")
    assert len(sensors) == 2

    # Check if any sensor has high value
    sensor_high_value = exists(sensors, lambda e: e.attrs.get("value", 0) > 20)
    assert sensor_high_value() is True

    # Filter to only actuators
    actuators = sample_entity_set.filter(lambda e: e.attrs.get("type") == "actuator")
    assert len(actuators) == 2

    # Check if any actuator has very high value
    actuator_very_high_value = exists(actuators, lambda e: e.attrs.get("value", 0) > 40)
    assert actuator_very_high_value() is False

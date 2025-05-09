"""
Tests for the Entities module functionality.
"""

import pytest

from spaxiom.entities import (
    Entity,
    EntitySet,
    ENTITY_SETS,
    get_entity_set,
    clear_entity_sets,
)


@pytest.fixture
def clean_registry():
    """Clear the entity sets registry before and after each test."""
    clear_entity_sets()
    yield
    clear_entity_sets()


def test_entity_creation():
    """Test that Entity objects can be created correctly."""
    # Create an entity with auto-generated ID
    entity1 = Entity()
    assert entity1.id is not None
    assert entity1.attrs == {}

    # Create an entity with specified ID and attributes
    entity2 = Entity(id="test-id", attrs={"name": "Test Entity", "value": 42})
    assert entity2.id == "test-id"
    assert entity2.attrs["name"] == "Test Entity"
    assert entity2.attrs["value"] == 42


def test_entity_set_creation(clean_registry):
    """Test that EntitySet objects can be created and registered globally."""
    entity_set = EntitySet("test-set")
    assert entity_set.name == "test-set"
    assert len(entity_set) == 0

    # Check that the entity set was registered globally
    assert "test-set" in ENTITY_SETS
    assert ENTITY_SETS["test-set"] is entity_set


def test_entity_set_duplicate_name(clean_registry):
    """Test that creating an EntitySet with a duplicate name raises an error."""
    EntitySet("test-set")

    with pytest.raises(ValueError) as excinfo:
        EntitySet("test-set")

    assert "already exists" in str(excinfo.value)


def test_entity_set_add_remove(clean_registry):
    """Test adding and removing entities from an EntitySet."""
    entity_set = EntitySet("test-set")
    entity = Entity(id="test-entity")

    # Add entity
    entity_set.add(entity)
    assert len(entity_set) == 1

    # Adding the same entity again should not increase the count
    entity_set.add(entity)
    assert len(entity_set) == 1

    # Remove entity
    entity_set.remove(entity)
    assert len(entity_set) == 0

    # Removing a non-existent entity should raise KeyError
    with pytest.raises(KeyError):
        entity_set.remove(entity)


def test_entity_set_iteration(clean_registry):
    """Test iterating over entities in an EntitySet."""
    entity_set = EntitySet("test-set")
    entity1 = Entity(id="entity1")
    entity2 = Entity(id="entity2")
    entity3 = Entity(id="entity3")

    entity_set.add(entity1)
    entity_set.add(entity2)
    entity_set.add(entity3)

    entities = list(entity_set)
    assert len(entities) == 3
    assert entity1 in entities
    assert entity2 in entities
    assert entity3 in entities


def test_entity_set_filter(clean_registry):
    """Test filtering entities in an EntitySet."""
    entity_set = EntitySet("test-set")

    entity1 = Entity(id="entity1", attrs={"type": "A", "value": 10})
    entity2 = Entity(id="entity2", attrs={"type": "A", "value": 20})
    entity3 = Entity(id="entity3", attrs={"type": "B", "value": 30})

    entity_set.add(entity1)
    entity_set.add(entity2)
    entity_set.add(entity3)

    # Filter by attribute "type"
    type_a_entities = entity_set.filter(lambda e: e.attrs.get("type") == "A")
    assert len(type_a_entities) == 2
    assert entity1 in type_a_entities
    assert entity2 in type_a_entities
    assert entity3 not in type_a_entities

    # Filter by attribute "value"
    high_value_entities = entity_set.filter(lambda e: e.attrs.get("value", 0) > 15)
    assert len(high_value_entities) == 2
    assert entity1 not in high_value_entities
    assert entity2 in high_value_entities
    assert entity3 in high_value_entities


def test_entity_set_find_by_id(clean_registry):
    """Test finding entities by ID in an EntitySet."""
    entity_set = EntitySet("test-set")

    entity1 = Entity(id="entity1")
    entity2 = Entity(id="entity2")

    entity_set.add(entity1)
    entity_set.add(entity2)

    found_entity = entity_set.find_by_id("entity1")
    assert found_entity is entity1

    not_found = entity_set.find_by_id("entity3")
    assert not_found is None


def test_get_entity_set(clean_registry):
    """Test retrieving an entity set by name."""
    entity_set = EntitySet("test-set")

    retrieved = get_entity_set("test-set")
    assert retrieved is entity_set

    not_found = get_entity_set("non-existent")
    assert not_found is None


def test_clear_entity_sets(clean_registry):
    """Test clearing all entity sets from the registry."""
    EntitySet("set1")
    EntitySet("set2")

    assert len(ENTITY_SETS) == 2

    clear_entity_sets()

    assert len(ENTITY_SETS) == 0

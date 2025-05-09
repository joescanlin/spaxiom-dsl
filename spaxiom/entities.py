"""
Entities module for defining and working with collections of entities in Spaxiom DSL.
"""

from typing import Dict, Set, Callable, Iterator, Any, Optional, TypeVar, Generic
import uuid

# Type variable for entity filtering
T = TypeVar("T", bound="Entity")

# Global registry of all entity sets
ENTITY_SETS: Dict[str, "EntitySet"] = {}


class Entity:
    """
    A generic entity with a unique identifier and arbitrary attributes.

    Attributes:
        id: Unique identifier for the entity
        attrs: Dictionary of arbitrary attributes
    """

    def __init__(
        self, id: Optional[str] = None, attrs: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an entity with an optional ID and attributes.

        Args:
            id: Unique identifier for the entity (auto-generated if not provided)
            attrs: Dictionary of arbitrary attributes
        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.attrs = attrs or {}

    def __repr__(self) -> str:
        """Return a string representation of the entity."""
        return f"Entity(id='{self.id}', attrs={self.attrs})"


class EntitySet(Generic[T]):
    """
    A collection of entities with support for filtering.

    Attributes:
        name: Name of the entity set
        entities: Set of entities in this collection
    """

    def __init__(self, name: str):
        """
        Initialize an entity set with a unique name.

        Args:
            name: Unique name for the entity set

        Raises:
            ValueError: If an entity set with the same name already exists
        """
        if name in ENTITY_SETS:
            raise ValueError(f"EntitySet with name '{name}' already exists")

        self.name = name
        self.entities: Set[T] = set()

        # Register this entity set in the global registry
        ENTITY_SETS[name] = self

    def add(self, entity: T) -> None:
        """
        Add an entity to this set.

        Args:
            entity: The entity to add
        """
        self.entities.add(entity)

    def remove(self, entity: T) -> None:
        """
        Remove an entity from this set.

        Args:
            entity: The entity to remove

        Raises:
            KeyError: If the entity is not in the set
        """
        self.entities.remove(entity)

    def filter(self, fn: Callable[[T], bool]) -> "EntitySet[T]":
        """
        Create a new entity set containing only entities that match the filter function.

        Args:
            fn: Filter function that takes an entity and returns a boolean

        Returns:
            A new EntitySet containing only the filtered entities
        """
        result = EntitySet(f"{self.name}_filtered_{uuid.uuid4().hex[:8]}")
        for entity in self.entities:
            if fn(entity):
                result.add(entity)
        return result

    def find_by_id(self, id: str) -> Optional[T]:
        """
        Find an entity by its ID.

        Args:
            id: The ID to search for

        Returns:
            The entity with the given ID, or None if not found
        """
        for entity in self.entities:
            if entity.id == id:
                return entity
        return None

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over all entities in this set.

        Returns:
            An iterator over the entities
        """
        return iter(self.entities)

    def __len__(self) -> int:
        """
        Get the number of entities in this set.

        Returns:
            The number of entities
        """
        return len(self.entities)

    def __repr__(self) -> str:
        """Return a string representation of the entity set."""
        return f"EntitySet(name='{self.name}', count={len(self)})"


def get_entity_set(name: str) -> Optional[EntitySet]:
    """
    Get an entity set by name from the global registry.

    Args:
        name: The name of the entity set

    Returns:
        The entity set, or None if not found
    """
    return ENTITY_SETS.get(name)


def clear_entity_sets() -> None:
    """
    Clear all entity sets from the global registry.
    Used primarily for testing.
    """
    ENTITY_SETS.clear()

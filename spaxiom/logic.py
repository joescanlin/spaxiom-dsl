"""
Logic module with timestamped Conditions for Spaxiom DSL.

Implements condition dependency tracking and evaluation modes per Paper Section 2.5:
- Polling mode (default): condition evaluated every tick
- Event-driven mode: condition evaluated only when dependencies change
- Auto mode: runtime selects based on whether dependencies are trackable
"""

import time
from typing import Callable, Optional, TypeVar, Set, Any, Iterable, Literal

from spaxiom.entities import EntitySet, Entity
from spaxiom.summarize import RollingSummary

# Type variable for entity filtering
T = TypeVar("T", bound=Entity)

# Evaluation mode type
EvaluationMode = Literal["polling", "event-driven", "auto"]


class _IdentitySet:
    """A set-like class that uses object identity for comparison.

    This is needed because dependency objects (Sensors, Patterns, temporal windows,
    derived signals, etc.) may not be hashable, but we still need set-like operations
    for tracking condition dependencies. Uses id() for all comparisons, so works
    with any Python object regardless of hashability.
    """

    def __init__(self, items: Iterable[Any]):
        # Store items as id -> item mapping
        self._items: dict = {id(item): item for item in items}

    def __contains__(self, item: Any) -> bool:
        return id(item) in self._items

    def __iter__(self):
        return iter(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, _IdentitySet):
            return self._items.keys() == other._items.keys()
        if isinstance(other, set):
            # Compare by identity with set items
            other_ids = {id(item) for item in other}
            return self._items.keys() == other_ids
        return False

    def __and__(self, other: Any) -> "_IdentitySet":
        """Intersection with another IdentitySet or iterable."""
        if isinstance(other, _IdentitySet):
            common = {k: v for k, v in self._items.items() if k in other._items}
            result = _IdentitySet([])
            result._items = common
            return result
        # For regular iterable, compare by identity
        other_ids = {id(item) for item in other}
        common = {k: v for k, v in self._items.items() if k in other_ids}
        result = _IdentitySet([])
        result._items = common
        return result

    def __or__(self, other: "_IdentitySet") -> "_IdentitySet":
        """Union with another IdentitySet."""
        result = _IdentitySet([])
        result._items = {**self._items, **other._items}
        return result

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def __repr__(self) -> str:
        return f"_IdentitySet({list(self._items.values())})"


class Condition:
    """
    A wrapper for a boolean function that can be combined with logical operators
    and tracks its evaluation timestamp and history.

    Enables writing expressions like:

    in_zone = Condition(lambda: zone.contains(sensor.location))
    is_active = Condition(lambda: sensor.is_active())

    combined = in_zone & is_active  # logical AND
    alternative = in_zone | is_active  # logical OR
    negated = ~in_zone  # logical NOT

    Supports evaluation modes:
    - "polling" (default): evaluated every tick
    - "event-driven": only evaluated when dependencies change
    - "auto": runtime selects based on dependency trackability
    """

    def __init__(
        self,
        fn: Callable[..., bool],
        mode: EvaluationMode = "polling",
        depends_on: Optional[Iterable[Any]] = None,
    ):
        """
        Initialize with a function that returns a boolean.

        Args:
            fn: A callable that returns a boolean. May accept optional arguments
                such as 'now' and 'history' for temporal conditions.
            mode: Evaluation mode - "polling", "event-driven", or "auto"
            depends_on: Optional iterable of dependencies (sensors, patterns).
                       Required for event-driven mode to work correctly.
        """
        self.fn = fn
        self.mode = mode
        # Store dependencies as a list (sensors/patterns may not be hashable)
        self._depends_on: list = list(depends_on) if depends_on else []
        self.last_value = False
        self.last_changed = time.time()  # Initialize with current time
        # Track whether the condition just transitioned to true
        self._last_transition_to_true = None
        # Track evaluation count for testing event-driven mode
        self._eval_count = 0

    @property
    def dependencies(self) -> Set[Any]:
        """
        Return the set of dependencies (sensors, patterns) this condition depends on.

        Note: Uses object identity for comparison since sensors may not be hashable.

        Returns:
            Set of dependency objects declared via depends_on parameter.
        """
        # Return a set-like wrapper that uses identity comparison
        return _IdentitySet(self._depends_on)

    @property
    def _effective_mode(self) -> str:
        """
        Return the effective evaluation mode.

        For "auto" mode, returns "event-driven" if dependencies are declared,
        otherwise returns "polling".
        """
        if self.mode == "auto":
            # If we have trackable dependencies, use event-driven
            if self._depends_on:
                return "event-driven"
            # Otherwise fall back to polling
            return "polling"
        return self.mode

    def evaluate(self, now: Optional[float] = None, **kwargs) -> bool:
        """
        Evaluate the condition and update the timestamp fields.

        Args:
            now: The current timestamp (uses current time if None)
            **kwargs: Optional arguments to pass to the wrapped function

        Returns:
            The boolean result of the wrapped function
        """
        # Increment evaluation count for testing
        self._eval_count += 1

        # Get current time if not provided
        if now is None:
            now = time.time()

        # Make a copy of kwargs and ensure now isn't passed twice
        kwargs_copy = kwargs.copy()
        if "now" in kwargs_copy:
            del kwargs_copy["now"]

        # Evaluate the function
        try:
            current_value = bool(self.fn(**kwargs_copy))
        except (TypeError, ValueError):
            try:
                # If it doesn't accept kwargs, try with just now
                if (
                    hasattr(self.fn, "__code__")
                    and "now" in self.fn.__code__.co_varnames
                ):
                    current_value = bool(self.fn(now))
                else:
                    # If it doesn't accept any arguments, call without args
                    current_value = bool(self.fn())
            except (TypeError, ValueError):
                # Last resort: no arguments
                current_value = bool(self.fn())

        # Track transition to true
        if current_value and not self.last_value:
            self._last_transition_to_true = now

        # Update timestamp if the value changed
        if current_value != self.last_value:
            self.last_changed = now
            self.last_value = current_value

        return current_value

    def __call__(self, **kwargs) -> bool:
        """
        Evaluate the condition by calling evaluate.

        Args:
            **kwargs: Optional arguments to pass to the wrapped function.
                     Used by temporal conditions to receive 'now' and 'history'.

        Returns:
            The boolean result of evaluate
        """
        # Extract now from kwargs if present
        now = kwargs.get("now")

        # Call evaluate with extracted now and the remaining kwargs
        return self.evaluate(now=now, **kwargs)

    def summary(self, window: int = 60) -> RollingSummary:
        """
        Create a RollingSummary for tracking statistics from a numeric sensor.

        Use this method when the condition references a numeric sensor, and you
        want to track statistics like average, max, and trend over time.

        Args:
            window: Number of readings to maintain in the rolling window (default: 60)

        Returns:
            A RollingSummary instance configured with the specified window size

        Example:
            ```python
            # Create a condition based on a temperature sensor
            temp_c = Condition(lambda: temp_sensor.read())

            # Get a summary to track statistics
            temp_stats = temp_c.summary(window=30)

            # Later, update statistics and get a summary
            temp_stats.add(temp_sensor.read())
            print(f"Temperature: {temp_stats.to_text()}")  # e.g., "avg=22.5, max=24.1 🡑"
            ```
        """
        return RollingSummary(window=window)

    def transitioned_to_true(self, now: Optional[float] = None) -> bool:
        """
        Check if the condition just transitioned to true at the given timestamp.

        Args:
            now: The current timestamp (uses current time if None)

        Returns:
            True if the condition is true and just changed from false to true
        """
        if now is None:
            now = time.time()

        # Evaluate the condition at this timestamp
        current_value = self.evaluate(now=now)

        # Return true if we just recorded a transition at this exact timestamp
        return current_value and self._last_transition_to_true == now

    def __and__(self, other: "Condition") -> "Condition":
        """
        Implement the & operator (logical AND).

        Args:
            other: Another Condition object

        Returns:
            A new Condition that is true only when both conditions are true.
            The new condition inherits dependencies from both operands.
        """

        def combined_condition(**kwargs):
            # Short-circuit evaluation
            if not self(**kwargs):
                return False
            return other(**kwargs)

        # Combine dependencies from both conditions (dedupe by identity)
        combined_deps = self.dependencies | other.dependencies
        # If either is polling, result is polling; otherwise event-driven
        mode = (
            "polling"
            if self.mode == "polling" or other.mode == "polling"
            else self.mode
        )
        return Condition(combined_condition, mode=mode, depends_on=list(combined_deps))

    def __or__(self, other: "Condition") -> "Condition":
        """
        Implement the | operator (logical OR).

        Args:
            other: Another Condition object

        Returns:
            A new Condition that is true when either condition is true.
            The new condition inherits dependencies from both operands.
        """

        def combined_condition(**kwargs):
            # Short-circuit evaluation
            if self(**kwargs):
                return True
            return other(**kwargs)

        # Combine dependencies from both conditions (dedupe by identity)
        combined_deps = self.dependencies | other.dependencies
        # If either is polling, result is polling; otherwise event-driven
        mode = (
            "polling"
            if self.mode == "polling" or other.mode == "polling"
            else self.mode
        )
        return Condition(combined_condition, mode=mode, depends_on=list(combined_deps))

    def __invert__(self) -> "Condition":
        """
        Implement the ~ operator (logical NOT).

        Returns:
            A new Condition that is true when this condition is false.
            The new condition inherits dependencies from the original.
        """

        def inverted_condition(**kwargs):
            return not self(**kwargs)

        return Condition(
            inverted_condition, mode=self.mode, depends_on=self._depends_on
        )

    def __repr__(self) -> str:
        """Return a string representation of the condition"""
        return f"Condition({self.fn.__name__ if hasattr(self.fn, '__name__') else 'lambda'})"


def transitioned_to_true(condition: Condition, now: Optional[float] = None) -> bool:
    """
    Helper function to check if a condition just transitioned to true.

    Args:
        condition: The condition to check
        now: Current timestamp (uses current time if None)

    Returns:
        True if the condition just transitioned to true
    """
    return condition.transitioned_to_true(now)


def exists(
    entity_set: EntitySet[T], predicate: Optional[Callable[[T], bool]] = None
) -> Condition:
    """
    Create a condition that is true when at least one entity in the set satisfies the predicate.

    Args:
        entity_set: The entity set to check
        predicate: Function that takes an entity and returns a boolean.
                   If None, the condition is true if the entity set has any entities.

    Returns:
        A Condition that is true when at least one entity satisfies the predicate

    Example:
        ```python
        # Check if any entity in the sensors set has a temperature above 30
        hot_sensor_exists = exists(sensors, lambda s: s.attrs.get("temperature", 0) > 30)

        # Check if there are any entities in the set
        has_entities = exists(sensors)
        ```
    """

    def check_existence() -> bool:
        if not entity_set:
            return False

        if predicate is None:
            return len(entity_set) > 0

        return any(predicate(entity) for entity in entity_set)

    return Condition(check_existence)

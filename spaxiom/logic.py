"""
Logic module with timestamped Conditions for Spaxiom DSL.
"""

import time
from typing import Callable, Optional, TypeVar

from spaxiom.entities import EntitySet, Entity
from spaxiom.summarize import RollingSummary

# Type variable for entity filtering
T = TypeVar("T", bound=Entity)


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
    """

    def __init__(self, fn: Callable[..., bool]):
        """
        Initialize with a function that returns a boolean.

        Args:
            fn: A callable that returns a boolean. May accept optional arguments
                such as 'now' and 'history' for temporal conditions.
        """
        self.fn = fn
        self.last_value = False
        self.last_changed = time.time()  # Initialize with current time
        # Track whether the condition just transitioned to true
        self._last_transition_to_true = None

    def evaluate(self, now: Optional[float] = None, **kwargs) -> bool:
        """
        Evaluate the condition and update the timestamp fields.

        Args:
            now: The current timestamp (uses current time if None)
            **kwargs: Optional arguments to pass to the wrapped function

        Returns:
            The boolean result of the wrapped function
        """
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
            A new Condition that is true only when both conditions are true
        """

        def combined_condition(**kwargs):
            # Short-circuit evaluation
            if not self(**kwargs):
                return False
            return other(**kwargs)

        return Condition(combined_condition)

    def __or__(self, other: "Condition") -> "Condition":
        """
        Implement the | operator (logical OR).

        Args:
            other: Another Condition object

        Returns:
            A new Condition that is true when either condition is true
        """

        def combined_condition(**kwargs):
            # Short-circuit evaluation
            if self(**kwargs):
                return True
            return other(**kwargs)

        return Condition(combined_condition)

    def __invert__(self) -> "Condition":
        """
        Implement the ~ operator (logical NOT).

        Returns:
            A new Condition that is true when this condition is false
        """

        def inverted_condition(**kwargs):
            return not self(**kwargs)

        return Condition(inverted_condition)

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

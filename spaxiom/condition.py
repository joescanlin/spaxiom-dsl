"""
Condition module for logical expressions in Spaxiom DSL.
"""

from typing import Callable


class Condition:
    """
    A wrapper for a boolean function that can be combined with logical operators.

    Enables writing expressions like:

    in_zone = Condition(lambda: zone.contains(sensor.location))
    is_active = Condition(lambda: sensor.is_active())

    combined = in_zone & is_active  # logical AND
    alternative = in_zone | is_active  # logical OR
    negated = ~in_zone  # logical NOT
    """

    def __init__(self, fn: Callable[[], bool]):
        """
        Initialize with a function that returns a boolean.

        Args:
            fn: A callable that takes no arguments and returns a boolean
        """
        self.fn = fn

    def __call__(self) -> bool:
        """
        Evaluate the condition by calling the wrapped function.

        Returns:
            The boolean result of the wrapped function
        """
        return bool(self.fn())

    def __and__(self, other: "Condition") -> "Condition":
        """
        Implement the & operator (logical AND).

        Args:
            other: Another Condition object

        Returns:
            A new Condition that is true only when both conditions are true
        """
        return Condition(lambda: self() and other())

    def __or__(self, other: "Condition") -> "Condition":
        """
        Implement the | operator (logical OR).

        Args:
            other: Another Condition object

        Returns:
            A new Condition that is true when either condition is true
        """
        return Condition(lambda: self() or other())

    def __invert__(self) -> "Condition":
        """
        Implement the ~ operator (logical NOT).

        Returns:
            A new Condition that is true when this condition is false
        """
        return Condition(lambda: not self())

    def __repr__(self) -> str:
        """Return a string representation of the condition"""
        return f"Condition({self.fn.__name__ if hasattr(self.fn, '__name__') else 'lambda'})"

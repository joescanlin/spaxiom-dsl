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

    def __init__(self, fn: Callable[..., bool]):
        """
        Initialize with a function that returns a boolean.

        Args:
            fn: A callable that returns a boolean. May accept optional arguments
               such as 'now' and 'history' for temporal conditions.
        """
        self.fn = fn

    def __call__(self, **kwargs) -> bool:
        """
        Evaluate the condition by calling the wrapped function.

        Args:
            **kwargs: Optional arguments to pass to the wrapped function.
                     Used by temporal conditions to receive 'now' and 'history'.

        Returns:
            The boolean result of the wrapped function
        """
        try:
            return bool(self.fn(**kwargs))
        except TypeError:
            # If the function doesn't accept the kwargs, call it without arguments
            return bool(self.fn())

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

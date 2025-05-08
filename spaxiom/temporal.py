"""
Temporal module for time-based condition evaluation in Spaxiom DSL.
"""

from typing import Deque, Tuple
import time

from spaxiom.condition import Condition


class TemporalWindow:
    """
    A time window that evaluates whether a condition has been continuously true
    for a specified duration.

    Attributes:
        duration_s: Duration in seconds for which the base condition must be continuously true
        base: The underlying condition to evaluate over time
    """

    def __init__(self, duration_s: float, base: Condition):
        """
        Initialize a temporal window with a duration and base condition.

        Args:
            duration_s: Duration in seconds for which the base condition must be continuously true
            base: The underlying condition to evaluate over time
        """
        self.duration_s = duration_s
        self.base = base

    def evaluate(self, now: float, history: Deque[Tuple[float, bool]]) -> bool:
        """
        Evaluate whether the base condition has been continuously true for the specified duration.

        Args:
            now: Current timestamp in seconds since epoch
            history: Deque of (timestamp, value) tuples representing the history of the base condition

        Returns:
            True if the base condition has been continuously true for duration_s seconds, False otherwise
        """
        if not history:
            return False

        # Check if the condition is currently true
        if not history[-1][1]:
            return False

        # Start from the most recent entry and work backwards
        # We need all entries to be True for at least duration_s seconds
        earliest_required_time = now - self.duration_s

        # Find the most recent False value
        most_recent_false_time = None
        for timestamp, value in reversed(history):
            if not value:
                most_recent_false_time = timestamp
                break

        # If we found a False value, check when it occurred
        if most_recent_false_time is not None:
            # If the most recent False is more recent than our required window,
            # then the condition hasn't been True for the full duration
            if most_recent_false_time >= earliest_required_time:
                return False

        # If all values in our time window are True, and we have enough history
        # Make sure we have at least one reading that covers the start of our window
        # to avoid false positives with insufficient history
        has_early_enough_reading = False
        for timestamp, _ in history:
            if timestamp <= earliest_required_time:
                has_early_enough_reading = True
                break

        return has_early_enough_reading


def within(seconds: float, cond: Condition) -> Condition:
    """
    Create a condition that is true when the base condition has been continuously
    true for the specified duration.

    Args:
        seconds: Duration in seconds for which the base condition must be continuously true
        cond: The base condition to evaluate over time

    Returns:
        A new Condition that wraps a TemporalWindow instance

    Example:
        ```python
        sensor_active = Condition(lambda: sensor.is_active())
        sensor_active_for_5s = within(5.0, sensor_active)
        ```
    """
    window = TemporalWindow(seconds, cond)

    # The runtime will inject now and history when evaluating this condition
    def temporal_condition(now=None, history=None):
        if now is None:
            now = time.time()
        if history is None:
            return False

        return window.evaluate(now, history)

    return Condition(temporal_condition)

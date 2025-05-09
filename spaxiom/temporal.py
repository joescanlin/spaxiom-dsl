"""
Temporal module for time-based condition evaluation in Spaxiom DSL.
"""

from typing import Deque, Tuple, List, Dict
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


class SequencePattern:
    """
    A pattern that evaluates whether a sequence of conditions has occurred in order
    within a specified time window.

    Attributes:
        conditions: List of conditions that must occur in sequence
        within_s: Maximum duration in seconds for the entire sequence to occur
    """

    def __init__(self, conditions: List[Condition], within_s: float):
        """
        Initialize a sequence pattern with ordered conditions and time window.

        Args:
            conditions: Ordered list of conditions that must occur in sequence
            within_s: Maximum duration in seconds for the entire sequence to occur

        Raises:
            ValueError: If conditions list is empty
        """
        if not conditions:
            raise ValueError("Conditions list cannot be empty")

        self.conditions = conditions
        self.within_s = within_s
        self._last_matched_indices: Dict[int, float] = (
            {}
        )  # Maps condition index to timestamp of last match

    def evaluate(self, now: float, histories: List[Deque[Tuple[float, bool]]]) -> bool:
        """
        Evaluate whether the sequence of conditions has occurred in order within
        the specified time window.

        Args:
            now: Current timestamp in seconds since epoch
            histories: List of history deques for each condition in the sequence

        Returns:
            True if all conditions have occurred in sequence within the time window, False otherwise
        """
        if len(histories) != len(self.conditions):
            return False

        earliest_allowed_time = now - self.within_s
        matched_indices = {}  # Temporary storage for matched timestamps

        # Look for pattern start (first condition) first
        first_condition_history = histories[0]
        first_match_time = None

        # Search backwards through history for the most recent transition to true for the first condition
        for i in range(len(first_condition_history) - 1, 0, -1):
            current = first_condition_history[i]
            previous = first_condition_history[i - 1]

            # Found a transition to true (previous=False, current=True)
            if current[1] and not previous[1]:
                # If this transition occurred within our time window
                if current[0] >= earliest_allowed_time:
                    first_match_time = current[0]
                    matched_indices[0] = first_match_time
                    break

        # If we didn't find the first condition, the sequence can't match
        if first_match_time is None:
            return False

        # Now check the rest of the conditions in order
        last_match_time = first_match_time

        for i in range(1, len(self.conditions)):
            condition_history = histories[i]
            match_found = False

            # Search for transitions to true that occurred after the previous match
            for j in range(len(condition_history) - 1, 0, -1):
                current = condition_history[j]
                previous = condition_history[j - 1]

                # Found a transition to true that happened after the previous condition matched
                if current[1] and not previous[1] and current[0] > last_match_time:
                    matched_indices[i] = current[0]
                    last_match_time = current[0]
                    match_found = True
                    break

            # If any condition in the sequence didn't match, the whole sequence fails
            if not match_found:
                return False

        # If we made it here, we found matches for all conditions in sequence
        # Final check: is the entire sequence within our time window?
        total_sequence_time = last_match_time - first_match_time
        if total_sequence_time <= self.within_s:
            # Store matched indices for future reference
            self._last_matched_indices = matched_indices
            return True

        return False


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


def sequence(*conditions: Condition, within_s: float) -> Condition:
    """
    Create a condition that is true when a sequence of conditions has occurred
    in the specified order within a time window.

    Args:
        *conditions: Ordered list of conditions that must occur in sequence
        within_s: Maximum duration in seconds for the entire sequence to occur

    Returns:
        A new Condition that evaluates to True when the sequence pattern is detected

    Example:
        ```python
        door_opened = Condition(lambda: door_sensor.is_open())
        person_detected = Condition(lambda: person_sensor.read() > 0.8)
        light_turned_on = Condition(lambda: light_sensor.read() > 0.5)

        # Pattern: door opened, then person detected, then light turned on, all within 10 seconds
        entry_sequence = sequence(door_opened, person_detected, light_turned_on, within_s=10.0)
        ```
    """
    if not conditions:
        raise ValueError("At least one condition must be provided")

    pattern = SequencePattern(list(conditions), within_s)

    # The runtime will inject now and all condition histories
    def sequence_condition(now=None, histories=None):
        if now is None:
            now = time.time()
        if histories is None:
            return False

        return pattern.evaluate(now, histories)

    return Condition(sequence_condition)

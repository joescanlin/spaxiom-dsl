"""
Tests for the Temporal module functionality.
"""

from collections import deque
import time

from spaxiom.condition import Condition
from spaxiom.temporal import TemporalWindow, within


def test_temporal_window_initialization():
    """Test that TemporalWindow objects can be created correctly."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    assert window.duration_s == 5.0
    assert window.base == cond


def test_temporal_window_evaluate_empty_history():
    """Test that TemporalWindow evaluate returns False with empty history."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    history = deque()
    now = time.time()

    assert window.evaluate(now, history) is False


def test_temporal_window_evaluate_condition_false():
    """Test that TemporalWindow evaluate returns False when current condition is False."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    now = time.time()
    history = deque(
        [(now - 10.0, True), (now - 5.0, True), (now, False)]  # Current value is False
    )

    assert window.evaluate(now, history) is False


def test_temporal_window_evaluate_not_long_enough():
    """Test that TemporalWindow returns False when condition hasn't been True long enough."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    now = time.time()
    # Create history with a false at the 3-second mark, so there's only 3 seconds of continuous True
    history = deque(
        [
            (now - 10.0, True),
            (now - 8.0, True),
            (now - 6.0, True),
            (now - 3.0, False),  # False 3 seconds ago
            (now - 2.0, True),  # Only 2 seconds of continuous True
            (now, True),
        ]
    )

    assert window.evaluate(now, history) is False


def test_temporal_window_evaluate_long_enough():
    """Test that TemporalWindow returns True when condition has been True long enough."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    now = time.time()
    history = deque(
        [
            (now - 10.0, False),
            (now - 7.0, True),  # True for 7 seconds, which is > 5
            (now - 3.0, True),
            (now, True),
        ]
    )

    assert window.evaluate(now, history) is True


def test_temporal_window_evaluate_edge_case():
    """Test that TemporalWindow handles edge case correctly."""
    cond = Condition(lambda: True)
    window = TemporalWindow(5.0, cond)

    now = time.time()
    history = deque(
        [
            (now - 10.0, False),
            (now - 5.0, True),  # Exactly 5 seconds ago
            (now - 3.0, True),
            (now, True),
        ]
    )

    assert window.evaluate(now, history) is True


def test_within_helper():
    """Test the within helper function."""
    cond = Condition(lambda: True)
    temporal_cond = within(5.0, cond)

    # Should be a Condition instance
    assert isinstance(temporal_cond, Condition)

    # Should return False with no history
    assert temporal_cond() is False

    # Should use current time if not provided
    now = time.time()
    # Create history with a false value within the last 5 seconds
    history = deque(
        [
            (now - 10.0, True),
            (
                now - 4.0,
                False,
            ),  # False 4 seconds ago, so condition is not true for full 5 seconds
            (now - 2.0, True),
            (now, True),
        ]
    )

    assert temporal_cond(now=now, history=history) is False

    # Should evaluate correctly with history and now for long enough condition
    history = deque(
        [
            (now - 10.0, False),
            (now - 7.0, True),  # True for 7 seconds, which is > 5
            (now - 3.0, True),
            (now, True),
        ]
    )

    assert temporal_cond(now=now, history=history) is True


def test_within_helper_integration():
    """Test the within helper works with regular condition operations."""
    base_cond = Condition(lambda: True)
    other_cond = Condition(lambda: False)

    # Test AND operation
    combined = within(5.0, base_cond) & other_cond

    now = time.time()
    history = deque([(now - 10.0, True), (now - 6.0, True), (now, True)])

    # The temporal part would be True, but other_cond is False, so result is False
    assert combined(now=now, history=history) is False

    # Test OR operation
    combined_or = within(5.0, base_cond) | other_cond

    # The temporal part is True, so result is True despite other_cond being False
    assert combined_or(now=now, history=history) is True

    # Test NOT operation
    negated = ~within(5.0, base_cond)

    # The temporal part is True, so negated is False
    assert negated(now=now, history=history) is False

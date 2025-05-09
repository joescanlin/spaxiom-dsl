"""
Tests for the sequence pattern functionality in Spaxiom DSL.
"""

import pytest
from collections import deque

from spaxiom.condition import Condition
from spaxiom.temporal import SequencePattern, sequence


class TestSequencePattern:
    """Test cases for the SequencePattern class."""

    def test_empty_conditions_raises_error(self):
        """Test that empty conditions list raises ValueError."""
        with pytest.raises(ValueError):
            SequencePattern([], within_s=10.0)

    def test_basic_sequence_detection(self):
        """Test basic sequence detection with mock condition histories."""
        # Create mock conditions
        cond1 = Condition(lambda: True)
        cond2 = Condition(lambda: True)
        cond3 = Condition(lambda: True)

        # Create sequence pattern with 10-second window
        pattern = SequencePattern([cond1, cond2, cond3], within_s=10.0)

        # Current time reference
        now = 100.0

        # Create history deques with transitions to true at different times
        # Format: (timestamp, value)
        # Condition 1: Transitioned to true at t=92
        hist1 = deque(
            [
                (90.0, False),  # False at t=90
                (91.0, False),  # False at t=91
                (92.0, True),  # True at t=92 (transition point)
                (93.0, True),  # True at t=93
                (94.0, True),  # True at t=94
            ]
        )

        # Condition 2: Transitioned to true at t=95
        hist2 = deque(
            [
                (93.0, False),  # False at t=93
                (94.0, False),  # False at t=94
                (95.0, True),  # True at t=95 (transition point)
                (96.0, True),  # True at t=96
                (97.0, True),  # True at t=97
            ]
        )

        # Condition 3: Transitioned to true at t=98
        hist3 = deque(
            [
                (96.0, False),  # False at t=96
                (97.0, False),  # False at t=97
                (98.0, True),  # True at t=98 (transition point)
                (99.0, True),  # True at t=99
                (100.0, True),  # True at t=100
            ]
        )

        # Sequence spans from t=92 to t=98, which is 6 seconds - within the 10s window
        result = pattern.evaluate(now, [hist1, hist2, hist3])
        assert result is True

    def test_sequence_outside_window(self):
        """Test sequence that spans longer than the allowed window."""
        # Create mock conditions
        cond1 = Condition(lambda: True)
        cond2 = Condition(lambda: True)

        # Create sequence pattern with 5-second window
        pattern = SequencePattern([cond1, cond2], within_s=5.0)

        # Current time reference
        now = 100.0

        # Condition 1: Transitioned to true at t=90
        hist1 = deque(
            [
                (89.0, False),
                (90.0, True),  # Transition point
                (91.0, True),
            ]
        )

        # Condition 2: Transitioned to true at t=97 (7 seconds after cond1)
        hist2 = deque(
            [
                (96.0, False),
                (97.0, True),  # Transition point
                (98.0, True),
            ]
        )

        # Sequence spans 7 seconds, which exceeds the 5s window
        result = pattern.evaluate(now, [hist1, hist2])
        assert result is False

    def test_sequence_wrong_order(self):
        """Test that sequence detection fails if events occur in wrong order."""
        # Create mock conditions
        cond1 = Condition(lambda: True)
        cond2 = Condition(lambda: True)

        # Create sequence pattern
        pattern = SequencePattern([cond1, cond2], within_s=10.0)

        # Current time reference
        now = 100.0

        # Condition 1: Transitioned to true at t=95 (after cond2!)
        hist1 = deque(
            [
                (94.0, False),
                (95.0, True),  # Transition point
                (96.0, True),
            ]
        )

        # Condition 2: Transitioned to true at t=92 (before cond1!)
        hist2 = deque(
            [
                (91.0, False),
                (92.0, True),  # Transition point
                (93.0, True),
            ]
        )

        # Events occurred in wrong order
        result = pattern.evaluate(now, [hist1, hist2])
        assert result is False


class TestSequenceHelper:
    """Test cases for the sequence helper function."""

    def test_sequence_helper_basic(self):
        """Test that the sequence helper correctly wraps conditions."""
        # Create mock conditions
        cond1 = Condition(lambda: True)
        cond2 = Condition(lambda: True)
        cond3 = Condition(lambda: True)

        # Create a sequence condition
        seq_condition = sequence(cond1, cond2, cond3, within_s=5.0)

        # Verify it's a Condition
        assert isinstance(seq_condition, Condition)

        # Mock the necessary arguments for calling the condition
        now = 100.0

        # Mock histories for the three conditions
        histories = [
            # Condition 1: Transitioned to true at t=96
            deque(
                [
                    (95.0, False),
                    (96.0, True),  # Transition point
                    (97.0, True),
                ]
            ),
            # Condition 2: Transitioned to true at t=97
            deque(
                [
                    (96.0, False),
                    (97.0, True),  # Transition point
                    (98.0, True),
                ]
            ),
            # Condition 3: Transitioned to true at t=99
            deque(
                [
                    (98.0, False),
                    (99.0, True),  # Transition point
                    (100.0, True),
                ]
            ),
        ]

        # The sequence spans 3 seconds, which is within the 5s window
        result = seq_condition(now=now, histories=histories)
        assert result is True

    def test_empty_sequence_raises_error(self):
        """Test that empty sequence raises ValueError."""
        with pytest.raises(ValueError):
            sequence(within_s=10.0)

    def test_sequence_helper_missing_arguments(self):
        """Test that sequence helper handles missing now/histories properly."""
        # Create mock conditions
        cond1 = Condition(lambda: True)
        cond2 = Condition(lambda: True)

        # Create a sequence condition
        seq_condition = sequence(cond1, cond2, within_s=5.0)

        # Missing histories should return False
        assert seq_condition(now=100.0) is False

        # Missing now should use current time
        # This is hard to test directly, so we'll just verify it doesn't crash
        try:
            seq_condition(histories=[deque(), deque()])
            assert True  # If we got here, no exception was raised
        except Exception:
            assert (
                False
            ), "sequence condition raised an exception with missing 'now' parameter"

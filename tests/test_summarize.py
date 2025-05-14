"""
Tests for the summarize module.
"""

import pytest
import numpy as np
from spaxiom import RollingSummary


class TestRollingSummary:
    """Test cases for the RollingSummary class."""

    def test_init(self):
        """Test initialization with different window sizes."""
        # Default window size
        summary = RollingSummary()
        assert summary.window == 10
        assert len(summary.readings) == 0

        # Custom window size
        summary = RollingSummary(window=5)
        assert summary.window == 5
        assert len(summary.readings) == 0

        # Invalid window size
        with pytest.raises(ValueError):
            RollingSummary(window=1)

    def test_add(self):
        """Test adding values to the summary."""
        summary = RollingSummary(window=3)

        # Add regular numeric values
        summary.add(1.0)
        summary.add(2)
        summary.add(3.5)
        assert list(summary.readings) == [1.0, 2.0, 3.5]

        # Test rolling behavior (oldest value is dropped)
        summary.add(4.0)
        assert list(summary.readings) == [2.0, 3.5, 4.0]

        # Test adding numpy values
        summary.clear()
        summary.add(np.array([1.0]))
        summary.add(np.float32(2.0))
        assert list(summary.readings) == [1.0, 2.0]

    def test_stats(self):
        """Test statistical methods."""
        summary = RollingSummary(window=5)

        # Empty summary
        assert summary.get_average() is None
        assert summary.get_max() is None
        assert summary.get_min() is None
        assert summary.get_trend() is None

        # Add values
        summary.add(2.0)
        summary.add(4.0)
        summary.add(6.0)
        summary.add(8.0)
        summary.add(10.0)

        # Test statistics
        assert summary.get_average() == 6.0
        assert summary.get_max() == 10.0
        assert summary.get_min() == 2.0
        assert summary.get_trend() == "rising"

        # Test falling trend
        summary.clear()
        summary.add(10.0)
        summary.add(8.0)
        summary.add(6.0)
        summary.add(4.0)
        summary.add(2.0)
        assert summary.get_trend() == "falling"

        # Test stable trend
        summary.clear()
        summary.add(5.0)
        summary.add(7.0)
        summary.add(6.0)
        summary.add(4.0)
        summary.add(5.0)
        assert summary.get_trend() == "stable"  # first and last are equal

    def test_to_text(self):
        """Test the to_text method."""
        summary = RollingSummary(window=3)

        # Empty summary
        assert summary.to_text() == "no data"

        # Rising trend
        summary.add(1.0)
        summary.add(2.0)
        summary.add(3.0)
        assert summary.to_text() == "avg=2.00, max=3.00 🡑"

        # Falling trend
        summary.clear()
        summary.add(3.0)
        summary.add(2.0)
        summary.add(1.0)
        assert summary.to_text() == "avg=2.00, max=3.00 🡓"

        # Stable trend (first == last)
        summary.clear()
        summary.add(2.0)
        summary.add(3.0)
        summary.add(2.0)
        assert summary.to_text() == "avg=2.33, max=3.00"  # no arrow for stable

        # Custom precision
        assert summary.to_text(precision=1) == "avg=2.3, max=3.0"
        assert summary.to_text(precision=3) == "avg=2.333, max=3.000"

    def test_clear_and_empty(self):
        """Test the clear and is_empty methods."""
        summary = RollingSummary()
        assert summary.is_empty() is True

        summary.add(1.0)
        assert summary.is_empty() is False

        summary.clear()
        assert summary.is_empty() is True

"""
Summarize module for statistical analysis of sensor readings in Spaxiom DSL.
"""

from collections import deque
from typing import Optional, Union, Deque
import statistics
import numpy as np


class RollingSummary:
    """
    A class for maintaining a rolling window of numeric readings and computing statistics.

    Keeps track of the last N readings and provides methods to get statistics
    and a human-readable text summary including trend information.

    Attributes:
        window: Number of readings to keep in the rolling window
        readings: Deque containing the most recent readings
    """

    def __init__(self, window: int = 10):
        """
        Initialize a rolling summary with a specified window size.

        Args:
            window: Number of readings to maintain in the rolling window (default: 10)

        Raises:
            ValueError: If window is less than 2
        """
        if window < 2:
            raise ValueError("Window size must be at least 2")

        self.window = window
        self.readings: Deque[float] = deque(maxlen=window)

    def add(self, value: Union[float, int, np.ndarray]) -> None:
        """
        Add a new reading to the rolling window.

        Args:
            value: The numeric value to add
        """
        # Handle numpy arrays or other sequence types by extracting a scalar value
        if isinstance(value, np.ndarray) and value.size == 1:
            value = float(value.item())
        elif hasattr(value, "__len__") and len(value) == 1:
            value = float(value[0])

        # Convert to float to ensure consistency
        self.readings.append(float(value))

    def clear(self) -> None:
        """Clear all readings from the window."""
        self.readings.clear()

    def is_empty(self) -> bool:
        """Check if there are any readings in the window."""
        return len(self.readings) == 0

    def get_average(self) -> Optional[float]:
        """
        Get the average of all readings in the window.

        Returns:
            The average value or None if no readings are available
        """
        if not self.readings:
            return None
        return statistics.mean(self.readings)

    def get_max(self) -> Optional[float]:
        """
        Get the maximum value in the window.

        Returns:
            The maximum value or None if no readings are available
        """
        if not self.readings:
            return None
        return max(self.readings)

    def get_min(self) -> Optional[float]:
        """
        Get the minimum value in the window.

        Returns:
            The minimum value or None if no readings are available
        """
        if not self.readings:
            return None
        return min(self.readings)

    def get_trend(self) -> Optional[str]:
        """
        Determine if the trend is rising, falling, or stable.

        Returns:
            "rising", "falling", "stable", or None if not enough readings
        """
        if len(self.readings) < 2:
            return None

        readings_list = list(self.readings)

        # Use the first and last readings to determine the overall trend
        if readings_list[-1] > readings_list[0]:
            return "rising"
        elif readings_list[-1] < readings_list[0]:
            return "falling"
        else:
            return "stable"

    def to_text(self, precision: int = 2) -> str:
        """
        Get a text summary of the readings including average, max, and trend.

        Args:
            precision: Number of decimal places to display (default: 2)

        Returns:
            A formatted string with summary statistics and trend indicator
        """
        if not self.readings:
            return "no data"

        avg = self.get_average()
        max_val = self.get_max()
        trend = self.get_trend()

        # Format average and max with the specified precision
        avg_text = f"avg={avg:.{precision}f}"
        max_text = f"max={max_val:.{precision}f}"

        # Add trend indicator
        trend_symbol = ""
        if trend == "rising":
            trend_symbol = "🡑"  # rising arrow
        elif trend == "falling":
            trend_symbol = "🡓"  # falling arrow

        # Combine parts
        return f"{avg_text}, {max_text} {trend_symbol}".rstrip()

    def __repr__(self) -> str:
        """Return a string representation of the summary."""
        return f"RollingSummary(window={self.window}, readings={list(self.readings)})"

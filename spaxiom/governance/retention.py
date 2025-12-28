"""
Retention policy for history buffers and temporal windows.

Provides bounded storage with TTL-based cleanup.

Reference: Paper Section 5 "Privacy, Security, and Data Governance"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class RetentionPolicy:
    """Policy for data retention in history buffers.

    Defines how long different types of events should be retained,
    with exceptions for compliance-critical events.

    Attributes:
        default_days: Default retention period in days
        raw_events_days: Retention for raw sensor events (often shorter)
        exceptions: Event types retained indefinitely (e.g., SafetyIncident)
        max_entries: Maximum number of entries per buffer (None = unlimited)
    """

    default_days: int = 30
    raw_events_days: int = 7
    exceptions: List[str] = field(default_factory=list)
    max_entries: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate policy parameters."""
        if self.default_days < 0:
            raise ValueError("default_days must be non-negative")
        if self.raw_events_days < 0:
            raise ValueError("raw_events_days must be non-negative")
        if self.max_entries is not None and self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        # Convert exceptions to set for O(1) lookup
        self._exception_set: Set[str] = set(self.exceptions)

    def get_retention_seconds(self, event_type: str = "") -> float:
        """Get retention period in seconds for an event type.

        Args:
            event_type: Type of event (e.g., "raw_sensor", "SafetyIncident")

        Returns:
            Retention period in seconds, or float('inf') for exceptions
        """
        if event_type in self._exception_set:
            return float("inf")
        if event_type == "raw_sensor":
            return self.raw_events_days * 24 * 60 * 60
        return self.default_days * 24 * 60 * 60

    def is_exception(self, event_type: str) -> bool:
        """Check if event type is in exceptions list.

        Args:
            event_type: Type of event

        Returns:
            True if event should be retained indefinitely
        """
        return event_type in self._exception_set

    def should_retain(
        self,
        timestamp: float,
        event_type: str = "",
        current_time: Optional[float] = None,
    ) -> bool:
        """Check if an event should be retained based on its timestamp.

        Args:
            timestamp: Event timestamp (seconds since epoch)
            event_type: Type of event
            current_time: Current time (defaults to time.time())

        Returns:
            True if event should be retained
        """
        if self.is_exception(event_type):
            return True
        current_time = current_time or time.time()
        retention_seconds = self.get_retention_seconds(event_type)
        age = current_time - timestamp
        return age < retention_seconds

    def apply_to_buffer(
        self,
        buffer: List[Dict[str, Any]],
        timestamp_key: str = "timestamp",
        type_key: str = "event_type",
        current_time: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Apply retention policy to a buffer of events.

        Removes events older than retention period, except for exceptions.

        Args:
            buffer: List of event dicts
            timestamp_key: Key for timestamp field
            type_key: Key for event type field
            current_time: Current time (defaults to time.time())

        Returns:
            New buffer with only retained events
        """
        current_time = current_time or time.time()
        retained = []
        for event in buffer:
            ts = event.get(timestamp_key, 0)
            event_type = event.get(type_key, "")
            if self.should_retain(ts, event_type, current_time):
                retained.append(event)

        # Apply max_entries limit if set
        if self.max_entries is not None and len(retained) > self.max_entries:
            # Keep most recent entries
            retained = retained[-self.max_entries :]

        return retained

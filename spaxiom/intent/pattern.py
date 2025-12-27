"""
Pattern base class and event types for INTENT patterns.

Implements the Pattern interface per Paper Section 2.4:
- Pattern base class with update(dt, context), emit(), depends_on()
- PatternEvent base class with to_dict() for stable serialization
- Typed event subclasses for each pattern type

Patterns are updated in Phase 2 of the tick loop in dependency order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class PatternEvent:
    """Base class for typed pattern events.

    All pattern events must inherit from this class and use @dataclass.
    Events are immutable and have stable serialization via to_dict().
    """

    event_type: str = field(init=False)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    pattern_name: str = ""

    def __post_init__(self):
        # Set event_type to the class name
        self.event_type = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary for JSON/LLM consumption.

        Returns:
            Dict with all event fields. Serialization is deterministic.
        """
        return asdict(self)


# Typed event classes for each pattern


@dataclass
class OccupancyChanged(PatternEvent):
    """Emitted when occupancy percentage changes significantly."""

    zone: str = ""
    percent: float = 0.0
    previous_percent: float = 0.0
    hotspots: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CrowdingDetected(PatternEvent):
    """Emitted when occupancy exceeds a threshold."""

    zone: str = ""
    percent: float = 0.0
    threshold: float = 0.0


@dataclass
class QueueLengthChanged(PatternEvent):
    """Emitted when queue length changes."""

    queue_name: str = ""
    length: float = 0.0
    previous_length: float = 0.0
    wait_time_seconds: float = 0.0


@dataclass
class ADLEvent(PatternEvent):
    """Emitted when an Activity of Daily Living is detected."""

    activity: str = ""  # "got_up", "meal", "bath", "walk"
    count_today: int = 0


@dataclass
class ServiceNeeded(PatternEvent):
    """Emitted when facility service is needed."""

    facility: str = ""
    reason: str = ""  # "low_towels", "bin_full", "gas_high", "spill"
    details: Dict[str, Any] = field(default_factory=dict)


class Pattern(ABC):
    """Abstract base class for INTENT patterns.

    Patterns encapsulate domain-specific logic and emit typed events.
    They are updated each tick in Phase 2 of the runtime.

    Subclasses must implement:
    - update(dt, context): Update internal state
    - emit(): Return list of events since last emit
    - depends_on(): Return list of dependencies for ordering
    """

    def __init__(self, name: str = ""):
        """Initialize pattern with optional name.

        Args:
            name: Human-readable name for the pattern
        """
        self._name = name
        self._pending_events: List[PatternEvent] = []

    @property
    def name(self) -> str:
        """Return pattern name."""
        return self._name or self.__class__.__name__

    @abstractmethod
    def update(self, dt: float, context: Dict[str, Any]) -> None:
        """Update pattern state.

        Called by runtime each tick in Phase 2.

        Args:
            dt: Time delta since last tick in seconds
            context: Tick context (sensor values, other pattern states)
        """
        pass

    def emit(self) -> List[PatternEvent]:
        """Return events emitted since last call and clear pending events.

        Returns:
            List of PatternEvent objects. May be empty.
        """
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events

    def _emit_event(self, event: PatternEvent) -> None:
        """Queue an event for emission.

        Args:
            event: Event to queue
        """
        if not event.pattern_name:
            event.pattern_name = self.name
        self._pending_events.append(event)

    def depends_on(self) -> List[Any]:
        """Return list of dependencies for ordering.

        Override in subclasses to declare dependencies on sensors or other patterns.
        Patterns are updated in topological order based on dependencies.

        Returns:
            List of dependency objects (sensors, patterns, etc.)
        """
        return []


# Global event handlers for pattern events
PATTERN_EVENT_HANDLERS: List[tuple] = []


def on_pattern_event(
    event_type: Optional[type] = None, pattern: Optional[Pattern] = None
):
    """Decorator to register a callback for pattern events.

    Args:
        event_type: Optional event class to filter by (e.g., OccupancyChanged)
        pattern: Optional pattern instance to filter by

    Example:
        @on_pattern_event(OccupancyChanged)
        def handle_occupancy(event):
            print(f"Occupancy changed to {event.percent}%")
    """

    def decorator(fn):
        PATTERN_EVENT_HANDLERS.append((event_type, pattern, fn))
        return fn

    return decorator


def dispatch_pattern_events(events: List[PatternEvent]) -> int:
    """Dispatch events to registered handlers.

    Args:
        events: List of events to dispatch

    Returns:
        Number of handlers invoked
    """
    count = 0
    for event in events:
        for event_type, pattern, handler in PATTERN_EVENT_HANDLERS:
            # Check event type filter
            if event_type is not None and not isinstance(event, event_type):
                continue
            # Check pattern filter
            if pattern is not None and event.pattern_name != pattern.name:
                continue
            # Call handler
            try:
                handler(event)
                count += 1
            except Exception:
                # Isolated dispatch - don't propagate exceptions
                pass
    return count

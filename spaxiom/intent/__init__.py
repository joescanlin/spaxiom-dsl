"""
INTENT: High-level patterns on top of the Spaxiom DSL.

This module exposes convenience abstractions for:
- Pattern base class with update/emit/depends_on interface
- Typed event classes for pattern emission
- Occupancy fields (from 2-D sensors)
- Queue and flow estimates
- Activities of Daily Living (ADL) tracking
- Facilities management (FM) service thresholds
"""

from .pattern import (
    Pattern,
    PatternEvent,
    OccupancyChanged,
    CrowdingDetected,
    QueueLengthChanged,
    ADLEvent,
    ServiceNeeded,
    on_pattern_event,
    dispatch_pattern_events,
    PATTERN_EVENT_HANDLERS,
)
from .occupancy_field import OccupancyField
from .queue_flow import QueueFlow
from .adl_tracker import ADLTracker
from .fm_steward import FmSteward

__all__ = [
    # Base classes
    "Pattern",
    "PatternEvent",
    # Event types
    "OccupancyChanged",
    "CrowdingDetected",
    "QueueLengthChanged",
    "ADLEvent",
    "ServiceNeeded",
    # Event handling
    "on_pattern_event",
    "dispatch_pattern_events",
    "PATTERN_EVENT_HANDLERS",
    # Patterns
    "OccupancyField",
    "QueueFlow",
    "ADLTracker",
    "FmSteward",
]

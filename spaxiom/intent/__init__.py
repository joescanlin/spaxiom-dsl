"""
INTENT: High-level patterns on top of the Spaxiom DSL.

This module exposes convenience abstractions for:
- Occupancy fields (from 2-D sensors)
- Queue and flow estimates
- Activities of Daily Living (ADL) tracking
- Facilities management (FM) service thresholds
"""

from .occupancy_field import OccupancyField
from .queue_flow import QueueFlow
from .adl_tracker import ADLTracker
from .fm_steward import FmSteward

__all__ = [
    "OccupancyField",
    "QueueFlow",
    "ADLTracker",
    "FmSteward",
]

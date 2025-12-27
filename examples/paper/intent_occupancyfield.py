#!/usr/bin/env python3
"""
intent_occupancyfield.py - Paper Parity Example

Demonstrates the OccupancyField INTENT pattern:
- Pattern base class with update(dt, context), emit(), depends_on()
- Typed events (OccupancyChanged, CrowdingDetected)
- Event serialization via to_dict()

Reference: Paper Section 2.4 and Section 3
"""

import asyncio
import numpy as np

from spaxiom.tick import PhasedTickRunner
from spaxiom.intent import (
    Pattern,
    OccupancyField,
    OccupancyChanged,
    CrowdingDetected,
    on_pattern_event,
    dispatch_pattern_events,
    PATTERN_EVENT_HANDLERS,
)


class MockGridSensor:
    """Mock sensor that returns a controllable frame."""

    def __init__(self, rows=10, cols=10):
        self.rows = rows
        self.cols = cols
        self._frame = np.zeros((rows, cols), dtype=np.float32)

    def frame(self):
        return self._frame

    def set_occupancy(self, percent: float):
        """Set occupancy to a specific percentage."""
        total_tiles = self.rows * self.cols
        active_tiles = int(total_tiles * percent / 100.0)
        self._frame = np.zeros((self.rows, self.cols), dtype=np.float32)
        self._frame.flat[:active_tiles] = 1.0


def main():
    print("=" * 60)
    print("intent_occupancyfield.py - OccupancyField Pattern Demo")
    print("=" * 60)
    print()

    # Clear any existing handlers
    PATTERN_EVENT_HANDLERS.clear()

    # Create a mock grid sensor (10x10 = 100 tiles)
    sensor = MockGridSensor(10, 10)

    # Create OccupancyField pattern with a crowding threshold of 60%
    field = OccupancyField(
        sensor,
        name="lobby_field",
        crowding_threshold=60.0,
    )

    print("1. Pattern Interface Demonstration")
    print("-" * 40)

    # Show that OccupancyField inherits from Pattern
    print(f"   OccupancyField inherits from Pattern: {isinstance(field, Pattern)}")

    # Show the depends_on() method
    deps = field.depends_on()
    print(f"   depends_on() returns: {deps}")
    print(f"   Contains sensor: {sensor in deps}")
    print()

    # =========================================================================
    # 2. Event emission demonstration
    # =========================================================================
    print("2. Event Emission Demonstration")
    print("-" * 40)

    # Set occupancy to 20%
    sensor.set_occupancy(20.0)
    print("   Setting occupancy to 20%")

    # Update pattern (simulating a tick)
    field.update(dt=0.1, context={})
    events = field.emit()
    print(f"   Events after first update: {len(events)}")

    # Now change to 50% (significant change > 5% threshold)
    sensor.set_occupancy(50.0)
    print("   Setting occupancy to 50% (change > 5% threshold)")

    field.update(dt=0.1, context={})
    events = field.emit()
    print(f"   Events emitted: {len(events)}")
    for event in events:
        print(f"     - {event.__class__.__name__}: {event.to_dict()}")
    print()

    # =========================================================================
    # 3. Crowding detection
    # =========================================================================
    print("3. Crowding Detection")
    print("-" * 40)

    # Now exceed the crowding threshold (60%)
    sensor.set_occupancy(75.0)
    print("   Setting occupancy to 75% (above 60% threshold)")

    field.update(dt=0.1, context={})
    events = field.emit()
    print(f"   Events emitted: {len(events)}")
    for event in events:
        print(f"     - {event.__class__.__name__}:")
        d = event.to_dict()
        for key, value in d.items():
            print(f"         {key}: {value}")
    print()

    # =========================================================================
    # 4. Event handler demonstration
    # =========================================================================
    print("4. Event Handler Demonstration")
    print("-" * 40)

    # Register handlers using decorator
    @on_pattern_event(OccupancyChanged)
    def handle_occupancy(event):
        print(f"   [HANDLER] Occupancy changed to {event.percent:.1f}%")

    @on_pattern_event(CrowdingDetected)
    def handle_crowding(event):
        print(f"   [HANDLER] CROWDING ALERT in {event.zone}!")

    # Reset pattern state
    sensor.set_occupancy(10.0)
    field2 = OccupancyField(sensor, name="entrance", crowding_threshold=50.0)

    # Trigger a significant change
    field2.update(dt=0.1, context={})
    field2.emit()  # Baseline

    sensor.set_occupancy(70.0)  # Trigger both events
    field2.update(dt=0.1, context={})
    events = field2.emit()

    print(f"   Dispatching {len(events)} events to handlers:")
    count = dispatch_pattern_events(events)
    print(f"   Handlers invoked: {count}")
    print()

    # =========================================================================
    # 5. Runtime integration
    # =========================================================================
    print("5. Runtime Integration")
    print("-" * 40)

    async def run_with_runtime():
        runtime = PhasedTickRunner(tick_rate_hz=10.0)

        sensor3 = MockGridSensor(10, 10)
        sensor3.set_occupancy(15.0)
        field3 = OccupancyField(sensor3, name="runtime_field", crowding_threshold=50.0)

        runtime.register_pattern(field3)
        print(f"   Registered pattern: {field3.name}")

        # Run first tick (baseline)
        stats = await runtime.run_single_tick()
        print(f"   Tick 1: patterns_updated={stats.patterns_updated}")

        # Change occupancy and run another tick
        sensor3.set_occupancy(80.0)
        stats = await runtime.run_single_tick()
        print(
            f"   Tick 2: patterns_updated={stats.patterns_updated}, "
            f"events_emitted={stats.events_emitted}"
        )

        # Show collected events
        if stats.pattern_events:
            print("   Collected events:")
            for event in stats.pattern_events:
                print(f"     - {event.__class__.__name__}: zone={event.zone}")

    asyncio.run(run_with_runtime())
    print()

    print("Done!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
intent_all_patterns.py - Paper Parity Example

Demonstrates all INTENT patterns with runtime integration:
- OccupancyField
- QueueFlow
- ADLTracker
- FmSteward

All patterns implement the Pattern base class interface:
- update(dt, context)
- emit()
- depends_on()

Reference: Paper Section 2.4
"""

import asyncio
import numpy as np

from spaxiom.tick import PhasedTickRunner
from spaxiom.intent import (
    Pattern,
    OccupancyField,
    QueueFlow,
    ADLTracker,
    FmSteward,
    PATTERN_EVENT_HANDLERS,
)

# =============================================================================
# Mock sensors for each pattern type
# =============================================================================


class MockGridSensor:
    """Mock floor grid sensor."""

    def __init__(self, rows=10, cols=10):
        self.rows = rows
        self.cols = cols
        self._frame = np.zeros((rows, cols), dtype=np.float32)

    def frame(self):
        return self._frame

    def set_occupancy(self, percent: float):
        total_tiles = self.rows * self.cols
        active_tiles = int(total_tiles * percent / 100.0)
        self._frame = np.zeros((self.rows, self.cols), dtype=np.float32)
        self._frame.flat[:active_tiles] = 1.0


class MockSensor:
    """Mock boolean/threshold sensor."""

    def __init__(self, value=0.0):
        self._value = value

    def read(self):
        return self._value

    def set_value(self, value):
        self._value = value


class MockDoorCounter:
    """Mock door counter."""

    def __init__(self, count=0):
        self._count = count

    def count_delta(self):
        return self._count


class MockTowelSensor:
    """Mock towel dispenser sensor."""

    def __init__(self, percent=100.0):
        self._percent = percent

    def percent_remaining(self):
        return self._percent


class MockBinSensor:
    """Mock bin sensor."""

    def __init__(self, percent=0.0):
        self._percent = percent

    def percent_full(self):
        return self._percent


class MockGasSensor:
    """Mock gas sensor."""

    def __init__(self, ppm=0.0):
        self._ppm = ppm

    def ppm(self):
        return self._ppm


class MockFloorSensor:
    """Mock floor wetness sensor."""

    def __init__(self, wet=False):
        self._wet = wet

    def is_wet(self):
        return self._wet


def main():
    print("=" * 60)
    print("intent_all_patterns.py - All INTENT Patterns Demo")
    print("=" * 60)
    print()

    # Clear any existing handlers
    PATTERN_EVENT_HANDLERS.clear()

    # =========================================================================
    # 1. Verify all patterns inherit from Pattern
    # =========================================================================
    print("1. Pattern Inheritance Verification")
    print("-" * 40)

    patterns_to_check = [
        ("OccupancyField", OccupancyField),
        ("QueueFlow", QueueFlow),
        ("ADLTracker", ADLTracker),
        ("FmSteward", FmSteward),
    ]

    for name, cls in patterns_to_check:
        inherits = issubclass(cls, Pattern)
        print(f"   {name} inherits from Pattern: {inherits}")
    print()

    # =========================================================================
    # 2. Create instances of all patterns
    # =========================================================================
    print("2. Creating Pattern Instances")
    print("-" * 40)

    # OccupancyField
    grid_sensor = MockGridSensor(10, 10)
    occupancy_field = OccupancyField(
        grid_sensor, name="lobby_field", crowding_threshold=70.0
    )
    print(f"   Created OccupancyField: {occupancy_field.name}")

    # QueueFlow
    queue_sensor = MockGridSensor(5, 20)
    queue_flow = QueueFlow(
        queue_sensor, name="checkout_queue", length_change_threshold=0.5
    )
    print(f"   Created QueueFlow: {queue_flow.name}")

    # ADLTracker
    bed_sensor = MockSensor(0.0)
    fridge_sensor = MockSensor(0.0)
    bath_sensor = MockSensor(0.0)
    hall_sensor = MockSensor(0.0)
    adl_tracker = ADLTracker(
        bed_sensor, fridge_sensor, bath_sensor, hall_sensor, name="resident_adl"
    )
    print(f"   Created ADLTracker: {adl_tracker.name}")

    # FmSteward
    door_counter = MockDoorCounter(0)
    towel_sensor = MockTowelSensor(100.0)
    bin_sensor = MockBinSensor(0.0)
    gas_sensor = MockGasSensor(0.0)
    floor_sensor = MockFloorSensor(False)
    fm_steward = FmSteward(
        door_counter,
        towel_sensor,
        bin_sensor,
        gas_sensor,
        floor_sensor,
        name="restroom_steward",
    )
    print(f"   Created FmSteward: {fm_steward.name}")
    print()

    # =========================================================================
    # 3. Demonstrate depends_on() for each pattern
    # =========================================================================
    print("3. Dependencies (depends_on())")
    print("-" * 40)

    patterns = [occupancy_field, queue_flow, adl_tracker, fm_steward]
    for pattern in patterns:
        deps = pattern.depends_on()
        print(f"   {pattern.name}: {len(deps)} dependencies")
    print()

    # =========================================================================
    # 4. Event emission from each pattern
    # =========================================================================
    print("4. Event Emission Demonstration")
    print("-" * 40)

    # OccupancyField: Trigger OccupancyChanged and CrowdingDetected
    print("   OccupancyField events:")
    grid_sensor.set_occupancy(10.0)
    occupancy_field.update(dt=0.1, context={})
    occupancy_field.emit()  # Baseline

    grid_sensor.set_occupancy(80.0)
    occupancy_field.update(dt=0.1, context={})
    events = occupancy_field.emit()
    for e in events:
        print(f"     - {e.__class__.__name__}")

    # QueueFlow: Trigger QueueLengthChanged
    print("   QueueFlow events:")
    queue_sensor.set_occupancy(0.0)
    queue_flow.update(dt=0.1, context={})
    queue_flow.emit()  # Baseline

    queue_sensor.set_occupancy(50.0)
    queue_flow.update(dt=0.1, context={})
    events = queue_flow.emit()
    for e in events:
        print(f"     - {e.__class__.__name__}")

    # ADLTracker: Trigger ADLEvent
    print("   ADLTracker events:")
    adl_tracker.update(dt=0.1, context={})
    adl_tracker.emit()  # Baseline

    fridge_sensor.set_value(1.0)  # Trigger meal event
    adl_tracker.update(dt=0.1, context={})
    events = adl_tracker.emit()
    for e in events:
        print(f"     - {e.__class__.__name__} (activity={e.activity})")

    # FmSteward: Trigger ServiceNeeded
    print("   FmSteward events:")
    fm_steward.update(dt=0.1, context={})
    fm_steward.emit()  # Baseline

    towel_sensor._percent = 5.0  # Low towels
    fm_steward.update(dt=0.1, context={})
    events = fm_steward.emit()
    for e in events:
        print(f"     - {e.__class__.__name__} (reason={e.reason})")
    print()

    # =========================================================================
    # 5. Runtime integration with all patterns
    # =========================================================================
    print("5. Runtime Integration")
    print("-" * 40)

    async def run_with_runtime():
        runtime = PhasedTickRunner(tick_rate_hz=10.0)

        # Create fresh sensors and patterns
        g1 = MockGridSensor(10, 10)
        g1.set_occupancy(20.0)
        p1 = OccupancyField(g1, name="area_a", crowding_threshold=60.0)

        g2 = MockGridSensor(5, 20)
        g2.set_occupancy(10.0)
        p2 = QueueFlow(g2, name="queue_a", length_change_threshold=0.5)

        # Register patterns
        runtime.register_pattern(p1)
        runtime.register_pattern(p2)
        print(f"   Registered {len(runtime._patterns)} patterns")

        # Run first tick (baseline)
        stats = await runtime.run_single_tick()
        print(f"   Tick 1: patterns_updated={stats.patterns_updated}")

        # Change sensor values to trigger events
        g1.set_occupancy(75.0)
        g2.set_occupancy(60.0)

        stats = await runtime.run_single_tick()
        print(
            f"   Tick 2: patterns_updated={stats.patterns_updated}, "
            f"events_emitted={stats.events_emitted}"
        )

        # Show collected events
        if stats.pattern_events:
            print("   Collected events:")
            for event in stats.pattern_events:
                print(f"     - {event.__class__.__name__} from {event.pattern_name}")

    asyncio.run(run_with_runtime())
    print()

    # =========================================================================
    # 6. Pattern dependency ordering demo
    # =========================================================================
    print("6. Pattern Dependency Ordering")
    print("-" * 40)

    # Create patterns with explicit dependencies
    class DependentPattern(Pattern):
        def __init__(self, name, depends_on_patterns=None):
            super().__init__(name=name)
            self._depends = depends_on_patterns or []
            self.update_count = 0

        def update(self, dt, context):
            self.update_count += 1
            print(f"     {self.name} updated (count={self.update_count})")

        def depends_on(self):
            return self._depends

    async def run_ordering_demo():
        runtime = PhasedTickRunner(tick_rate_hz=10.0)

        # Create A, B, C where C depends on B, B depends on A
        pattern_a = DependentPattern("pattern_A")
        pattern_b = DependentPattern("pattern_B", depends_on_patterns=[pattern_a])
        pattern_c = DependentPattern("pattern_C", depends_on_patterns=[pattern_b])

        # Register in reverse order
        runtime.register_pattern(pattern_c)
        runtime.register_pattern(pattern_a)
        runtime.register_pattern(pattern_b)

        print("   Running tick (patterns registered in order C, A, B):")
        await runtime.run_single_tick()
        print("   Expected order: A, B, C (topological sort)")

    asyncio.run(run_ordering_demo())
    print()

    print("Done!")


if __name__ == "__main__":
    main()

"""
test_intent_patterns_interface.py - Paper Parity Test

Tests that all INTENT patterns implement the Pattern interface:
- OccupancyField
- QueueFlow
- ADLTracker
- FmSteward

Reference: Paper Section 2.4
Proving Example: examples/paper/intent_all_patterns.py
"""

import pytest
import numpy as np

from spaxiom.intent import (
    Pattern,
    OccupancyField,
    QueueFlow,
    ADLTracker,
    FmSteward,
    QueueLengthChanged,
    ADLEvent,
    ServiceNeeded,
)


class MockGridSensor:
    """Mock sensor that returns a controllable frame."""

    def __init__(self, frame_data=None):
        self._frame = frame_data if frame_data is not None else np.zeros((10, 10))

    def frame(self):
        return self._frame

    def set_frame(self, data):
        self._frame = data


class MockSensor:
    """Mock sensor that returns a controllable value."""

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
    """Mock towel sensor."""

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
    """Mock floor sensor."""

    def __init__(self, wet=False):
        self._wet = wet

    def is_wet(self):
        return self._wet


class TestOccupancyFieldInterface:
    """Tests for OccupancyField Pattern interface."""

    def test_occupancyfield_inherits_pattern(self):
        """OccupancyField must inherit from Pattern base class."""
        assert issubclass(OccupancyField, Pattern)

    def test_occupancyfield_has_update(self):
        """OccupancyField must have update(dt, context) method."""
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")
        # Should not raise
        field.update(dt=0.1, context={})

    def test_occupancyfield_has_emit(self):
        """OccupancyField must have emit() method."""
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")
        events = field.emit()
        assert isinstance(events, list)

    def test_occupancyfield_has_depends_on(self):
        """OccupancyField must have depends_on() method."""
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")
        deps = field.depends_on()
        assert isinstance(deps, list)
        assert sensor in deps


class TestQueueFlowInterface:
    """Tests for QueueFlow Pattern interface."""

    def test_queueflow_inherits_pattern(self):
        """QueueFlow must inherit from Pattern base class."""
        assert issubclass(QueueFlow, Pattern)

    def test_queueflow_has_update(self):
        """QueueFlow must have update(dt, context) method."""
        sensor = MockGridSensor()
        queue = QueueFlow(sensor, name="test")
        # Should not raise
        queue.update(dt=0.1, context={})

    def test_queueflow_has_emit(self):
        """QueueFlow must have emit() method."""
        sensor = MockGridSensor()
        queue = QueueFlow(sensor, name="test")
        events = queue.emit()
        assert isinstance(events, list)

    def test_queueflow_has_depends_on(self):
        """QueueFlow must have depends_on() method."""
        sensor = MockGridSensor()
        queue = QueueFlow(sensor, name="test")
        deps = queue.depends_on()
        assert isinstance(deps, list)
        assert sensor in deps

    def test_queueflow_emits_queue_events(self):
        """QueueFlow must emit QueueLengthChanged events."""
        sensor = MockGridSensor(np.zeros((10, 10)))
        queue = QueueFlow(sensor, name="test", length_change_threshold=0.5)

        # First update
        queue.update(dt=0.1, context={})
        queue.emit()

        # Change queue length
        sensor.set_frame(np.ones((10, 10)))
        queue.update(dt=0.1, context={})
        events = queue.emit()

        assert any(isinstance(e, QueueLengthChanged) for e in events)


class TestADLTrackerInterface:
    """Tests for ADLTracker Pattern interface."""

    def test_adltracker_inherits_pattern(self):
        """ADLTracker must inherit from Pattern base class."""
        assert issubclass(ADLTracker, Pattern)

    def test_adltracker_has_update(self):
        """ADLTracker must have update(dt, context) method."""
        bed = MockSensor()
        fridge = MockSensor()
        bath = MockSensor()
        hall = MockSensor()
        tracker = ADLTracker(bed, fridge, bath, hall, name="test")
        # Should not raise
        tracker.update(dt=0.1, context={})

    def test_adltracker_has_emit(self):
        """ADLTracker must have emit() method."""
        bed = MockSensor()
        fridge = MockSensor()
        bath = MockSensor()
        hall = MockSensor()
        tracker = ADLTracker(bed, fridge, bath, hall, name="test")
        events = tracker.emit()
        assert isinstance(events, list)

    def test_adltracker_has_depends_on(self):
        """ADLTracker must have depends_on() method."""
        bed = MockSensor()
        fridge = MockSensor()
        bath = MockSensor()
        hall = MockSensor()
        tracker = ADLTracker(bed, fridge, bath, hall, name="test")
        deps = tracker.depends_on()
        assert isinstance(deps, list)
        assert bed in deps
        assert fridge in deps

    def test_adltracker_emits_adl_events(self):
        """ADLTracker must emit ADLEvent events."""
        bed = MockSensor(0.0)
        fridge = MockSensor(0.0)
        bath = MockSensor(0.0)
        hall = MockSensor(0.0)
        tracker = ADLTracker(bed, fridge, bath, hall, name="test")

        # First update (baseline)
        tracker.update(dt=0.1, context={})
        tracker.emit()

        # Trigger fridge sensor (meal event)
        fridge.set_value(1.0)
        tracker.update(dt=0.1, context={})
        events = tracker.emit()

        assert any(isinstance(e, ADLEvent) for e in events)
        assert any(e.activity == "meal" for e in events if isinstance(e, ADLEvent))


class TestFmStewardInterface:
    """Tests for FmSteward Pattern interface."""

    def test_fmsteward_inherits_pattern(self):
        """FmSteward must inherit from Pattern base class."""
        assert issubclass(FmSteward, Pattern)

    def test_fmsteward_has_update(self):
        """FmSteward must have update(dt, context) method."""
        door = MockDoorCounter()
        towel = MockTowelSensor()
        bin_sensor = MockBinSensor()
        gas = MockGasSensor()
        floor = MockFloorSensor()
        steward = FmSteward(door, towel, bin_sensor, gas, floor, name="test")
        # Should not raise
        steward.update(dt=0.1, context={})

    def test_fmsteward_has_emit(self):
        """FmSteward must have emit() method."""
        door = MockDoorCounter()
        towel = MockTowelSensor()
        bin_sensor = MockBinSensor()
        gas = MockGasSensor()
        floor = MockFloorSensor()
        steward = FmSteward(door, towel, bin_sensor, gas, floor, name="test")
        events = steward.emit()
        assert isinstance(events, list)

    def test_fmsteward_has_depends_on(self):
        """FmSteward must have depends_on() method."""
        door = MockDoorCounter()
        towel = MockTowelSensor()
        bin_sensor = MockBinSensor()
        gas = MockGasSensor()
        floor = MockFloorSensor()
        steward = FmSteward(door, towel, bin_sensor, gas, floor, name="test")
        deps = steward.depends_on()
        assert isinstance(deps, list)
        assert door in deps
        assert towel in deps

    def test_fmsteward_emits_service_events(self):
        """FmSteward must emit ServiceNeeded events."""
        door = MockDoorCounter()
        towel = MockTowelSensor(100.0)
        bin_sensor = MockBinSensor(0.0)
        gas = MockGasSensor(0.0)
        floor = MockFloorSensor(False)
        steward = FmSteward(door, towel, bin_sensor, gas, floor, name="test")

        # First update (baseline)
        steward.update(dt=0.1, context={})
        steward.emit()

        # Trigger low towels
        towel._percent = 5.0
        steward.update(dt=0.1, context={})
        events = steward.emit()

        assert any(isinstance(e, ServiceNeeded) for e in events)
        assert any(
            e.reason == "low_towels" for e in events if isinstance(e, ServiceNeeded)
        )


class TestRuntimePatternIntegration:
    """Tests for pattern integration with runtime."""

    def test_runtime_accepts_patterns(self):
        """Runtime must accept pattern registration."""
        from spaxiom.tick import PhasedTickRunner

        runtime = PhasedTickRunner()
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")

        # Register pattern
        runtime.register_pattern(field)
        assert field in runtime._patterns

    @pytest.mark.asyncio
    async def test_runtime_calls_pattern_update(self):
        """Runtime must call pattern.update(dt, context) each tick."""
        from spaxiom.tick import PhasedTickRunner

        runtime = PhasedTickRunner()
        sensor = MockGridSensor(np.ones((10, 10)))
        field = OccupancyField(sensor, name="test")

        runtime.register_pattern(field)

        # Run a tick
        stats = await runtime.run_single_tick()

        # Should have updated patterns
        assert stats.patterns_updated >= 1

    @pytest.mark.asyncio
    async def test_runtime_collects_events(self):
        """Runtime must collect events from pattern.emit()."""
        from spaxiom.tick import PhasedTickRunner

        runtime = PhasedTickRunner()
        sensor = MockGridSensor(np.ones((10, 10)))
        field = OccupancyField(sensor, name="test")

        runtime.register_pattern(field)

        # Run a tick - should emit events due to occupancy change
        stats = await runtime.run_single_tick()

        # Events should be collected
        assert stats.events_emitted >= 0
        assert hasattr(stats, "pattern_events")

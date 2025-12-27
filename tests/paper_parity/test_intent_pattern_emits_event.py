"""
test_intent_pattern_emits_event.py - Paper Parity Test

Tests INTENT pattern event emission:
- Pattern base class with update(dt, context), emit(), depends_on()
- Typed event objects with to_dict()
- Deterministic event emission

Reference: Paper Section 2.4 and Section 3
Proving Example: examples/paper/intent_occupancyfield.py
"""

import numpy as np

from spaxiom.intent import (
    Pattern,
    OccupancyChanged,
    CrowdingDetected,
    QueueLengthChanged,
    ADLEvent,
    ServiceNeeded,
    OccupancyField,
)


class MockGridSensor:
    """Mock sensor that returns a controllable frame."""

    def __init__(self, frame_data=None):
        self._frame = frame_data if frame_data is not None else np.zeros((10, 10))

    def frame(self):
        return self._frame

    def set_frame(self, data):
        self._frame = data


class TestPatternBaseClass:
    """Tests for Pattern base class."""

    def test_pattern_base_class_exists(self):
        """Pattern base class must exist."""
        assert Pattern is not None
        from abc import ABC

        assert issubclass(Pattern, ABC)

    def test_pattern_has_update_method(self):
        """Pattern must have update(dt, context) method."""
        assert hasattr(Pattern, "update")
        import inspect

        sig = inspect.signature(Pattern.update)
        params = list(sig.parameters.keys())
        assert "dt" in params
        assert "context" in params

    def test_pattern_has_emit_method(self):
        """Pattern must have emit() method returning list of events."""
        assert hasattr(Pattern, "emit")
        # Create a concrete implementation to test
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")
        events = field.emit()
        assert isinstance(events, list)

    def test_pattern_has_depends_on_method(self):
        """Pattern must have depends_on() method returning dependencies."""
        assert hasattr(Pattern, "depends_on")
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="test")
        deps = field.depends_on()
        assert isinstance(deps, list)

    def test_pattern_has_name_property(self):
        """Pattern must have name property."""
        sensor = MockGridSensor()
        field = OccupancyField(sensor, name="lobby_field")
        assert field.name == "lobby_field"


class TestTypedEvents:
    """Tests for typed event objects."""

    def test_events_are_typed(self):
        """Emitted events must be typed objects, not plain dicts."""
        event = OccupancyChanged(zone="lobby", percent=45.5)
        assert hasattr(event, "__class__")
        assert event.__class__.__name__ == "OccupancyChanged"

    def test_events_have_to_dict(self):
        """Events must have to_dict() for JSON serialization."""
        event = OccupancyChanged(zone="lobby", percent=45.5)
        d = event.to_dict()
        assert isinstance(d, dict)
        assert "zone" in d
        assert "percent" in d
        assert d["zone"] == "lobby"
        assert d["percent"] == 45.5

    def test_event_serialization_stable(self):
        """Event serialization must be deterministic (same input -> same output)."""
        event = OccupancyChanged(
            zone="lobby", percent=45.5, previous_percent=40.0, hotspots=[]
        )
        d1 = event.to_dict()
        d2 = event.to_dict()
        assert d1 == d2

    def test_all_event_types_exist(self):
        """All typed event classes must exist."""
        assert OccupancyChanged is not None
        assert CrowdingDetected is not None
        assert QueueLengthChanged is not None
        assert ADLEvent is not None
        assert ServiceNeeded is not None

    def test_events_have_event_type_field(self):
        """Events must have event_type field set to class name."""
        event = OccupancyChanged(zone="lobby", percent=45.5)
        assert event.event_type == "OccupancyChanged"

        event2 = ServiceNeeded(facility="restroom", reason="low_towels")
        assert event2.event_type == "ServiceNeeded"


class TestOccupancyFieldPattern:
    """Tests for OccupancyField pattern integration."""

    def test_occupancyfield_inherits_pattern(self):
        """OccupancyField must inherit from Pattern base class."""
        assert issubclass(OccupancyField, Pattern)

    def test_occupancyfield_emits_events(self):
        """OccupancyField.emit() must return OccupancyChanged events."""
        sensor = MockGridSensor(np.zeros((10, 10)))
        field = OccupancyField(sensor, name="test", crowding_threshold=80.0)

        # First update with 0% occupancy
        field.update(dt=0.1, context={})
        events = field.emit()
        # No events initially (0% is baseline)

        # Change occupancy significantly (>5% change threshold)
        sensor.set_frame(np.ones((10, 10)))  # 100% occupancy
        field.update(dt=0.1, context={})
        events = field.emit()

        assert len(events) >= 1
        assert any(isinstance(e, OccupancyChanged) for e in events)

    def test_occupancyfield_emits_crowding_event(self):
        """OccupancyField must emit CrowdingDetected when threshold exceeded."""
        sensor = MockGridSensor(np.zeros((10, 10)))
        field = OccupancyField(sensor, name="test", crowding_threshold=50.0)

        # First update to set baseline
        field.update(dt=0.1, context={})
        field.emit()

        # Change to above threshold
        sensor.set_frame(np.ones((10, 10)))  # 100% occupancy
        field.update(dt=0.1, context={})
        events = field.emit()

        assert any(isinstance(e, CrowdingDetected) for e in events)


class TestEventDeterminism:
    """Tests for deterministic event emission."""

    def test_same_state_same_events(self):
        """Same pattern state must produce same events."""
        sensor = MockGridSensor(np.zeros((10, 10)))
        field1 = OccupancyField(sensor, name="test1")
        field2 = OccupancyField(sensor, name="test2")

        # Set to known state
        test_frame = np.zeros((10, 10))
        test_frame[0:5, 0:5] = 1  # 25% occupancy
        sensor.set_frame(test_frame)

        # Update both fields
        field1.update(dt=0.1, context={})
        field2.update(dt=0.1, context={})

        events1 = field1.emit()
        events2 = field2.emit()

        # Both should have same number of events
        assert len(events1) == len(events2)

        # Event types should match
        if events1 and events2:
            for e1, e2 in zip(events1, events2):
                assert e1.__class__ == e2.__class__
                # Same percent value
                if hasattr(e1, "percent"):
                    assert e1.percent == e2.percent

    def test_emit_clears_pending_events(self):
        """After emit(), pending events should be cleared."""
        sensor = MockGridSensor(np.ones((10, 10)))  # 100% occupancy
        field = OccupancyField(sensor, name="test")

        field.update(dt=0.1, context={})
        _ = field.emit()  # First emit clears pending events

        # Second emit without update should return empty
        events2 = field.emit()
        assert len(events2) == 0

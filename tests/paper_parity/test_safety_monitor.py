"""
test_safety_monitor.py - Paper Parity Test

Tests SafetyMonitor runtime component:
- SafetyMonitor class
- Violation detection and callback
- Structured audit records

Reference: Paper Section 7.3 "Runtime monitoring and enforcement"
Proving Example: examples/paper/safety_export_uppaal.py
"""

import pytest

# Skip entire module if spaxiom.safety not yet implemented (Step 5)
pytest.importorskip("spaxiom.safety", reason="Requires Step 5: safety module")

from spaxiom.safety import (
    SafetyMonitor,
    SafetyViolation,
    compare,
    verifiable,
)


class TestSafetyMonitorClass:
    """Tests for SafetyMonitor class."""

    def test_safety_monitor_exists(self):
        """SafetyMonitor class must exist."""
        assert SafetyMonitor is not None

    def test_safety_monitor_constructor(self):
        """SafetyMonitor must accept name, property, on_violation."""
        cond = verifiable(compare("temp", "<", 100), "temp_ok")

        callback_called = []

        def on_violation(v):
            callback_called.append(v)

        monitor = SafetyMonitor(
            name="temp_monitor",
            property=cond,
            on_violation=on_violation,
        )

        assert monitor.name == "temp_monitor"
        assert monitor is not None

    def test_safety_monitor_with_callable(self):
        """SafetyMonitor can use simple callable as property."""
        value = [True]

        def check_value():
            return value[0]

        monitor = SafetyMonitor(
            name="value_monitor",
            property=check_value,
        )

        # Should be safe
        assert monitor.check() is True


class TestViolationDetection:
    """Tests for safety violation detection."""

    def test_monitor_detects_violation(self):
        """Monitor must detect when safety property becomes false."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        monitor = SafetyMonitor(name="temp_monitor", property=cond)

        # Safe state
        result = monitor.check({"temp": 50})
        assert result is True
        assert len(monitor.violations) == 0

        # Violation state
        result = monitor.check({"temp": 150})
        assert result is False
        assert len(monitor.violations) == 1

    def test_violation_triggers_callback(self):
        """Violation must trigger the on_violation callback."""
        cond = verifiable(compare("pressure", "<", 50), "pressure_safe")

        callbacks_received = []

        def on_violation(v):
            callbacks_received.append(v)

        monitor = SafetyMonitor(
            name="pressure_monitor",
            property=cond,
            on_violation=on_violation,
        )

        # Safe
        monitor.check({"pressure": 30})
        assert len(callbacks_received) == 0

        # Violation
        monitor.check({"pressure": 80})
        assert len(callbacks_received) == 1
        assert isinstance(callbacks_received[0], SafetyViolation)

    def test_violation_only_on_transition(self):
        """Violation callback only fires on transition to violated state."""
        cond = verifiable(compare("x", ">", 0), "x_positive")
        callbacks = []

        monitor = SafetyMonitor(
            name="x_monitor",
            property=cond,
            on_violation=lambda v: callbacks.append(v),
        )

        # Safe
        monitor.check({"x": 10})
        assert len(callbacks) == 0

        # Violation
        monitor.check({"x": -5})
        assert len(callbacks) == 1

        # Still violated - no new callback
        monitor.check({"x": -10})
        assert len(callbacks) == 1

        # Back to safe
        monitor.check({"x": 5})
        assert len(callbacks) == 1

        # Violation again - new callback
        monitor.check({"x": -1})
        assert len(callbacks) == 2


class TestAuditRecords:
    """Tests for structured audit records."""

    def test_violation_generates_audit_record(self):
        """Violation must generate structured audit record."""
        cond = verifiable(compare("speed", "<", 100), "speed_safe")
        monitor = SafetyMonitor(name="speed_monitor", property=cond)

        # Trigger violation
        monitor.check({"speed": 50})  # Safe first
        monitor.check({"speed": 150})  # Violation

        records = monitor.get_audit_records()
        assert len(records) == 1
        assert isinstance(records[0], dict)

    def test_audit_record_schema(self):
        """Audit records must have defined schema."""
        cond = verifiable(compare("level", ">", 0), "level_ok")
        monitor = SafetyMonitor(name="level_monitor", property=cond)

        # Trigger violation
        monitor.check({"level": 10})
        monitor.check({"level": -5})

        records = monitor.get_audit_records()
        assert len(records) == 1

        record = records[0]
        # Required fields
        assert "timestamp" in record
        assert "monitor_name" in record
        assert "property_name" in record
        assert "state" in record
        assert "message" in record

        assert record["monitor_name"] == "level_monitor"
        assert record["state"] == "violated"

    def test_safety_violation_to_dict(self):
        """SafetyViolation has to_dict() method."""
        violation = SafetyViolation(
            monitor_name="test",
            property_name="prop",
            state="violated",
        )
        d = violation.to_dict()
        assert isinstance(d, dict)
        assert d["monitor_name"] == "test"


class TestSafetyMonitorRuntimeIntegration:
    """Tests for SafetyMonitor integration with runtime."""

    def test_runtime_accepts_safety_monitor(self):
        """Runtime must accept SafetyMonitor registration."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()
        cond = verifiable(compare("x", ">", 0), "x_ok")
        monitor = SafetyMonitor(name="x_monitor", property=cond)

        runner.register_safety_monitor(monitor)
        assert monitor in runner._safety_monitors

    @pytest.mark.asyncio
    async def test_runtime_checks_monitors(self):
        """Runtime must check all safety monitors each tick."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()

        check_count = [0]

        def counting_check():
            check_count[0] += 1
            return True

        monitor = SafetyMonitor(name="counter", property=counting_check)
        runner.register_safety_monitor(monitor)

        # Run a tick
        await runner.run_single_tick()
        assert check_count[0] >= 1

    @pytest.mark.asyncio
    async def test_runtime_reports_violations(self):
        """Runtime stats include violation info."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()

        # Property that always fails
        def always_fails():
            return False

        monitor = SafetyMonitor(name="failing", property=always_fails)
        runner.register_safety_monitor(monitor)

        stats = await runner.run_single_tick()
        assert stats.safety_monitors_checked == 1
        assert stats.safety_violations == 1

    def test_monitor_has_compile_to_uppaal(self):
        """SafetyMonitor must have compile_to_uppaal() method."""
        cond = verifiable(compare("val", "<", 50), "val_safe")
        monitor = SafetyMonitor(name="val_monitor", property=cond)

        assert hasattr(monitor, "compile_to_uppaal")

        automaton = monitor.compile_to_uppaal()
        assert automaton is not None

    def test_compile_to_uppaal_requires_verifiable(self):
        """compile_to_uppaal() requires VerifiableCondition."""

        # With regular callable, should raise
        def simple_check():
            return True

        monitor = SafetyMonitor(name="simple", property=simple_check)

        with pytest.raises(TypeError):
            monitor.compile_to_uppaal()


class TestMonitorReset:
    """Tests for monitor reset functionality."""

    def test_reset_clears_violations(self):
        """reset() clears recorded violations."""
        cond = verifiable(compare("x", ">", 0), "x_ok")
        monitor = SafetyMonitor(name="x_monitor", property=cond)

        # Trigger violation
        monitor.check({"x": 10})
        monitor.check({"x": -5})
        assert len(monitor.violations) == 1

        # Reset
        monitor.reset()
        assert len(monitor.violations) == 0
        assert monitor.check_count == 0

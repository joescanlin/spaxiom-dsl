"""
test_runtime_tick_ordering.py - Paper Parity Test

Tests deterministic 4-phase tick execution:
1. Sensor reads (concurrent)
2. Pattern updates (dependency-ordered)
3. Condition evaluation
4. Callback dispatch (concurrent, isolated)

Reference: Paper Section 2.5 "Runtime Architecture and Execution Model"
Proving Example: examples/paper/runtime_tick_phases.py
"""

import asyncio
import time

import pytest

from spaxiom import RandomSensor, Condition, SensorRegistry, PhasedTickRunner
from spaxiom.events import EVENT_HANDLERS


@pytest.fixture(autouse=True)
def clean_state():
    """Clear sensor registry and event handlers before and after each test."""
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    yield
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()


class TestPhasedTickExecution:
    """Tests for deterministic phased tick execution model."""

    def test_tick_has_four_phases(self):
        """Each tick must execute exactly 4 phases in order."""
        # Create a runner
        runner = PhasedTickRunner(tick_rate_hz=10.0)

        # Create a sensor so there's something to read
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Run one tick
        stats = asyncio.run(runner.run_single_tick())

        # Assert phases executed in correct order
        assert stats.phase_order == [
            "sensor_read",
            "pattern_update",
            "condition_eval",
            "callback_dispatch",
        ]

    def test_phase1_sensor_reads_concurrent(self):
        """Phase 1 must read all sensors concurrently using asyncio.gather()."""
        # Create 3 sensors
        for i in range(3):
            RandomSensor(name=f"sensor_{i}", location=(i, 0, 0))

        runner = PhasedTickRunner(tick_rate_hz=10.0)

        # Run one tick
        stats = asyncio.run(runner.run_single_tick())

        # Assert all 3 sensors were read
        assert stats.sensors_read == 3

    @pytest.mark.skip(reason="MISSING: Phase 2 pattern updates in dependency order")
    def test_phase2_patterns_dependency_ordered(self):
        """Phase 2 must update patterns in topological order based on depends_on()."""
        # When implemented:
        # 1. Create patterns A, B, C where C depends on B, B depends on A
        # 2. Instrument update() calls
        # 3. Run one tick
        # 4. Assert update order: A, B, C
        pass

    def test_phase3_conditions_after_patterns(self):
        """Phase 3 must evaluate conditions only after all pattern updates complete."""
        # Create a sensor and condition
        sensor = RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Track when condition is evaluated
        eval_times = []

        def track_eval():
            eval_times.append(time.perf_counter())
            return sensor.read() > 0.5

        condition = Condition(track_eval)

        # Register handler
        from spaxiom.events import on

        @on(condition)
        def handler():
            pass

        runner = PhasedTickRunner(tick_rate_hz=10.0)

        # Run one tick
        stats = asyncio.run(runner.run_single_tick())

        # Condition was evaluated
        assert stats.conditions_evaluated >= 1

        # Phase order proves condition_eval comes after pattern_update
        assert stats.phase_order.index("condition_eval") > stats.phase_order.index(
            "pattern_update"
        )

    @pytest.mark.skip(reason="MISSING: Phase 4 batched concurrent callback dispatch")
    def test_phase4_callbacks_concurrent_isolated(self):
        """Phase 4 must dispatch callbacks concurrently with exception isolation."""
        # When implemented:
        # 1. Create condition with 3 callbacks, one throws exception
        # 2. Run tick where condition becomes true
        # 3. Assert all 3 callbacks attempted, exception logged but not propagated
        pass

    def test_deterministic_ordering_across_ticks(self):
        """Phase ordering must be deterministic across multiple ticks."""
        # Create sensors
        for i in range(2):
            RandomSensor(name=f"sensor_{i}", location=(i, 0, 0))

        runner = PhasedTickRunner(tick_rate_hz=100.0)

        # Run multiple ticks and collect phase orders
        async def run_ticks():
            orders = []
            for _ in range(10):
                stats = await runner.run_single_tick()
                orders.append(stats.phase_order)
            return orders

        orders = asyncio.run(run_ticks())

        # Assert phase order identical for every tick
        expected_order = [
            "sensor_read",
            "pattern_update",
            "condition_eval",
            "callback_dispatch",
        ]
        for order in orders:
            assert order == expected_order


class TestTickRate:
    """Tests for configurable tick rate."""

    def test_configurable_tick_rate(self):
        """Runtime must accept tick_rate in Hz."""
        runner = PhasedTickRunner(tick_rate_hz=10.0)
        assert runner.tick_rate_hz == 10.0
        assert runner.tick_period_s == 0.1

        runner2 = PhasedTickRunner(tick_rate_hz=20.0)
        assert runner2.tick_rate_hz == 20.0
        assert runner2.tick_period_s == 0.05

    @pytest.mark.skip(reason="MISSING: Tick timing enforcement")
    def test_tick_timing_enforced(self):
        """Ticks must occur at configured rate +/- tolerance."""
        # When implemented:
        # 1. Create runtime with tick_rate=10.0
        # 2. Record tick timestamps
        # 3. Assert intervals are 100ms +/- 10ms
        pass

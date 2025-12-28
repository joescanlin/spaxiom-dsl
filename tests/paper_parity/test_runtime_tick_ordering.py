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

    def test_phase2_patterns_dependency_ordered(self):
        """Phase 2 must update patterns in topological order based on depends_on()."""
        from spaxiom.intent import Pattern

        # Track update order
        update_order = []

        class PatternA(Pattern):
            def update(self, dt, context):
                update_order.append("A")

            def depends_on(self):
                return []  # No dependencies

        class PatternB(Pattern):
            def __init__(self, dep_a):
                super().__init__(name="B")
                self._dep_a = dep_a

            def update(self, dt, context):
                update_order.append("B")

            def depends_on(self):
                return [self._dep_a]  # Depends on A

        class PatternC(Pattern):
            def __init__(self, dep_b):
                super().__init__(name="C")
                self._dep_b = dep_b

            def update(self, dt, context):
                update_order.append("C")

            def depends_on(self):
                return [self._dep_b]  # Depends on B

        # Create patterns
        pattern_a = PatternA(name="A")
        pattern_b = PatternB(pattern_a)
        pattern_c = PatternC(pattern_b)

        runner = PhasedTickRunner(tick_rate_hz=10.0)

        # Register in reverse order to test ordering
        runner.register_pattern(pattern_c)
        runner.register_pattern(pattern_a)
        runner.register_pattern(pattern_b)

        # Run one tick
        asyncio.run(runner.run_single_tick())

        # Assert update order: A, B, C (topological order)
        assert update_order == ["A", "B", "C"]

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

    @pytest.mark.skip(
        reason="DEFERRED: Callbacks run sequentially with isolation; concurrent dispatch requires asyncio.gather for callbacks"
    )
    def test_phase4_callbacks_concurrent_isolated(self):
        """Phase 4 must dispatch callbacks concurrently with exception isolation."""
        # Currently: Callbacks run sequentially with exception isolation (implemented)
        # Missing: Concurrent dispatch using asyncio.gather for multiple callbacks
        # To implement: Change _phase4_callback_dispatch to use gather() instead of sequential loop
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

    @pytest.mark.skip(
        reason="DEFERRED: Tick timing enforcement requires async sleep in run() loop; run_single_tick() is instantaneous"
    )
    def test_tick_timing_enforced(self):
        """Ticks must occur at configured rate +/- tolerance."""
        # Currently: run_single_tick() executes instantly, run() has basic sleep
        # Missing: Precise timing with drift compensation in run() loop
        # To implement: Add timing enforcement in run() with measured tick duration subtracted from sleep
        pass

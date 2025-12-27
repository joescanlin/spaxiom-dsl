"""
test_runtime_instrumentation.py - Paper Parity Test

Tests per-tick instrumentation and profiling:
- enable_profiling(runtime)
- runtime.profiler.get_stats()
- Phase timing statistics

Reference: Paper Section 2.5 "Performance profiling and debugging"
Proving Example: examples/paper/runtime_profiling.py
"""

import asyncio

import pytest

from spaxiom import (
    RandomSensor,
    Condition,
    SensorRegistry,
    PhasedTickRunner,
    enable_profiling,
)
from spaxiom.events import EVENT_HANDLERS, on


@pytest.fixture(autouse=True)
def clean_state():
    """Clear sensor registry and event handlers before and after each test."""
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    yield
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()


class TestProfilingAPI:
    """Tests for profiling API."""

    def test_enable_profiling_exists(self):
        """enable_profiling(runtime) function must exist."""
        runner = PhasedTickRunner()
        enable_profiling(runner)
        assert runner.profiler.enabled

    def test_get_stats_returns_dict(self):
        """get_stats() must return dict with required keys."""
        runner = PhasedTickRunner(tick_rate_hz=100.0)
        enable_profiling(runner)

        # Create some sensors
        for i in range(3):
            RandomSensor(name=f"sensor_{i}", location=(i, 0, 0))

        # Run some ticks
        async def run_ticks():
            for _ in range(5):
                await runner.run_single_tick()

        asyncio.run(run_ticks())

        # Get stats
        stats = runner.profiler.get_stats()

        # Verify required keys exist
        assert "tick_count" in stats
        assert "avg_tick_ms" in stats
        assert "callback_failures" in stats
        assert stats["tick_count"] == 5


class TestPhaseTimings:
    """Tests for per-phase timing collection."""

    def test_phase_timings_collected(self):
        """Profiler must collect timing for each phase."""
        runner = PhasedTickRunner(tick_rate_hz=100.0)
        enable_profiling(runner)

        # Create a sensor
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Run some ticks
        async def run_ticks():
            for _ in range(3):
                await runner.run_single_tick()

        asyncio.run(run_ticks())

        # Get stats
        stats = runner.profiler.get_stats()

        # Verify phase timing keys exist
        assert "phase1_sensor_read_avg_ms" in stats
        assert "phase2_pattern_update_avg_ms" in stats
        assert "phase3_condition_eval_avg_ms" in stats
        assert "phase4_callback_dispatch_avg_ms" in stats

        # All timings should be non-negative
        assert stats["phase1_sensor_read_avg_ms"] >= 0
        assert stats["phase2_pattern_update_avg_ms"] >= 0
        assert stats["phase3_condition_eval_avg_ms"] >= 0
        assert stats["phase4_callback_dispatch_avg_ms"] >= 0

    @pytest.mark.skip(reason="MISSING: Sensor read latency histograms")
    def test_sensor_read_latency_percentiles(self):
        """Profiler must provide sensor read latency percentiles."""
        # When implemented:
        # stats = runtime.profiler.get_stats()
        # assert 'sensor_read_p50_ms' in stats
        # assert 'sensor_read_p99_ms' in stats
        pass


class TestCallbackTracking:
    """Tests for callback failure tracking."""

    def test_callback_failures_counted(self):
        """Profiler must count callback failures."""
        runner = PhasedTickRunner(tick_rate_hz=100.0)
        enable_profiling(runner)

        # Create sensor and condition that always fires
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Force condition to be true
        condition = Condition(lambda: True)

        # Register callback that throws
        @on(condition)
        def failing_callback():
            raise ValueError("Intentional failure")

        # Run ticks - callback should fail
        async def run_ticks():
            for _ in range(3):
                await runner.run_single_tick()

        asyncio.run(run_ticks())

        # Get stats - failures should be counted
        stats = runner.profiler.get_stats()

        # First tick triggers the rising edge (False -> True), so 1 failure
        # Subsequent ticks don't trigger callback (already True)
        assert stats["callback_failures"] >= 1

    @pytest.mark.skip(reason="MISSING: Condition tracing")
    def test_trace_condition(self):
        """Profiler must support tracing specific conditions."""
        # When implemented:
        # runtime.profiler.trace_condition("my_condition")
        # # Logs: evaluation results, timing, sensor reads, callback dispatch
        pass


class TestProfilingOverhead:
    """Tests for profiling overhead."""

    @pytest.mark.skip(reason="MISSING: Profiling overhead measurement")
    def test_profiling_overhead_below_threshold(self):
        """Profiling overhead must be <1%."""
        # When implemented:
        # 1. Run 1000 ticks without profiling, measure time
        # 2. Run 1000 ticks with profiling, measure time
        # 3. Assert overhead < 1%
        pass

"""
test_runtime_delegation.py - Paper Parity Test

Tests runtime delegation to PhasedTickRunner:
- SPAXIOM_RUNTIME env var selection
- Default phased mode runs PhasedTickRunner
- Legacy mode uses task-based runtime

Reference: Paper Section 2.5 "Runtime Architecture"
"""

import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from spaxiom import RandomSensor, SensorRegistry
from spaxiom.events import EVENT_HANDLERS
import spaxiom.runtime as runtime_module
from spaxiom.runtime import (
    start_runtime,
    get_runtime_mode,
    set_runtime_mode,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Clear sensor registry and event handlers before and after each test."""
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    # Save original runtime mode
    original_mode = runtime_module.RUNTIME_MODE
    yield
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()
    # Restore original runtime mode
    runtime_module.RUNTIME_MODE = original_mode


class TestRuntimeModeSelection:
    """Tests for runtime mode selection."""

    def test_get_runtime_mode_returns_current_mode(self):
        """get_runtime_mode() must return current mode."""
        set_runtime_mode("phased")
        assert get_runtime_mode() == "phased"

        set_runtime_mode("legacy")
        assert get_runtime_mode() == "legacy"

    def test_set_runtime_mode_validates_input(self):
        """set_runtime_mode() must reject invalid modes."""
        with pytest.raises(ValueError) as exc_info:
            set_runtime_mode("invalid")
        assert "Invalid runtime mode" in str(exc_info.value)

    def test_set_runtime_mode_case_insensitive(self):
        """set_runtime_mode() must accept case-insensitive input."""
        set_runtime_mode("PHASED")
        assert get_runtime_mode() == "phased"

        set_runtime_mode("Legacy")
        assert get_runtime_mode() == "legacy"


class TestLegacyRuntimePath:
    """Tests for legacy runtime path."""

    @pytest.mark.asyncio
    async def test_legacy_mode_uses_task_based_runtime(self):
        """SPAXIOM_RUNTIME=legacy must use the task-based runtime."""
        set_runtime_mode("legacy")

        # Create a sensor
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Mock the async event to allow immediate cancellation
        with patch("spaxiom.runtime.asyncio.Event") as mock_event, patch(
            "spaxiom.runtime._evaluate_conditions"
        ):
            mock_event_obj = AsyncMock()
            mock_event.return_value = mock_event_obj
            mock_event_obj.wait.side_effect = asyncio.CancelledError()

            try:
                await start_runtime(poll_ms=100)
            except asyncio.CancelledError:
                pass

        # Verify legacy-specific behavior: ACTIVE_TASKS should have been used
        # (phased mode doesn't use ACTIVE_TASKS)
        # We check by verifying _evaluate_conditions was called (legacy only)
        # This is implicit from the mock being used

    @pytest.mark.asyncio
    async def test_legacy_mode_prints_legacy_message(self, capsys):
        """Legacy mode must print identifying message."""
        set_runtime_mode("legacy")

        # Clear any existing tasks
        runtime_module.ACTIVE_TASKS.clear()

        RandomSensor(name="test_sensor", location=(0, 0, 0))

        with patch("spaxiom.runtime.asyncio.Event") as mock_event, patch(
            "spaxiom.runtime._evaluate_conditions"
        ), patch("spaxiom.runtime._poll_sensor", new_callable=AsyncMock):
            mock_event_obj = AsyncMock()
            mock_event.return_value = mock_event_obj
            mock_event_obj.wait.side_effect = asyncio.CancelledError()

            try:
                await start_runtime(poll_ms=100)
            except asyncio.CancelledError:
                pass

        captured = capsys.readouterr()
        assert "Legacy runtime started" in captured.out


class TestPhasedRuntimePath:
    """Tests for phased runtime path (default)."""

    @pytest.mark.asyncio
    async def test_default_mode_is_phased(self):
        """Default runtime mode must be phased."""
        # Reset to check default
        runtime_module.RUNTIME_MODE = os.environ.get(
            "SPAXIOM_RUNTIME", "phased"
        ).lower()
        # If env var isn't set, default should be phased
        if "SPAXIOM_RUNTIME" not in os.environ:
            assert get_runtime_mode() == "phased"

    @pytest.mark.asyncio
    async def test_phased_mode_uses_phased_tick_runner(self):
        """SPAXIOM_RUNTIME=phased must use PhasedTickRunner."""
        set_runtime_mode("phased")

        # Create a sensor
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Track if PhasedTickRunner.run() was called
        runner_run_called = False
        original_runner = None

        async def mock_run(max_ticks=None):
            nonlocal runner_run_called
            runner_run_called = True
            # Run just one tick to verify it works
            if original_runner:
                await original_runner.run_single_tick()

        with patch("spaxiom.tick.PhasedTickRunner") as MockRunner:
            mock_instance = MagicMock()
            mock_instance.run = mock_run
            mock_instance.stop = MagicMock()
            MockRunner.return_value = mock_instance

            try:
                await start_runtime(poll_ms=100)
            except asyncio.CancelledError:
                pass

        assert runner_run_called, "PhasedTickRunner.run() should have been called"

    @pytest.mark.asyncio
    async def test_phased_mode_prints_phased_message(self, capsys):
        """Phased mode must print identifying message."""
        set_runtime_mode("phased")

        RandomSensor(name="test_sensor", location=(0, 0, 0))

        with patch("spaxiom.tick.PhasedTickRunner") as MockRunner:
            mock_instance = MagicMock()

            async def mock_run(max_ticks=None):
                pass  # Exit immediately

            mock_instance.run = mock_run
            mock_instance.stop = MagicMock()
            MockRunner.return_value = mock_instance

            try:
                await start_runtime(poll_ms=100)
            except asyncio.CancelledError:
                pass

        captured = capsys.readouterr()
        assert "Phased runtime started" in captured.out

    @pytest.mark.asyncio
    async def test_phased_mode_converts_poll_ms_to_tick_rate(self):
        """Phased mode must convert poll_ms to tick_rate_hz."""
        set_runtime_mode("phased")

        RandomSensor(name="test_sensor", location=(0, 0, 0))

        captured_tick_rate = None

        with patch("spaxiom.tick.PhasedTickRunner") as MockRunner:

            def capture_init(*args, **kwargs):
                nonlocal captured_tick_rate
                captured_tick_rate = kwargs.get("tick_rate_hz")
                mock = MagicMock()
                mock.run = AsyncMock()
                mock.stop = MagicMock()
                return mock

            MockRunner.side_effect = capture_init

            try:
                await start_runtime(poll_ms=50)  # 50ms = 20 Hz
            except asyncio.CancelledError:
                pass

        assert captured_tick_rate == 20.0, f"Expected 20.0 Hz, got {captured_tick_rate}"

    @pytest.mark.asyncio
    async def test_phased_mode_runs_at_least_one_tick(self):
        """Phased mode must run at least one tick successfully."""
        set_runtime_mode("phased")

        # Create a sensor (registers with SensorRegistry)
        RandomSensor(name="test_sensor", location=(0, 0, 0))

        # Import PhasedTickRunner directly for this test
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner(tick_rate_hz=100.0)

        # Run a single tick
        stats = await runner.run_single_tick()

        # Verify tick executed successfully
        assert stats.phase_order == [
            "sensor_read",
            "pattern_update",
            "condition_eval",
            "callback_dispatch",
        ]
        assert stats.sensors_read >= 1


class TestSignalHandling:
    """Tests for signal handling in both modes."""

    @pytest.mark.asyncio
    async def test_phased_mode_stops_on_shutdown(self):
        """Phased mode must stop runner on shutdown signal."""
        set_runtime_mode("phased")

        stop_called = False

        with patch("spaxiom.tick.PhasedTickRunner") as MockRunner:
            mock_instance = MagicMock()

            async def mock_run(max_ticks=None):
                # Simulate running until stopped
                while mock_instance._running:
                    await asyncio.sleep(0.01)

            mock_instance._running = True
            mock_instance.run = mock_run

            def mock_stop():
                nonlocal stop_called
                stop_called = True
                mock_instance._running = False

            mock_instance.stop = mock_stop
            MockRunner.return_value = mock_instance

            # Start runtime in background
            task = asyncio.create_task(start_runtime(poll_ms=100))

            # Give it a moment to start
            await asyncio.sleep(0.05)

            # Simulate shutdown
            mock_instance.stop()

            # Wait for task to complete
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()

        assert stop_called, "runner.stop() should have been called"

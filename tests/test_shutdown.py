"""
Tests for the Spaxiom runtime shutdown mechanism.
"""

import asyncio
import pytest
from spaxiom.sensor import RandomSensor
from spaxiom.runtime import start_runtime, shutdown, ACTIVE_TASKS
from spaxiom.core import SensorRegistry


class TestShutdown:
    """Test the shutdown mechanism for the runtime."""

    @pytest.mark.asyncio
    async def test_tasks_cancelled_on_shutdown(self):
        """Test that tasks are cancelled when shutdown is called."""
        # Clear any existing state
        initial_tasks = set(ACTIVE_TASKS)
        for task in initial_tasks:
            if not task.done():
                task.cancel()
        ACTIVE_TASKS.clear()

        # Clear the sensor registry
        SensorRegistry().clear()

        # Create some dummy sensors with different update frequencies
        _ = RandomSensor(  # noqa: F841
            name="sensor1",
            location=(0, 0, 0),
            hz=5.0,
        )

        _ = RandomSensor(  # noqa: F841
            name="sensor2",
            location=(1, 1, 0),
            hz=2.0,
        )

        # Start the runtime in a separate task
        _ = asyncio.create_task(start_runtime(poll_ms=100))

        # Give the runtime a moment to start and initialize all sensor tasks
        await asyncio.sleep(0.5)

        # Store initial count of active tasks
        test_tasks = set(ACTIVE_TASKS)

        # Verify that tasks are running
        assert len(test_tasks) > 0, "No tasks were created"
        for task in test_tasks:
            assert not task.done(), "Task should be running initially"

        # Call shutdown directly
        await shutdown()

        # Wait a moment for tasks to be cancelled
        await asyncio.sleep(0.1)

        # Verify all tasks are done
        for task in test_tasks:
            assert (
                task.done() or task.cancelled()
            ), "Task should be cancelled after shutdown"

    @pytest.mark.asyncio
    async def test_restart_after_shutdown(self):
        """Test that we can restart the runtime after shutdown."""
        # Clear any existing state
        initial_tasks = set(ACTIVE_TASKS)
        for task in initial_tasks:
            if not task.done():
                task.cancel()
        ACTIVE_TASKS.clear()

        # Clear the sensor registry
        SensorRegistry().clear()

        # First Run: Create tasks and run
        _ = RandomSensor(  # noqa: F841
            name="restart_test_sensor",
            location=(2, 2, 0),
            hz=10.0,
        )

        # Start the runtime
        _ = asyncio.create_task(start_runtime(poll_ms=100))

        # Give the runtime a moment to start
        await asyncio.sleep(0.5)

        # Verify that tasks are running
        first_run_tasks = set(ACTIVE_TASKS)
        assert len(first_run_tasks) > 0, "No tasks were created in first run"

        # Shutdown
        await shutdown()

        # Wait a moment for tasks to be cancelled
        await asyncio.sleep(0.1)

        # Verify all tasks are cancelled
        for task in first_run_tasks:
            assert (
                task.done() or task.cancelled()
            ), "Task should be cancelled after first shutdown"

        # Clear task list and reset
        ACTIVE_TASKS.clear()

        # Second Run: Start again after shutdown
        _ = asyncio.create_task(start_runtime(poll_ms=100))

        # Give it time to start
        await asyncio.sleep(0.5)

        # Verify new tasks are running
        second_run_tasks = set(ACTIVE_TASKS) - first_run_tasks
        assert len(second_run_tasks) > 0, "No new tasks were created in second run"
        for task in second_run_tasks:
            assert not task.done(), "New tasks should be running"

        # Shutdown again
        await shutdown()

        # Wait a moment for tasks to be cancelled
        await asyncio.sleep(0.1)

        # Verify all new tasks are cancelled
        for task in second_run_tasks:
            assert (
                task.done() or task.cancelled()
            ), "New tasks should be cancelled after second shutdown"

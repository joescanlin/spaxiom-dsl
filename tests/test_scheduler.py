"""
Tests for the Spaxiom sensor scheduler system.
"""

import asyncio
import pytest
from spaxiom.sensor import RandomSensor
from spaxiom.runtime import _poll_sensor


class TestScheduler:
    """Test the sensor scheduling functionality."""

    @pytest.mark.asyncio
    async def test_sensor_frequency(self):
        """Test that a sensor with hz=5.0 gets polled approximately 5 times per second."""
        # Create a sensor with 5 Hz frequency
        sensor = RandomSensor(
            name="test_sensor",
            location=(0, 0, 0),
            hz=5.0,  # 5 Hz → 0.2s period
        )

        # Keep track of read counts
        read_count = 0

        # Replace the _read_raw method to count calls
        original_read_raw = sensor._read_raw

        def counting_read_raw():
            nonlocal read_count
            read_count += 1
            return original_read_raw()

        sensor._read_raw = counting_read_raw

        # Start polling task - will run for just over 1 second
        poll_task = asyncio.create_task(_poll_sensor(sensor))

        # Wait for 1.1 seconds (slightly longer than 1s to ensure we get a full second of data)
        await asyncio.sleep(1.1)

        # Cancel the task
        poll_task.cancel()

        # Allow task to complete cancellation
        try:
            await poll_task
        except asyncio.CancelledError:
            pass

        # We should have approximately 5 reads
        # Add tolerance for timing variations in test environment
        assert 4 <= read_count <= 6, f"Expected ~5 reads, got {read_count}"


class TestSchedulerIntegration:
    """Test scheduler integration with the runtime."""

    @pytest.mark.asyncio
    async def test_multiple_sensors(self):
        """Test multiple sensors with different frequencies."""
        # Create two sensors with different frequencies
        fast_sensor = RandomSensor(
            name="fast_sensor",
            location=(0, 0, 0),
            hz=10.0,  # 10 Hz → 0.1s period
        )

        slow_sensor = RandomSensor(
            name="slow_sensor",
            location=(0, 0, 0),
            hz=2.0,  # 2 Hz → 0.5s period
        )

        # Keep track of read counts
        fast_count = 0
        slow_count = 0

        # Replace the _read_raw methods to count calls
        original_fast_read = fast_sensor._read_raw
        original_slow_read = slow_sensor._read_raw

        def fast_counting_read():
            nonlocal fast_count
            fast_count += 1
            return original_fast_read()

        def slow_counting_read():
            nonlocal slow_count
            slow_count += 1
            return original_slow_read()

        fast_sensor._read_raw = fast_counting_read
        slow_sensor._read_raw = slow_counting_read

        # Start polling tasks
        fast_task = asyncio.create_task(_poll_sensor(fast_sensor))
        slow_task = asyncio.create_task(_poll_sensor(slow_sensor))

        # Wait for 1.1 seconds
        await asyncio.sleep(1.1)

        # Cancel tasks
        fast_task.cancel()
        slow_task.cancel()

        # Allow tasks to complete cancellation
        try:
            await fast_task
        except asyncio.CancelledError:
            pass

        try:
            await slow_task
        except asyncio.CancelledError:
            pass

        # Verify relative read counts
        # Fast sensor should have ~5 times as many reads as slow sensor
        assert 9 <= fast_count <= 12, f"Expected ~10 fast reads, got {fast_count}"
        assert 1 <= slow_count <= 3, f"Expected ~2 slow reads, got {slow_count}"
        ratio = fast_count / max(1, slow_count)
        assert 3 <= ratio <= 6, f"Expected ratio of ~5, got {ratio}"

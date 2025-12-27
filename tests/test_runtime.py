"""
Tests for the Spaxiom runtime module.
"""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from spaxiom.core import SensorRegistry, Sensor
from spaxiom.condition import Condition
from spaxiom.runtime import (
    format_sensor_value,
    _poll_sensor,
    _evaluate_conditions,
    start_runtime,
    start_blocking,
    shutdown,
    GLOBAL_HISTORY,
    ACTIVE_TASKS,
    PRIVATE_SENSORS_WARNED,
)
import spaxiom.runtime as runtime_module
from spaxiom.events import EVENT_HANDLERS


class MockSensor(Sensor):
    """Mock sensor for testing."""
    
    def __init__(self, name, privacy="public", sample_period_s=0.001, throw_error=False):
        super().__init__(
            name=name,
            sensor_type="mock",
            location=(0, 0, 0),
            privacy=privacy,
            sample_period_s=sample_period_s,
        )
        self.throw_error = throw_error
        self.read_count = 0
        self.value = 0.5
    
    def _read_raw(self):
        """Implement the _read_raw method."""
        self.read_count += 1
        if self.throw_error:
            raise ValueError("Mock sensor error")
        return self.value


@pytest.fixture
def clear_registry():
    """Clear the sensor registry before and after test."""
    SensorRegistry().clear()
    yield
    SensorRegistry().clear()


@pytest.fixture
def clear_event_handlers():
    """Clear the event handlers before and after test."""
    # Store original handlers
    original_handlers = EVENT_HANDLERS.copy()
    # Clear handlers
    EVENT_HANDLERS.clear()
    yield
    # Restore original handlers
    EVENT_HANDLERS.clear()
    EVENT_HANDLERS.extend(original_handlers)


@pytest.fixture
def reset_runtime_state():
    """Reset runtime state variables."""
    # Store original state
    original_global_history = GLOBAL_HISTORY.copy()
    original_active_tasks = ACTIVE_TASKS.copy()
    original_shutdown_initiated = runtime_module.SHUTDOWN_INITIATED
    original_private_sensors_warned = PRIVATE_SENSORS_WARNED.copy()

    # Clear state
    GLOBAL_HISTORY.clear()
    ACTIVE_TASKS.clear()
    runtime_module.SHUTDOWN_INITIATED = False
    PRIVATE_SENSORS_WARNED.clear()

    yield

    # Restore original state
    GLOBAL_HISTORY.clear()
    GLOBAL_HISTORY.extend(original_global_history)
    ACTIVE_TASKS.clear()
    ACTIVE_TASKS.extend(original_active_tasks)
    runtime_module.SHUTDOWN_INITIATED = original_shutdown_initiated
    PRIVATE_SENSORS_WARNED.clear()
    PRIVATE_SENSORS_WARNED.update(original_private_sensors_warned)


def test_format_sensor_value_public():
    """Test formatting values for public sensors."""
    sensor = Sensor(name="test_public", sensor_type="test", location=(0, 0, 0), privacy="public")
    value = 42.5
    
    result = format_sensor_value(sensor, value)
    
    assert result == "42.5"
    assert sensor.name not in PRIVATE_SENSORS_WARNED


def test_format_sensor_value_private():
    """Test formatting values for private sensors."""
    sensor = Sensor(name="test_private", sensor_type="test", location=(0, 0, 0), privacy="private")
    value = 42.5
    
    result = format_sensor_value(sensor, value)
    
    assert result == "***"
    assert sensor.name in PRIVATE_SENSORS_WARNED


@pytest.mark.asyncio
async def test_poll_sensor(clear_registry):
    """Test the _poll_sensor function."""
    # Create a mock sensor
    sensor = MockSensor(name="test_sensor", sample_period_s=0.001)
    
    # Create a task to run _poll_sensor for a short time
    task = asyncio.create_task(_poll_sensor(sensor))
    
    # Let it run briefly
    await asyncio.sleep(0.01)
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify the sensor was read at least once
    assert sensor.read_count > 0


@pytest.mark.asyncio
async def test_poll_sensor_error(clear_registry):
    """Test error handling in _poll_sensor."""
    # Create a mock sensor that throws an error
    sensor = MockSensor(name="error_sensor", sample_period_s=0.001, throw_error=True)
    
    # Create a task to run _poll_sensor for a short time
    with patch('spaxiom.runtime.logger') as mock_logger:
        task = asyncio.create_task(_poll_sensor(sensor))
        
        # Let it run briefly
        await asyncio.sleep(0.01)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Verify the error was logged
    mock_logger.error.assert_called()
    assert "Mock sensor error" in str(mock_logger.error.call_args)


@pytest.mark.asyncio
async def test_poll_sensor_privacy_error(clear_registry):
    """Test error handling with private sensors."""
    # Create a private mock sensor that throws an error
    sensor = MockSensor(name="private_error", privacy="private", sample_period_s=0.001, throw_error=True)
    
    # Create a task to run _poll_sensor for a short time
    with patch('spaxiom.runtime.logger') as mock_logger:
        task = asyncio.create_task(_poll_sensor(sensor))
        
        # Let it run briefly
        await asyncio.sleep(0.01)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Verify the error was logged with redacted message
    mock_logger.error.assert_called()
    assert "*** (Error in private sensor)" in str(mock_logger.error.call_args)
    # Verify we logged a warning about privacy
    mock_logger.warning.assert_called()
    assert sensor.name in PRIVATE_SENSORS_WARNED


@pytest.mark.asyncio
async def test_evaluate_conditions(clear_registry, clear_event_handlers, reset_runtime_state):
    """Test the _evaluate_conditions function."""
    # Create test condition
    condition_triggered = False
    
    def test_callback():
        nonlocal condition_triggered
        condition_triggered = True
    
    # Create a condition that returns the specified value
    condition_value = True
    test_condition = Condition(lambda: condition_value)
    
    # Register the condition and callback
    EVENT_HANDLERS.append((test_condition, test_callback))
    
    # Run _evaluate_conditions for a short time
    task = asyncio.create_task(_evaluate_conditions(100))
    
    # Let it run briefly
    await asyncio.sleep(0.05)
    
    # Check if the callback was triggered on the rising edge
    assert condition_triggered
    
    # Verify history was recorded
    assert len(GLOBAL_HISTORY) > 0
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_evaluate_conditions_edge_detection(clear_registry, clear_event_handlers, reset_runtime_state):
    """Test that callbacks are only triggered on rising edges."""
    # Create test condition with state tracking
    condition_trigger_count = 0
    
    def test_callback():
        nonlocal condition_trigger_count
        condition_trigger_count += 1
    
    # State that will be toggled
    condition_state = [False]
    
    def toggle_condition():
        return condition_state[0]
    
    test_condition = Condition(toggle_condition)
    
    # Register the condition and callback
    EVENT_HANDLERS.append((test_condition, test_callback))
    
    # Run _evaluate_conditions for a short time
    task = asyncio.create_task(_evaluate_conditions(100))
    
    # Let it run for a moment with condition False
    await asyncio.sleep(0.01)
    
    # Change to True (should trigger callback)
    condition_state[0] = True
    await asyncio.sleep(0.01)
    
    # Still True (should NOT trigger callback again)
    await asyncio.sleep(0.01)
    
    # Change to False
    condition_state[0] = False
    await asyncio.sleep(0.01)
    
    # Change to True again (should trigger callback again)
    condition_state[0] = True
    await asyncio.sleep(0.01)
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Should have triggered exactly twice (on the two rising edges)
    assert condition_trigger_count == 2


@pytest.mark.asyncio
async def test_evaluate_conditions_exception(clear_registry, clear_event_handlers, reset_runtime_state):
    """Test error handling in _evaluate_conditions."""
    # Create a condition that raises an exception
    def faulty_condition():
        raise ValueError("Test exception")
    
    test_condition = Condition(faulty_condition)
    mock_callback = MagicMock()
    mock_callback.__name__ = "mock_callback"
    
    # Register the condition and callback
    EVENT_HANDLERS.append((test_condition, mock_callback))
    
    # Run _evaluate_conditions with logging capture
    with patch('spaxiom.runtime.logger') as mock_logger:
        task = asyncio.create_task(_evaluate_conditions(100))
        
        # Let it run briefly
        await asyncio.sleep(0.01)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Verify error was logged
    mock_logger.error.assert_called()
    error_msg = mock_logger.error.call_args_list[0][0][0]
    assert "Error in condition or callback" in error_msg
    assert "Test exception" in str(mock_logger.error.call_args)
    
    # Callback should not have been called
    mock_callback.assert_not_called()


@pytest.mark.asyncio
async def test_shutdown_function(reset_runtime_state):
    """Test the shutdown function cancels tasks."""
    # Create some mock tasks
    mock_task1 = AsyncMock()
    mock_task1.done.return_value = False
    
    mock_task2 = AsyncMock()
    mock_task2.done.return_value = False
    
    # Add tasks to ACTIVE_TASKS
    ACTIVE_TASKS.append(mock_task1)
    ACTIVE_TASKS.append(mock_task2)
    
    # Call shutdown
    await shutdown()
    
    # Verify tasks were cancelled
    mock_task1.cancel.assert_called_once()
    mock_task2.cancel.assert_called_once()
    
    # Verify shutdown flag was set
    assert runtime_module.SHUTDOWN_INITIATED is True
    
    # Verify ACTIVE_TASKS was cleared
    assert len(ACTIVE_TASKS) == 0


@pytest.mark.asyncio
async def test_shutdown_already_initiated(reset_runtime_state):
    """Test that shutdown is only processed once."""
    # Set the shutdown flag
    globals()['SHUTDOWN_INITIATED'] = True
    
    mock_task = AsyncMock()
    ACTIVE_TASKS.append(mock_task)
    
    # Call shutdown
    await shutdown()
    
    # Verify task was not cancelled (because we already initiated shutdown)
    mock_task.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_start_runtime_sensor_polling(clear_registry, reset_runtime_state):
    """Test that start_runtime creates polling tasks for sensors."""
    # Create test sensors
    _sensor1 = MockSensor(name="sensor1", sample_period_s=0.1)
    sensor2 = MockSensor(name="sensor2", sample_period_s=0)  # Uses global polling rate

    # Mock the event handler creation to prevent it from running indefinitely
    with patch('spaxiom.runtime._evaluate_conditions'), \
         patch('spaxiom.runtime.asyncio.Event') as mock_event, \
         patch('spaxiom.runtime.asyncio.create_task', side_effect=asyncio.create_task) as mock_create_task:
        
        # Set up event to allow immediate return
        mock_event_obj = AsyncMock()
        mock_event.return_value = mock_event_obj
        mock_event_obj.wait.side_effect = asyncio.CancelledError()
        
        # Start runtime with exception catch
        try:
            await start_runtime(poll_ms=50, history_length=100)
        except asyncio.CancelledError:
            pass
    
    # Verify that tasks were created (1 for each sensor + 1 for evaluation)
    assert mock_create_task.call_count >= 3
    
    # Verify that sensor2 had its sample_period adjusted
    assert hasattr(sensor2, "_original_sample_period_s")
    assert sensor2.sample_period_s == 0.05  # 50ms converted to seconds


@pytest.mark.asyncio
async def test_start_runtime_signal_handlers(clear_registry, reset_runtime_state):
    """Test that signal handlers are registered properly."""
    # Mock the signal-related functions
    with patch('spaxiom.runtime.asyncio.get_running_loop') as mock_get_loop, \
         patch('spaxiom.runtime.signal'), \
         patch('spaxiom.runtime._evaluate_conditions'), \
         patch('spaxiom.runtime.asyncio.Event') as mock_event:
        
        # Set up mock loop
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        
        # Set up event to allow immediate return
        mock_event_obj = AsyncMock()
        mock_event.return_value = mock_event_obj
        mock_event_obj.wait.side_effect = asyncio.CancelledError()
        
        # Start runtime with exception catch
        try:
            await start_runtime(poll_ms=50, history_length=100)
        except asyncio.CancelledError:
            pass
    
    # Verify that signal handlers were added
    assert mock_loop.add_signal_handler.call_count >= 2  # At least SIGINT and SIGTERM


def test_start_blocking():
    """Test the start_blocking wrapper function."""
    # Mock asyncio.run to avoid actually running the event loop
    with patch('spaxiom.runtime.asyncio.run') as mock_run, \
         patch('spaxiom.runtime.sys.exit') as mock_exit:
        
        # Test normal execution
        start_runtime_mock = AsyncMock()
        mock_run.side_effect = lambda coro: None
        
        with patch('spaxiom.runtime.start_runtime', return_value=start_runtime_mock):
            start_blocking(poll_ms=50, history_length=100)
        
        # Verify start_runtime was called with correct parameters
        mock_run.assert_called_once()
        mock_exit.assert_called_once_with(0)
        
        # Test with KeyboardInterrupt
        mock_run.reset_mock()
        mock_exit.reset_mock()
        mock_run.side_effect = KeyboardInterrupt()
        
        with patch('spaxiom.runtime.start_runtime', return_value=start_runtime_mock):
            start_blocking(poll_ms=50, history_length=100)
        
        # Verify sys.exit was still called
        mock_exit.assert_called_once_with(0) 
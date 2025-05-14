"""
Runtime module for Spaxiom DSL that handles the event loop and sensor polling.
"""

import asyncio
import logging
import time
import signal
import sys
from typing import Dict, Callable, Deque, Tuple, Set, List
from collections import deque

from spaxiom.events import EVENT_HANDLERS
from spaxiom.core import SensorRegistry, Sensor

logger = logging.getLogger(__name__)

# Maximum number of history entries to keep in global history
MAX_HISTORY_LENGTH = 1000

# Global history deque with (timestamp, condition_id, value) entries
GLOBAL_HISTORY: Deque[Tuple[float, int, bool]] = deque(maxlen=MAX_HISTORY_LENGTH)

# Set to track private sensors that have been logged about
PRIVATE_SENSORS_WARNED: Set[str] = set()

# List to track active sensor polling tasks
ACTIVE_TASKS: List[asyncio.Task] = []

# Flag to track if shutdown has been initiated
SHUTDOWN_INITIATED = False

# Reference to the main runtime task
RUNTIME_TASK = None

# Flag to track if plugins have been initialized
PLUGINS_INITIALIZED = False


def format_sensor_value(sensor: Sensor, value) -> str:
    """
    Format a sensor value respecting privacy settings.

    Args:
        sensor: The sensor whose value is being formatted
        value: The value to format

    Returns:
        The formatted value as a string, or "***" if the sensor is private
    """
    if sensor.privacy == "private":
        # Check if we've warned about this sensor already
        if sensor.name not in PRIVATE_SENSORS_WARNED:
            logger.warning(
                f"Sensor '{sensor.name}' is marked as private. Its values will be redacted."
            )
            PRIVATE_SENSORS_WARNED.add(sensor.name)

        return "***"  # Redact private values

    # For public sensors, format as normal
    return str(value)


async def _poll_sensor(sensor: Sensor) -> None:
    """
    Continuously poll a sensor at its specified sample rate.

    Args:
        sensor: The sensor to poll
    """
    try:
        while True:
            try:
                # Read and update the sensor's last_value
                sensor.read()
            except Exception as e:
                # Redact error messages for private sensors
                error_msg = str(e)
                if sensor.privacy == "private":
                    error_msg = "*** (Error in private sensor)"

                    # Emit warning if this is the first time
                    if sensor.name not in PRIVATE_SENSORS_WARNED:
                        logger.warning(
                            f"Sensor '{sensor.name}' is marked as private. Errors will be redacted."
                        )
                        PRIVATE_SENSORS_WARNED.add(sensor.name)

                logger.error(f"Error reading sensor {sensor.name}: {error_msg}")

            # Sleep for the configured sample period
            await asyncio.sleep(sensor.sample_period_s)
    except asyncio.CancelledError:
        logger.debug(f"Polling task for sensor {sensor.name} cancelled")
    except Exception as e:
        logger.error(
            f"Unexpected error in sensor polling task for {sensor.name}: {str(e)}"
        )


async def _evaluate_conditions(history_length: int) -> None:
    """
    Continuously evaluate all conditions and trigger callbacks on rising edges.

    Args:
        history_length: Maximum number of history entries to keep per condition
    """
    # Track which conditions were true in the previous iteration
    # to detect rising edges (false -> true transitions)
    previous_states: Dict[Callable[[], bool], bool] = {}

    # Create a mapping of conditions to their unique IDs for history tracking
    condition_ids: Dict[Callable[[], bool], int] = {}

    # Initialize all conditions as False and assign unique IDs
    for i, (condition, _) in enumerate(EVENT_HANDLERS):
        previous_states[condition] = False
        condition_ids[condition] = i

    try:
        while True:
            # Get current timestamp using monotonic time (doesn't go backwards)
            current_time = time.monotonic()

            # Check all event handlers for rising edges
            for condition, callback in EVENT_HANDLERS:
                try:
                    # Get the condition ID
                    condition_id = condition_ids[condition]

                    # Filter history for this condition
                    condition_history = [
                        (timestamp, value)
                        for timestamp, cid, value in GLOBAL_HISTORY
                        if cid == condition_id
                    ]

                    # Prepare kwargs for condition evaluation
                    kwargs = {"now": current_time}

                    # Only include history if we have entries for this condition
                    if condition_history:
                        kwargs["history"] = deque(
                            condition_history, maxlen=history_length
                        )

                    # Evaluate the condition via its __call__ method
                    try:
                        current_state = bool(condition(**kwargs))
                    except TypeError:
                        # If it fails with kwargs, try with no arguments
                        current_state = bool(condition())

                    # Add to global history
                    GLOBAL_HISTORY.append((current_time, condition_id, current_state))

                    # Check for rising edge (false -> true)
                    if current_state and not previous_states[condition]:
                        # We don't redact callback names as they don't contain sensor values
                        print(f"[Spaxiom] Fired {callback.__name__}")
                        await asyncio.create_task(asyncio.to_thread(callback))

                    # Update the previous state
                    previous_states[condition] = current_state

                except Exception as e:
                    logger.error(
                        f"Error in condition or callback {callback.__name__}: {str(e)}"
                    )

            # Small delay to prevent CPU hogging (much shorter than previous global poll)
            await asyncio.sleep(0.01)  # 10ms
    except asyncio.CancelledError:
        logger.debug("Condition evaluation task cancelled")


async def shutdown():
    """
    Gracefully shutdown the runtime by cancelling all active tasks.

    This function is called when the process receives SIGINT or SIGTERM signals,
    allowing for a clean shutdown with proper resource cleanup.
    """
    global ACTIVE_TASKS, SHUTDOWN_INITIATED, RUNTIME_TASK

    # Use an already_shutdown flag to track if we're in the middle of shutdown
    already_shutdown = SHUTDOWN_INITIATED

    # Always set the flag - this way tests can verify it was set
    SHUTDOWN_INITIATED = True

    # Early return if already shutting down
    if already_shutdown:
        return

    logger.info("Shutting down Spaxiom runtime...")
    print("\n[Spaxiom] Shutdown initiated, cancelling tasks...")

    # Cancel all running tasks
    for task in ACTIVE_TASKS:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete cancellation
    if ACTIVE_TASKS:
        await asyncio.gather(*ACTIVE_TASKS, return_exceptions=True)

    # Cancel the main runtime task if it exists and is running
    if RUNTIME_TASK is not None and not RUNTIME_TASK.done():
        RUNTIME_TASK.cancel()

    # Reset sensor sample periods that were set temporarily
    registry = SensorRegistry()
    for sensor in registry.list_all().values():
        if hasattr(sensor, "_original_sample_period_s"):
            sensor.sample_period_s = sensor._original_sample_period_s
            delattr(sensor, "_original_sample_period_s")

    # Clear the active tasks list
    ACTIVE_TASKS.clear()

    print("[Spaxiom] Shutdown complete.")

    # Exit the process for signal handlers
    if hasattr(shutdown, "_signal_triggered") and shutdown._signal_triggered:
        # Reset the flag
        shutdown._signal_triggered = False
        sys.exit(0)


async def start_runtime(
    poll_ms: int = 100, history_length: int = MAX_HISTORY_LENGTH
) -> None:
    """
    Start the Spaxiom runtime that reads sensors and processes events asynchronously.

    Args:
        poll_ms: The polling interval in milliseconds (for backward compatibility, only used for sensors with sample_period_s=0)
        history_length: Maximum number of history entries to keep per condition

    This function:
    1. Loads and initializes plugins
    2. Spawns tasks to poll sensors at their individual rates
    3. For sensors with sample_period_s=0, uses the global poll rate
    4. Evaluates all conditions using sensors' cached values
    5. Fires callbacks only on rising edges (when a condition changes from False to True)
    6. Maintains global history of condition values for temporal conditions
    7. Respects sensor privacy settings when logging/printing values
    8. Registers signal handlers for graceful shutdown on Ctrl+C or termination signals

    Terminate with KeyboardInterrupt (Ctrl+C).
    """
    global GLOBAL_HISTORY, PRIVATE_SENSORS_WARNED, ACTIVE_TASKS, SHUTDOWN_INITIATED, RUNTIME_TASK, PLUGINS_INITIALIZED

    # Store reference to this task
    RUNTIME_TASK = asyncio.current_task()

    # Reset shutdown flag
    SHUTDOWN_INITIATED = False

    # Set the global history deque max length
    GLOBAL_HISTORY = deque(maxlen=history_length)

    # Clear the warned sensors set at the beginning of each run
    PRIVATE_SENSORS_WARNED.clear()

    # Clear any existing tasks
    for task in ACTIVE_TASKS:
        if not task.done():
            task.cancel()
    ACTIVE_TASKS.clear()

    # Initialize plugins if not already done
    if not PLUGINS_INITIALIZED:
        try:
            from spaxiom.plugins import discover_and_load_plugins, initialize_plugins

            print("[Spaxiom] Discovering and loading plugins...")
            discover_and_load_plugins()
            initialize_plugins()
            PLUGINS_INITIALIZED = True
        except ImportError:
            # The plugins module might not be available in older versions
            logger.debug("Plugins module not available, skipping plugin initialization")
        except Exception as e:
            logger.error(f"Error initializing plugins: {str(e)}")
            import traceback

            logger.debug(traceback.format_exc())

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    # Define signal handler function
    def signal_handler():
        if not SHUTDOWN_INITIATED:
            # Set a flag to indicate this was triggered by a signal
            shutdown._signal_triggered = True
            # Schedule the shutdown coroutine
            asyncio.create_task(shutdown())

    # Register the signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        registry = SensorRegistry()
        sensors = registry.list_all().values()

        # Create polling tasks for sensors with custom sample periods
        for sensor in sensors:
            if sensor.sample_period_s > 0:
                task = asyncio.create_task(_poll_sensor(sensor))
                ACTIVE_TASKS.append(task)
            else:
                # For sensors with sample_period_s=0, create a task using the global poll_ms
                adjusted_period = poll_ms / 1000  # Convert ms to seconds
                # Save original sample period
                sensor._original_sample_period_s = sensor.sample_period_s
                # Set the sample period temporarily for this run
                sensor.sample_period_s = adjusted_period
                task = asyncio.create_task(_poll_sensor(sensor))
                ACTIVE_TASKS.append(task)

        print(
            f"[Spaxiom] Runtime started with {len(ACTIVE_TASKS)} sensor polling tasks"
        )
        print("[Spaxiom] Press Ctrl+C to stop")

        # Create and start the condition evaluation task
        evaluation_task = asyncio.create_task(_evaluate_conditions(history_length))
        ACTIVE_TASKS.append(evaluation_task)

        # Wait until interrupted
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        # This shouldn't happen with signal handlers, but just in case
        await shutdown()
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")
        await shutdown()


def start_blocking(
    poll_ms: int = 100, history_length: int = MAX_HISTORY_LENGTH
) -> None:
    """
    Start the Spaxiom runtime in a blocking manner (wrapper for async start_runtime).

    Args:
        poll_ms: The polling interval in milliseconds (for sensors with sample_period_s=0)
        history_length: Maximum number of history entries to keep per condition
    """
    try:
        asyncio.run(start_runtime(poll_ms, history_length))
    except KeyboardInterrupt:
        # This will be caught by asyncio.run and the event loop will be closed
        pass
    # Clean exit after asyncio.run completes
    sys.exit(0)

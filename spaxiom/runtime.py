"""
Runtime module for Spaxiom DSL that handles the event loop and sensor polling.

RUNTIME SELECTION (as of Step 8):
---------------------------------
This module provides two runtime implementations:

1. PHASED (default): Uses PhasedTickRunner with deterministic 4-phase tick execution:
   - Phase 1: Concurrent sensor reads
   - Phase 2: Dependency-ordered pattern updates
   - Phase 3: Condition evaluation (polling or event-driven)
   - Phase 4: Isolated callback dispatch

2. LEGACY: Uses the original async task-based runtime with independent sensor
   polling tasks. Kept for backwards compatibility.

RUNTIME SELECTION:
- Environment variable: SPAXIOM_RUNTIME=phased|legacy (default: phased)
- CLI flag: --runtime phased|legacy

The phased runtime is recommended for new code. Legacy runtime is available
for backwards compatibility with existing scripts that depend on the old
behavior.
"""

import asyncio
import inspect
import logging
import os
import time
import signal
import sys
from typing import Dict, Callable, Deque, Tuple, Set, List, Optional
from collections import deque

from spaxiom.events import EVENT_HANDLERS
from spaxiom.core import SensorRegistry, Sensor

logger = logging.getLogger(__name__)

# Runtime selection: "phased" (default) or "legacy"
RUNTIME_MODE = os.environ.get("SPAXIOM_RUNTIME", "phased").lower()


def get_runtime_mode() -> str:
    """Get the current runtime mode.

    Returns:
        "phased" or "legacy"
    """
    return RUNTIME_MODE


def set_runtime_mode(mode: str) -> None:
    """Set the runtime mode programmatically.

    Args:
        mode: "phased" or "legacy"

    Raises:
        ValueError: If mode is not "phased" or "legacy"
    """
    global RUNTIME_MODE
    mode = mode.lower()
    if mode not in ("phased", "legacy"):
        raise ValueError(f"Invalid runtime mode: {mode}. Must be 'phased' or 'legacy'.")
    RUNTIME_MODE = mode


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

# Reference to the PhasedTickRunner when using phased mode
PHASED_RUNNER: Optional["PhasedTickRunner"] = None  # noqa: F821


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
    # Handle both real asyncio.Task objects and mock objects from tests
    awaitables = []
    for task in ACTIVE_TASKS:
        # Check if task is done (handle mocks that may not have proper done())
        try:
            is_done = task.done() if hasattr(task, "done") else True
            # In Python 3.13+, AsyncMock.done() returns a coroutine, not a bool
            # If we got a coroutine, treat as not done and don't await it
            if asyncio.iscoroutine(is_done):
                is_done = False
        except Exception:
            is_done = True

        if not is_done and hasattr(task, "cancel"):
            task.cancel()

        # Only gather real awaitables (Task, Future, coroutine)
        if (
            asyncio.isfuture(task)
            or isinstance(task, asyncio.Task)
            or asyncio.iscoroutine(task)
            or inspect.isawaitable(task)
        ):
            awaitables.append(task)

    # Wait for all real awaitables to complete cancellation
    if awaitables:
        await asyncio.gather(*awaitables, return_exceptions=True)

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


async def _start_runtime_phased(poll_ms: int, history_length: int) -> None:
    """Start the phased tick runtime (new default).

    This uses PhasedTickRunner for deterministic 4-phase execution.
    """
    global SHUTDOWN_INITIATED, PLUGINS_INITIALIZED, PHASED_RUNNER

    # Reset shutdown flag
    SHUTDOWN_INITIATED = False

    # Initialize plugins if not already done
    if not PLUGINS_INITIALIZED:
        try:
            from spaxiom.plugins import discover_and_load_plugins, initialize_plugins

            print("[Spaxiom] Discovering and loading plugins...")
            discover_and_load_plugins()
            initialize_plugins()
            PLUGINS_INITIALIZED = True
        except ImportError:
            logger.debug("Plugins module not available, skipping plugin initialization")
        except Exception as e:
            logger.error(f"Error initializing plugins: {str(e)}")
            import traceback

            logger.debug(traceback.format_exc())

    # Import PhasedTickRunner here to avoid circular imports
    from spaxiom.tick import PhasedTickRunner

    # Convert poll_ms to tick rate in Hz
    tick_rate_hz = 1000.0 / poll_ms if poll_ms > 0 else 10.0

    # Create the runner
    runner = PhasedTickRunner(tick_rate_hz=tick_rate_hz)
    PHASED_RUNNER = runner

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler():
        global SHUTDOWN_INITIATED
        if not SHUTDOWN_INITIATED:
            SHUTDOWN_INITIATED = True
            print("\n[Spaxiom] Shutdown initiated...")
            runner.stop()

    # Register the signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        registry = SensorRegistry()
        sensor_count = len(registry.list_all())

        print(f"[Spaxiom] Phased runtime started (tick_rate={tick_rate_hz:.1f} Hz)")
        print(f"[Spaxiom] {sensor_count} sensors registered")
        print("[Spaxiom] Press Ctrl+C to stop")

        # Run the phased tick loop
        await runner.run()

    except asyncio.CancelledError:
        runner.stop()
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")
        runner.stop()
    finally:
        PHASED_RUNNER = None
        print("[Spaxiom] Shutdown complete.")


async def _start_runtime_legacy(poll_ms: int, history_length: int) -> None:
    """Start the legacy task-based runtime.

    This is the original implementation kept for backwards compatibility.
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
            f"[Spaxiom] Legacy runtime started with {len(ACTIVE_TASKS)} sensor polling tasks"
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


async def start_runtime(
    poll_ms: int = 100, history_length: int = MAX_HISTORY_LENGTH
) -> None:
    """
    Start the Spaxiom runtime that reads sensors and processes events asynchronously.

    Args:
        poll_ms: The polling interval in milliseconds (converted to tick_rate_hz for phased mode)
        history_length: Maximum number of history entries to keep per condition (legacy mode only)

    Runtime Mode Selection:
        - Set SPAXIOM_RUNTIME=phased (default) for deterministic 4-phase execution
        - Set SPAXIOM_RUNTIME=legacy for backwards-compatible task-based execution

    Terminate with KeyboardInterrupt (Ctrl+C).
    """
    if RUNTIME_MODE == "phased":
        await _start_runtime_phased(poll_ms, history_length)
    else:
        await _start_runtime_legacy(poll_ms, history_length)


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

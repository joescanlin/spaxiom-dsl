"""
Runtime module for Spaxiom DSL that handles the event loop and sensor polling.
"""

import asyncio
import logging
import time
from typing import Dict, Callable, Deque, Tuple, Set
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


async def start_runtime(
    poll_ms: int = 100, history_length: int = MAX_HISTORY_LENGTH
) -> None:
    """
    Start the Spaxiom runtime that reads sensors and processes events asynchronously.

    Args:
        poll_ms: The polling interval in milliseconds
        history_length: Maximum number of history entries to keep per condition

    This function:
    1. Polls all registered sensors at regular intervals
    2. Evaluates all conditions
    3. Fires callbacks only on rising edges (when a condition changes from False to True)
    4. Logs when callbacks are triggered
    5. Maintains global history of condition values for temporal conditions
    6. Respects sensor privacy settings when logging/printing values

    Terminate with KeyboardInterrupt (Ctrl+C).
    """
    # Track which conditions were true in the previous iteration
    # to detect rising edges (false -> true transitions)
    previous_states: Dict[Callable[[], bool], bool] = {}

    # Set the global history deque max length
    global GLOBAL_HISTORY
    GLOBAL_HISTORY = deque(maxlen=history_length)

    # Clear the warned sensors set at the beginning of each run
    global PRIVATE_SENSORS_WARNED
    PRIVATE_SENSORS_WARNED.clear()

    # Create a mapping of conditions to their unique IDs for history tracking
    condition_ids: Dict[Callable[[], bool], int] = {}

    # Initialize all conditions as False and assign unique IDs
    for i, (condition, _) in enumerate(EVENT_HANDLERS):
        previous_states[condition] = False
        condition_ids[condition] = i

    try:
        print(f"[Spaxiom] Runtime started with poll interval of {poll_ms}ms")

        while True:
            # Get current timestamp using monotonic time (doesn't go backwards)
            current_time = time.monotonic()

            # Read all sensors to update their values
            registry = SensorRegistry()
            for sensor in registry.list_all().values():
                try:
                    # We still read private sensors, but don't log their values
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

            # Wait for the next polling interval
            await asyncio.sleep(poll_ms / 1000)

    except KeyboardInterrupt:
        print("[Spaxiom] Runtime stopped by user")
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")


def start_blocking(
    poll_ms: int = 100, history_length: int = MAX_HISTORY_LENGTH
) -> None:
    """
    Start the Spaxiom runtime in a blocking manner (wrapper for async start_runtime).

    Args:
        poll_ms: The polling interval in milliseconds
        history_length: Maximum number of history entries to keep per condition
    """
    asyncio.run(start_runtime(poll_ms, history_length))

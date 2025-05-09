"""
Runtime module for Spaxiom DSL that handles the event loop and sensor polling.
"""

import asyncio
import logging
import time
from typing import Dict, Callable, Deque, Tuple
from collections import deque

from spaxiom.events import EVENT_HANDLERS
from spaxiom.registry import SensorRegistry

logger = logging.getLogger(__name__)

# Maximum number of history entries to keep in global history
MAX_HISTORY_LENGTH = 1000

# Global history deque with (timestamp, condition_id, value) entries
GLOBAL_HISTORY: Deque[Tuple[float, int, bool]] = deque(maxlen=MAX_HISTORY_LENGTH)


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

    Terminate with KeyboardInterrupt (Ctrl+C).
    """
    # Track which conditions were true in the previous iteration
    # to detect rising edges (false -> true transitions)
    previous_states: Dict[Callable[[], bool], bool] = {}

    # Set the global history deque max length
    global GLOBAL_HISTORY
    GLOBAL_HISTORY = deque(maxlen=history_length)

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
                    sensor.read()
                except Exception as e:
                    logger.error(f"Error reading sensor {sensor.name}: {str(e)}")

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

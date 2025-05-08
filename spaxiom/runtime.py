"""
Runtime module for Spaxiom DSL that handles the event loop and sensor polling.
"""

import asyncio
import logging
from typing import Dict, Callable

from spaxiom.events import EVENT_HANDLERS
from spaxiom.registry import SensorRegistry

logger = logging.getLogger(__name__)


async def start_runtime(poll_ms: int = 100) -> None:
    """
    Start the Spaxiom runtime that reads sensors and processes events asynchronously.

    Args:
        poll_ms: The polling interval in milliseconds

    This function:
    1. Polls all registered sensors at regular intervals
    2. Evaluates all conditions
    3. Fires callbacks only on rising edges (when a condition changes from False to True)
    4. Logs when callbacks are triggered

    Terminate with KeyboardInterrupt (Ctrl+C).
    """
    # Track which conditions were true in the previous iteration
    # to detect rising edges (false -> true transitions)
    previous_states: Dict[Callable[[], bool], bool] = {}

    # Initialize all conditions as False
    for condition, _ in EVENT_HANDLERS:
        previous_states[condition] = False

    try:
        print(f"[Spaxiom] Runtime started with poll interval of {poll_ms}ms")

        while True:
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
                    # Evaluate the condition
                    current_state = condition()

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


def start_blocking(poll_ms: int = 100) -> None:
    """
    Start the Spaxiom runtime in a blocking manner (wrapper for async start_runtime).

    Args:
        poll_ms: The polling interval in milliseconds
    """
    asyncio.run(start_runtime(poll_ms))

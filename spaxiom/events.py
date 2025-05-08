"""
Events module for condition-based callbacks in Spaxiom DSL.
"""

from typing import Callable, List, Any, Tuple
import functools
import logging
import time

# Import here rather than from ... to avoid circular imports
from spaxiom.condition import Condition

# Global registry of event handlers
EVENT_HANDLERS: List[Tuple[Condition, Callable[[], Any]]] = []

logger = logging.getLogger(__name__)


def on(condition: Condition) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
    """
    Decorator to register a function to be called when a condition is met.

    Args:
        condition: The condition that triggers the callback

    Returns:
        A decorator function that registers the callback

    Example:
        ```python
        sensor_in_zone = Condition(lambda: zone.contains(sensor.location))

        @on(sensor_in_zone)
        def alert_sensor_in_zone():
            print("Sensor entered the zone!")
        ```
    """

    def decorator(callback: Callable[[], Any]) -> Callable[[], Any]:
        # Register the callback with its condition
        EVENT_HANDLERS.append((condition, callback))

        @functools.wraps(callback)
        def wrapper(*args, **kwargs):
            return callback(*args, **kwargs)

        return wrapper

    return decorator


def process_events() -> None:
    """
    Check all registered conditions and call their callbacks if the conditions are met.

    This should be called periodically, for example in a main loop.
    """
    for condition, callback in EVENT_HANDLERS:
        try:
            if condition():
                callback()
        except Exception as e:
            logger.error(f"Error in event handler {callback.__name__}: {str(e)}")


def run_event_loop(interval: float = 0.1) -> None:
    """
    Run a simple event loop that processes events at the specified interval.

    Args:
        interval: Time in seconds between processing events
    """
    try:
        while True:
            process_events()
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Event loop stopped by user")
    except Exception as e:
        logger.error(f"Event loop error: {str(e)}")

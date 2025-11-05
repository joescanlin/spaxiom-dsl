from __future__ import annotations

from typing import Callable, Dict, List, Optional
from datetime import datetime


class ADLTracker:
    """
    Activities of Daily Living (ADL) tracking helper.

    This is a thin wrapper around a few boolean/threshold conditions for:
    - getting up from bed
    - meal preparation events
    - bathroom visits
    - hallway walking

    Consumers are expected to register callbacks for simple event names.
    """

    def __init__(
        self,
        bed_sensor,
        fridge_sensor,
        bath_sensor,
        hall_sensor,
    ) -> None:
        self.bed_sensor = bed_sensor
        self.fridge_sensor = fridge_sensor
        self.bath_sensor = bath_sensor
        self.hall_sensor = hall_sensor

        self._callbacks: Dict[str, List[Callable[[datetime], None]]] = {}
        self._counts: Dict[str, int] = {
            "got_up": 0,
            "meal": 0,
            "bath": 0,
            "walk": 0,
        }

    def on(self, event_name: str, callback: Callable[[datetime], None]) -> None:
        """Register a callback for a named ADL event."""
        self._callbacks.setdefault(event_name, []).append(callback)

    def _emit(self, event_name: str) -> None:
        now = datetime.now()
        self._counts[event_name] = self._counts.get(event_name, 0) + 1
        for cb in self._callbacks.get(event_name, []):
            cb(now)

    # The following methods are intentionally simplistic; an application
    # can call them from Spaxiom Conditions or event handlers:

    def mark_got_up(self) -> None:
        self._emit("got_up")

    def mark_meal(self) -> None:
        self._emit("meal")

    def mark_bath(self) -> None:
        self._emit("bath")

    def mark_walk(self) -> None:
        self._emit("walk")

    def daily_counts(self) -> Dict[str, int]:
        """Return current counts for the day."""
        return dict(self._counts)

    def reset(self) -> None:
        """Reset all counts (e.g. at end of day)."""
        for k in list(self._counts.keys()):
            self._counts[k] = 0

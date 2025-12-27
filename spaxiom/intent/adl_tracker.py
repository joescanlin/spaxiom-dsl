from __future__ import annotations

from typing import Any, Callable, Dict, List
from datetime import datetime

from spaxiom.intent.pattern import Pattern, ADLEvent


class ADLTracker(Pattern):
    """
    Activities of Daily Living (ADL) tracking helper.

    This is a thin wrapper around a few boolean/threshold conditions for:
    - getting up from bed
    - meal preparation events
    - bathroom visits
    - hallway walking

    Consumers are expected to register callbacks for simple event names.

    Inherits from Pattern to support update/emit/depends_on interface.
    """

    def __init__(
        self,
        bed_sensor,
        fridge_sensor,
        bath_sensor,
        hall_sensor,
        name: str = "adl_tracker",
    ) -> None:
        super().__init__(name=name)
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
        # Track previous sensor states for edge detection
        self._prev_bed: bool = False
        self._prev_fridge: bool = False
        self._prev_bath: bool = False
        self._prev_hall: bool = False

    def on(self, event_name: str, callback: Callable[[datetime], None]) -> None:
        """Register a callback for a named ADL event."""
        self._callbacks.setdefault(event_name, []).append(callback)

    def _emit_adl(self, event_name: str) -> None:
        """Internal method to emit an ADL event (both legacy callbacks and typed events)."""
        now = datetime.now()
        self._counts[event_name] = self._counts.get(event_name, 0) + 1
        # Legacy callback dispatch
        for cb in self._callbacks.get(event_name, []):
            cb(now)
        # Typed event emission
        self._emit_event(
            ADLEvent(
                activity=event_name,
                count_today=self._counts[event_name],
            )
        )

    # The following methods are intentionally simplistic; an application
    # can call them from Spaxiom Conditions or event handlers:

    def mark_got_up(self) -> None:
        self._emit_adl("got_up")

    def mark_meal(self) -> None:
        self._emit_adl("meal")

    def mark_bath(self) -> None:
        self._emit_adl("bath")

    def mark_walk(self) -> None:
        self._emit_adl("walk")

    def daily_counts(self) -> Dict[str, int]:
        """Return current counts for the day."""
        return dict(self._counts)

    def reset(self) -> None:
        """Reset all counts (e.g. at end of day)."""
        for k in list(self._counts.keys()):
            self._counts[k] = 0

    # Pattern interface methods

    def _read_sensor(self, sensor) -> bool:
        """Safely read a sensor as boolean."""
        try:
            val = sensor.read()
            return bool(val > 0.5 if isinstance(val, (int, float)) else val)
        except (AttributeError, TypeError):
            return False

    def update(self, dt: float, context: Dict[str, Any]) -> None:
        """Update pattern state by detecting sensor edge transitions.

        Args:
            dt: Time delta since last tick in seconds
            context: Tick context (sensor values, other pattern states)
        """
        # Read current sensor states
        bed_active = self._read_sensor(self.bed_sensor)
        fridge_active = self._read_sensor(self.fridge_sensor)
        bath_active = self._read_sensor(self.bath_sensor)
        hall_active = self._read_sensor(self.hall_sensor)

        # Detect rising edges (sensor becomes active)
        if bed_active and not self._prev_bed:
            # Bed sensor triggers "got_up" on rising edge
            # (assumption: sensor detects when bed becomes unoccupied)
            pass  # We interpret this as "got back to bed", not got_up
        if not bed_active and self._prev_bed:
            # Bed sensor falling edge = got up from bed
            self._emit_adl("got_up")

        if fridge_active and not self._prev_fridge:
            self._emit_adl("meal")

        if bath_active and not self._prev_bath:
            self._emit_adl("bath")

        if hall_active and not self._prev_hall:
            self._emit_adl("walk")

        # Update previous states
        self._prev_bed = bed_active
        self._prev_fridge = fridge_active
        self._prev_bath = bath_active
        self._prev_hall = hall_active

    def depends_on(self) -> List[Any]:
        """Return list of dependencies for ordering.

        Returns:
            List containing all sensors this pattern depends on.
        """
        return [
            self.bed_sensor,
            self.fridge_sensor,
            self.bath_sensor,
            self.hall_sensor,
        ]

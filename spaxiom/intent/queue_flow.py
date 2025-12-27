from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from spaxiom.adaptors.floor_grid_sensor import FloorGridSensor

from spaxiom.intent.pattern import Pattern, QueueLengthChanged
from spaxiom.intent.occupancy_field import OccupancyField


class QueueFlow(Pattern):
    """
    Rough queue-flow estimation on top of a floor grid.

    This is a simple, lightweight helper; it's not meant to be a full
    queuing-theory implementation, but rather something that provides:
    - estimated queue length (people count)
    - crude arrival/service rates
    - a heuristic wait-time estimate

    Inherits from Pattern to support update/emit/depends_on interface.
    """

    def __init__(
        self,
        sensor: FloorGridSensor,
        name: str = "queue",
        avg_tiles_per_person: float = 3.0,
        length_change_threshold: float = 1.0,
    ) -> None:
        super().__init__(name=name)
        self.sensor = sensor
        self._field = OccupancyField(sensor, name=name)
        self._avg_tiles_per_person = avg_tiles_per_person
        self._length_change_threshold = length_change_threshold

        # Very simple rolling stats
        self._total_arrivals = 0.0
        self._total_departures = 0.0
        self._window_seconds = 300.0  # conceptual, not strictly enforced
        self._previous_length: float = 0.0

    def _estimated_people(self) -> float:
        frame = self.sensor.frame()
        active_tiles = float(frame.sum())
        if self._avg_tiles_per_person <= 0:
            return active_tiles
        return active_tiles / self._avg_tiles_per_person

    def length(self) -> float:
        """Estimated queue length (people)."""
        return self._estimated_people()

    def arrival_rate(self) -> float:
        """
        Crude arrival rate (people / minute).

        Currently this is a placeholder using total arrivals and a conceptual window.
        Application code can update arrivals/departures if desired.
        """
        if self._window_seconds <= 0:
            return 0.0
        return (self._total_arrivals / self._window_seconds) * 60.0

    def service_rate(self) -> float:
        """Crude service rate (people / minute)."""
        if self._window_seconds <= 0:
            return 0.0
        return (self._total_departures / self._window_seconds) * 60.0

    def wait_time(self) -> float:
        """
        Very rough wait-time estimate in seconds, using Little's Law style idea:
            W ~ L / λ
        where L is queue length, λ is service rate.
        """
        rate = self.service_rate()
        if rate <= 0:
            return 0.0
        return (self.length() / rate) * 60.0

    # Optional hooks for external code to update counts:
    def record_arrival(self, n: float = 1.0) -> None:
        self._total_arrivals += n

    def record_departure(self, n: float = 1.0) -> None:
        self._total_departures += n

    # Pattern interface methods

    def update(self, dt: float, context: Dict[str, Any]) -> None:
        """Update pattern state and emit events if queue length changed.

        Args:
            dt: Time delta since last tick in seconds
            context: Tick context (sensor values, other pattern states)
        """
        current_length = self.length()
        change = abs(current_length - self._previous_length)

        if change >= self._length_change_threshold:
            self._emit_event(
                QueueLengthChanged(
                    queue_name=self._name,
                    length=current_length,
                    previous_length=self._previous_length,
                    wait_time_seconds=self.wait_time(),
                )
            )

        self._previous_length = current_length

    def depends_on(self) -> List[Any]:
        """Return list of dependencies for ordering.

        Returns:
            List containing the sensor this pattern depends on.
        """
        return [self.sensor]

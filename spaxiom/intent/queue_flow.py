from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from spaxiom.adaptors.floor_grid_sensor import FloorGridSensor

from spaxiom.intent.occupancy_field import OccupancyField


class QueueFlow:
    """
    Rough queue-flow estimation on top of a floor grid.

    This is a simple, lightweight helper; it's not meant to be a full
    queuing-theory implementation, but rather something that provides:
    - estimated queue length (people count)
    - crude arrival/service rates
    - a heuristic wait-time estimate
    """

    def __init__(
        self,
        sensor: FloorGridSensor,
        name: str = "queue",
        avg_tiles_per_person: float = 3.0,
    ) -> None:
        self.sensor = sensor
        self.name = name
        self._field = OccupancyField(sensor, name=name)
        self._avg_tiles_per_person = avg_tiles_per_person

        # Very simple rolling stats
        self._total_arrivals = 0.0
        self._total_departures = 0.0
        self._window_seconds = 300.0  # conceptual, not strictly enforced

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

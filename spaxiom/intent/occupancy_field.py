from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from spaxiom.adaptors.floor_grid_sensor import FloorGridSensor

from spaxiom.logic import Condition
from spaxiom.geo import Zone
from spaxiom.intent.pattern import Pattern, OccupancyChanged, CrowdingDetected


class OccupancyField(Pattern):
    """
    High-level wrapper for a 2-D boolean floor grid sensor.

    Provides simple helpers to compute occupancy percentages and rough hotspots
    that can be fed into agent logic or LLM prompts.

    Inherits from Pattern to support update/emit/depends_on interface.
    """

    def __init__(
        self,
        sensor: FloorGridSensor,
        name: str = "field",
        zone: Optional[Zone] = None,
        crowding_threshold: float = 80.0,
    ) -> None:
        super().__init__(name=name)
        self.sensor = sensor
        self.zone = zone
        self._crowding_threshold = crowding_threshold
        self._previous_percent: float = 0.0
        self._change_threshold: float = 5.0  # Emit event if change exceeds this

    def _frame(self) -> np.ndarray:
        frame = self.sensor.frame()
        if self.zone is None:
            return frame
        # For now, assume Zone describes a sub-rectangle in tile indices.
        # More sophisticated mapping can be added later.
        # Zone: (x1, y1, x2, y2) inclusive/exclusive is defined in geo.
        x1, y1, x2, y2 = self.zone.x1, self.zone.y1, self.zone.x2, self.zone.y2
        return frame[y1:y2, x1:x2]

    def percent(self) -> float:
        """Return occupancy percentage (0-100) of the selected frame."""
        f = self._frame()
        if f.size == 0:
            return 0.0
        return float(f.mean() * 100.0)

    def percent_above(self, threshold: float) -> Condition:
        """
        Return a Condition that becomes true when occupancy % >= threshold.

        This is intended to be composed with temporal logic, e.g.:

            crowded = within(180, field.percent_above(10.0))
        """
        return Condition(lambda: self.percent() >= threshold)

    def hotspots(self, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Return a list of approximate hotspots: [{x, y, weight}, ...].

        This is intentionally simple and lightweight: it finds the top_k
        active tiles by value in the current frame.
        """
        f = self._frame()
        if f.size == 0:
            return []

        ys, xs = np.nonzero(f)
        weights = f[ys, xs].astype(float)
        if xs.size == 0:
            return []

        # Sort by weight (all ones) then by index; this is simple but good enough for now.
        indices = np.argsort(-weights)
        xs = xs[indices][:top_k]
        ys = ys[indices][:top_k]
        weights = weights[indices][:top_k]

        hotspots: List[Dict[str, Any]] = []
        for x, y, w in zip(xs, ys, weights):
            hotspots.append({"x": int(x), "y": int(y), "weight": float(w)})
        return hotspots

    # Pattern interface methods

    def update(self, dt: float, context: Dict[str, Any]) -> None:
        """Update pattern state and emit events if occupancy changed significantly.

        Args:
            dt: Time delta since last tick in seconds
            context: Tick context (sensor values, other pattern states)
        """
        current_percent = self.percent()
        zone_name = self.zone.name if self.zone else self._name

        # Check for significant change
        change = abs(current_percent - self._previous_percent)
        if change >= self._change_threshold:
            self._emit_event(
                OccupancyChanged(
                    zone=zone_name,
                    percent=current_percent,
                    previous_percent=self._previous_percent,
                    hotspots=self.hotspots(),
                )
            )

        # Check for crowding
        if (
            current_percent >= self._crowding_threshold
            and self._previous_percent < self._crowding_threshold
        ):
            self._emit_event(
                CrowdingDetected(
                    zone=zone_name,
                    percent=current_percent,
                    threshold=self._crowding_threshold,
                )
            )

        self._previous_percent = current_percent

    def depends_on(self) -> List[Any]:
        """Return list of dependencies for ordering.

        Returns:
            List containing the sensor this pattern depends on.
        """
        return [self.sensor]

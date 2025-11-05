from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from spaxiom.adaptors.floor_grid_sensor import FloorGridSensor

from spaxiom.logic import Condition
from spaxiom.geo import Zone


class OccupancyField:
    """
    High-level wrapper for a 2-D boolean floor grid sensor.

    Provides simple helpers to compute occupancy percentages and rough hotspots
    that can be fed into agent logic or LLM prompts.
    """

    def __init__(
        self,
        sensor: FloorGridSensor,
        name: str = "field",
        zone: Optional[Zone] = None,
    ) -> None:
        self.sensor = sensor
        self.name = name
        self.zone = zone

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

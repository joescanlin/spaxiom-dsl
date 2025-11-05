from __future__ import annotations

from typing import Any, Dict


class FmSteward:
    """
    Facilities-management steward helper.

    Encapsulates the concept of "needs service" based on a small set of
    restroom / consumable / air-quality sensors.
    """

    def __init__(
        self,
        door_counter,
        towel_sensor,
        bin_sensor,
        gas_sensor,
        floor_sensor,
        entries_threshold: int = 120,
        towel_threshold_pct: float = 15.0,
        bin_threshold_pct: float = 85.0,
        gas_threshold_ppm: float = 15.0,
    ) -> None:
        self.door_counter = door_counter
        self.towel_sensor = towel_sensor
        self.bin_sensor = bin_sensor
        self.gas_sensor = gas_sensor
        self.floor_sensor = floor_sensor

        self.entries_threshold = entries_threshold
        self.towel_threshold_pct = towel_threshold_pct
        self.bin_threshold_pct = bin_threshold_pct
        self.gas_threshold_ppm = gas_threshold_ppm

    def _disp_percent_left(self) -> float:
        # We assume towel_sensor exposes .percent_remaining() if available,
        # otherwise we treat .read() as grams and expect the application to
        # subclass this for more accuracy.
        if hasattr(self.towel_sensor, "percent_remaining"):
            return float(self.towel_sensor.percent_remaining())
        return 100.0  # fallback

    def needs_service(self) -> bool:
        """
        Return True if any of the service conditions is met AND the door
        traffic has passed the entries threshold.
        """
        try:
            entries = self.door_counter.count_delta()
        except AttributeError:
            entries = 0

        low_towels = self._disp_percent_left() < self.towel_threshold_pct
        try:
            bin_pct = float(self.bin_sensor.percent_full())
        except AttributeError:
            bin_pct = 0.0

        try:
            gas_ppm = float(self.gas_sensor.ppm())
        except AttributeError:
            gas_ppm = 0.0

        spill = False
        try:
            spill = bool(self.floor_sensor.is_wet())
        except AttributeError:
            spill = False

        needs = (low_towels or bin_pct > self.bin_threshold_pct
                 or gas_ppm > self.gas_threshold_ppm or spill)
        return bool(needs and entries >= self.entries_threshold)

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a compact snapshot suitable for JSON, summarising the
        current state of the facility with respect to service triggers.
        """
        try:
            entries = self.door_counter.count_delta()
        except AttributeError:
            entries = 0

        pct_towels = self._disp_percent_left()
        try:
            bin_pct = float(self.bin_sensor.percent_full())
        except AttributeError:
            bin_pct = 0.0

        try:
            gas_ppm = float(self.gas_sensor.ppm())
        except AttributeError:
            gas_ppm = 0.0

        try:
            spill = bool(self.floor_sensor.is_wet())
        except AttributeError:
            spill = False

        return {
            "entries_threshold": self.entries_threshold,
            "entries_approx": entries,
            "towel_pct": pct_towels,
            "bin_pct": bin_pct,
            "nh3_ppm": gas_ppm,
            "spill": spill,
            "needs_service": self.needs_service(),
        }

from __future__ import annotations

from typing import Any, Dict, List

from spaxiom.intent.pattern import Pattern, ServiceNeeded


class FmSteward(Pattern):
    """
    Facilities-management steward helper.

    Encapsulates the concept of "needs service" based on a small set of
    restroom / consumable / air-quality sensors.

    Inherits from Pattern to support update/emit/depends_on interface.
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
        name: str = "fm_steward",
    ) -> None:
        super().__init__(name=name)
        self.door_counter = door_counter
        self.towel_sensor = towel_sensor
        self.bin_sensor = bin_sensor
        self.gas_sensor = gas_sensor
        self.floor_sensor = floor_sensor

        self.entries_threshold = entries_threshold
        self.towel_threshold_pct = towel_threshold_pct
        self.bin_threshold_pct = bin_threshold_pct
        self.gas_threshold_ppm = gas_threshold_ppm

        # Track previous service state to emit events only on transition
        self._prev_needs_service = False
        self._prev_reasons: Dict[str, bool] = {
            "low_towels": False,
            "bin_full": False,
            "gas_high": False,
            "spill": False,
        }

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

        needs = (
            low_towels
            or bin_pct > self.bin_threshold_pct
            or gas_ppm > self.gas_threshold_ppm
            or spill
        )
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

    # Pattern interface methods

    def update(self, dt: float, context: Dict[str, Any]) -> None:
        """Update pattern state and emit events when service conditions change.

        Args:
            dt: Time delta since last tick in seconds
            context: Tick context (sensor values, other pattern states)
        """
        # Check each service condition
        low_towels = self._disp_percent_left() < self.towel_threshold_pct

        try:
            bin_pct = float(self.bin_sensor.percent_full())
        except AttributeError:
            bin_pct = 0.0
        bin_full = bin_pct > self.bin_threshold_pct

        try:
            gas_ppm = float(self.gas_sensor.ppm())
        except AttributeError:
            gas_ppm = 0.0
        gas_high = gas_ppm > self.gas_threshold_ppm

        try:
            spill = bool(self.floor_sensor.is_wet())
        except AttributeError:
            spill = False

        # Emit events for conditions that just became true
        current_reasons = {
            "low_towels": low_towels,
            "bin_full": bin_full,
            "gas_high": gas_high,
            "spill": spill,
        }

        for reason, is_triggered in current_reasons.items():
            if is_triggered and not self._prev_reasons.get(reason, False):
                details = {"value": None}
                if reason == "low_towels":
                    details["value"] = self._disp_percent_left()
                elif reason == "bin_full":
                    details["value"] = bin_pct
                elif reason == "gas_high":
                    details["value"] = gas_ppm
                elif reason == "spill":
                    details["value"] = True

                self._emit_event(
                    ServiceNeeded(
                        facility=self._name,
                        reason=reason,
                        details=details,
                    )
                )

        self._prev_reasons = current_reasons

    def depends_on(self) -> List[Any]:
        """Return list of dependencies for ordering.

        Returns:
            List containing all sensors this pattern depends on.
        """
        return [
            self.door_counter,
            self.towel_sensor,
            self.bin_sensor,
            self.gas_sensor,
            self.floor_sensor,
        ]

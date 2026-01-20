#!/usr/bin/env python3
"""Facilities management demo for Spaxiom CLI."""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom.intent import FmSteward, ServiceNeeded
from spaxiom.sim.sensors import SimulatedAnalogSensor, SimulatedBinarySensor
from spaxiom.zone import Zone


class SimulatedDoorCounter(SimulatedAnalogSensor):
    def count_delta(self) -> float:
        return float(max(0.0, self.read()))


class SimulatedSupplySensor(SimulatedAnalogSensor):
    def percent_remaining(self) -> float:
        return float(max(0.0, min(100.0, self.read())))


class SimulatedBinSensor(SimulatedAnalogSensor):
    def percent_full(self) -> float:
        return float(max(0.0, min(100.0, self.read())))


class SimulatedAirQualitySensor(SimulatedAnalogSensor):
    def ppm(self) -> float:
        return float(max(0.0, self.read()))


class SimulatedFloorSensor(SimulatedBinarySensor):
    def is_wet(self) -> bool:
        return bool(self.read())


def _print_dashboard(snapshot: Dict[str, str]) -> None:
    print("\033[2J\033[H", end="")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                 FACILITIES MANAGEMENT DASHBOARD              ║")
    print("║                       Restroom 2A                             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                               ║")
    print(f"║  Status: {snapshot['status']:<53}║")
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  UTILIZATION & ENVIRONMENT:                                   ║")
    print("║                                                               ║")
    print(
        f"║  Estimated entries: {snapshot['entries']:>5} (threshold {snapshot['threshold']:>3})          ║"
    )
    print(
        f"║  Air quality (NH3): {snapshot['nh3_ppm']:>5} ppm                             ║"
    )
    print(
        f"║  Floor wet:          {snapshot['spill']:<5}                                   ║"
    )
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  SUPPLY LEVELS:                                               ║")
    print("║                                                               ║")
    print(
        f"║  Towel remaining:   {snapshot['towel_pct']:>5}%                              ║"
    )
    print(
        f"║  Bin fill level:    {snapshot['bin_pct']:>5}%                              ║"
    )
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  RECENT SERVICE ALERTS:                                       ║")
    print("║                                                               ║")
    for line in snapshot["alerts"]:
        print(f"║  {line:<60}║")
    print("╚══════════════════════════════════════════════════════════════╝")


def main() -> None:
    zone = Zone(0, 0, 18, 12)
    zone.name = "Restroom_2A"

    door_counter = SimulatedDoorCounter(
        name="door_counter_2a",
        location=(1.5, 6.0, 1.2),
        base=120.0,
        min_value=0.0,
        max_value=2000.0,
        noise_std=2.0,
        drift_per_s=0.03,
        seed=7,
    )
    towel_supply = SimulatedSupplySensor(
        name="towel_supply_2a",
        location=(2.5, 10.0, 1.6),
        base=55.0,
        min_value=0.0,
        max_value=100.0,
        noise_std=1.5,
        drift_per_s=-0.01,
        seed=8,
    )
    bin_sensor = SimulatedBinSensor(
        name="bin_fill_2a",
        location=(3.5, 2.5, 0.2),
        base=45.0,
        min_value=0.0,
        max_value=100.0,
        noise_std=1.0,
        drift_per_s=0.02,
        seed=9,
    )
    air_quality = SimulatedAirQualitySensor(
        name="air_quality_2a",
        location=(9.0, 6.0, 2.4),
        base=8.0,
        min_value=0.0,
        max_value=40.0,
        noise_std=1.0,
        spike_probability=0.05,
        spike_delta=15.0,
        spike_duration_s=300.0,
        seed=12,
    )
    floor_wet = SimulatedFloorSensor(
        name="floor_wet_2a",
        location=(7.0, 6.0, 0.0),
        probability_on=0.05,
        min_on_s=30.0,
        min_off_s=600.0,
        seed=15,
    )

    steward = FmSteward(
        door_counter=door_counter,
        towel_sensor=towel_supply,
        bin_sensor=bin_sensor,
        gas_sensor=air_quality,
        floor_sensor=floor_wet,
        entries_threshold=140,
        towel_threshold_pct=20.0,
        bin_threshold_pct=80.0,
        gas_threshold_ppm=20.0,
        name=zone.name,
    )

    alerts: List[str] = []
    print("Starting facilities management demo. Press Ctrl+C to stop.")

    try:
        while True:
            steward.update(0.2, {})
            events = steward.emit()
            for event in events:
                if isinstance(event, ServiceNeeded):
                    alerts.insert(
                        0,
                        f"[{time.strftime('%H:%M:%S')}] {event.reason} (value={event.details.get('value')})",
                    )

            alerts = alerts[:5] or ["(no alerts)"]
            snapshot = steward.snapshot()

            status = "✓ Normal"
            if snapshot["needs_service"]:
                status = "⚠ Service required"

            dashboard = {
                "status": status,
                "entries": f"{int(snapshot['entries_approx'])}",
                "threshold": f"{int(snapshot['entries_threshold'])}",
                "nh3_ppm": f"{snapshot['nh3_ppm']:.1f}",
                "spill": "YES" if snapshot["spill"] else "no",
                "towel_pct": f"{snapshot['towel_pct']:.1f}",
                "bin_pct": f"{snapshot['bin_pct']:.1f}",
                "alerts": alerts,
            }

            _print_dashboard(dashboard)
            time.sleep(0.6)

    except KeyboardInterrupt:
        print("\nExiting facilities demo.")


if __name__ == "__main__":
    main()

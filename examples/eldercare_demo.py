#!/usr/bin/env python3
"""Elder-care daily living demo for Spaxiom CLI."""

from __future__ import annotations

import os
import sys
import time
from typing import List, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom.intent import ADLTracker, ADLEvent
from spaxiom.sim.sensors import SimulatedAnalogSensor, SimulatedBinarySensor
from spaxiom.zone import Zone


def _print_dashboard(snapshot: Dict[str, str]) -> None:
    print("\033[2J\033[H", end="")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              ELDER-CARE DAILY LIVING DASHBOARD               ║")
    print("║                     Apartment 12B                            ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                               ║")
    print(f"║  Status: {snapshot['status']:<53}║")
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  DAILY ACTIVITY COUNTS:                                      ║")
    print("║                                                               ║")
    print(
        f"║  Got out of bed:     {snapshot['got_up']:>3} times                              ║"
    )
    print(
        f"║  Meal events:        {snapshot['meal']:>3} times                              ║"
    )
    print(
        f"║  Bathroom visits:    {snapshot['bath']:>3} times                              ║"
    )
    print(
        f"║  Hallway walks:      {snapshot['walk']:>3} times                              ║"
    )
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  RECENT EVENTS:                                               ║")
    print("║                                                               ║")
    for line in snapshot["recent_events"]:
        print(f"║  {line:<60}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  CARE TEAM NOTES:                                             ║")
    print("║                                                               ║")
    for line in snapshot["notes"]:
        print(f"║  {line:<60}║")
    print("╚══════════════════════════════════════════════════════════════╝")


def main() -> None:
    zone = Zone(0, 0, 16, 12)
    zone.name = "Apartment_12B"

    bed_sensor = SimulatedBinarySensor(
        name="bed_mat_12b",
        location=(3.0, 9.0, 0.5),
        probability_on=0.4,
        min_on_s=120.0,
        min_off_s=300.0,
        seed=21,
    )
    fridge_sensor = SimulatedBinarySensor(
        name="fridge_door_12b",
        location=(12.0, 8.0, 0.5),
        probability_on=0.2,
        min_on_s=5.0,
        min_off_s=180.0,
        seed=31,
    )
    bath_sensor = SimulatedAnalogSensor(
        name="bath_humidity_12b",
        location=(13.5, 2.5, 1.8),
        base=45.0,
        min_value=35.0,
        max_value=85.0,
        noise_std=2.0,
        spike_probability=0.08,
        spike_delta=25.0,
        spike_duration_s=600.0,
        seed=11,
    )
    hall_sensor = SimulatedBinarySensor(
        name="hall_floor_grid_12b",
        location=(7.5, 5.0, 0.0),
        probability_on=0.3,
        min_on_s=10.0,
        min_off_s=60.0,
        seed=41,
    )

    tracker = ADLTracker(
        bed_sensor=bed_sensor,
        fridge_sensor=fridge_sensor,
        bath_sensor=bath_sensor,
        hall_sensor=hall_sensor,
        name=zone.name,
    )

    recent_events: List[str] = []
    notes = [
        "Routine stable; continue monitoring.",
        "No anomalies detected in last 6 hours.",
        "Next check-in scheduled at 6 PM.",
    ]

    print("Starting elder-care daily living demo. Press Ctrl+C to stop.")
    try:
        while True:
            events = tracker.update(0.2, {}) or []

            for event in events:
                if isinstance(event, ADLEvent):
                    recent_events.insert(
                        0,
                        f"[{time.strftime('%H:%M:%S')}] {event.activity} ({event.count_today} today)",
                    )

            recent_events = recent_events[:5] or ["(no events yet)"]
            counts = tracker.daily_counts()

            status = "✓ Normal routine"
            if counts["walk"] == 0 and counts["meal"] == 0:
                status = "⚠ No activity detected"

            snapshot = {
                "status": status,
                "got_up": f"{counts['got_up']}",
                "meal": f"{counts['meal']}",
                "bath": f"{counts['bath']}",
                "walk": f"{counts['walk']}",
                "recent_events": recent_events,
                "notes": notes,
            }

            _print_dashboard(snapshot)
            time.sleep(0.6)

    except KeyboardInterrupt:
        print("\nExiting elder-care demo.")


if __name__ == "__main__":
    main()

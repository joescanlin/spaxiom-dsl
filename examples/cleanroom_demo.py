#!/usr/bin/env python3
"""Cleanroom contamination risk demo for Spaxiom CLI."""

from __future__ import annotations

import os
import sys
import time
from typing import List, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Zone
from spaxiom.intent import (
    CleanroomRisk,
    ContaminationRiskUpdated,
    PressureBreach,
    ParticleExcursion,
    AirlockViolation,
    HighRiskMovement,
)
from spaxiom.sim.sensors import SimulatedAnalogSensor, SimulatedBinarySensor


def _print_dashboard(snapshot: Dict[str, str]) -> None:
    print("\033[2J\033[H", end="")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           CLEANROOM CONTAMINATION MONITOR                     ║")
    print("║                   ISO7_bio_room_3                             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                               ║")
    print(
        f"║  CONTAMINATION RISK INDEX:  {snapshot['cri_bar']}  {snapshot['cri_value']}          ║"
    )
    print(f"║  Status: {snapshot['status']}                                     ║")
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  COMPONENT BREAKDOWN (last hour):                             ║")
    print("║                                                               ║")
    print(
        f"║  Pressure Breaches:        {snapshot['breach_seconds']:>6} breach-seconds              ║"
    )
    print(
        f"║    └─ Anteroom boundary:   {snapshot['breach_anteroom']:>6}s (below 5.0 Pa)              ║"
    )
    print(
        f"║    └─ Corridor boundary:   {snapshot['breach_corridor']:>6}s (below 12.5 Pa)             ║"
    )
    print("║                                                               ║")
    print(
        f"║  Particle Excursion:       {snapshot['particle_excursion']:>10} count·seconds               ║"
    )
    print(
        f"║    └─ Peak: {snapshot['particle_peak']:>7}/m³ (ISO limit: 352,000)      ║"
    )
    print(
        f"║    └─ Duration above limit: {snapshot['particle_duration']:>5} minutes                      ║"
    )
    print("║                                                               ║")
    print(
        f"║  Airlock Violations:       {snapshot['airlock_violations']:>3} events                          ║"
    )
    print("║                                                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  RECENT EVENTS:                                               ║")
    print("║                                                               ║")
    for line in snapshot["recent_events"]:
        print(f"║  {line:<60}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  RECOMMENDATIONS:                                             ║")
    print("║                                                               ║")
    for line in snapshot["recommendations"]:
        print(f"║  {line:<60}║")
    print("╚══════════════════════════════════════════════════════════════╝")


def main() -> None:
    zone = Zone(0, 0, 30, 20)
    zone.name = "ISO7_bio_room_3"

    particle_sensor = SimulatedAnalogSensor(
        name="particle_counter_z3",
        location=(12.5, 8.2, 2.8),
        base=280000.0,
        min_value=10000.0,
        max_value=600000.0,
        noise_std=15000.0,
        spike_probability=0.05,
        spike_delta=120000.0,
        spike_duration_s=20.0,
    )

    dp_anteroom = SimulatedAnalogSensor(
        name="dp_z3_anteroom",
        location=(11.5, 7.5, 2.8),
        base=8.0,
        min_value=0.0,
        max_value=20.0,
        noise_std=0.8,
        spike_probability=0.06,
        spike_delta=-6.0,
        spike_duration_s=10.0,
    )

    dp_corridor = SimulatedAnalogSensor(
        name="dp_z3_corridor",
        location=(13.5, 7.5, 2.8),
        base=13.0,
        min_value=0.0,
        max_value=25.0,
        noise_std=0.8,
        spike_probability=0.05,
        spike_delta=-7.0,
        spike_duration_s=10.0,
    )

    airlock_3a = SimulatedBinarySensor(
        name="airlock_3a_violation",
        location=(9.0, 4.0, 0.0),
        probability_on=0.03,
        min_on_s=2.0,
        min_off_s=10.0,
    )
    airlock_3b = SimulatedBinarySensor(
        name="airlock_3b_violation",
        location=(16.0, 4.0, 0.0),
        probability_on=0.02,
        min_on_s=2.0,
        min_off_s=12.0,
    )

    temp_sensor = SimulatedAnalogSensor(
        name="temp_z3",
        location=(12.5, 8.2, 2.0),
        base=21.5,
        min_value=19.0,
        max_value=24.0,
        noise_std=0.2,
        spike_probability=0.01,
        spike_delta=1.2,
        spike_duration_s=60.0,
    )

    rh_sensor = SimulatedAnalogSensor(
        name="rh_z3",
        location=(12.8, 8.2, 2.0),
        base=42.0,
        min_value=30.0,
        max_value=55.0,
        noise_std=1.5,
        spike_probability=0.02,
        spike_delta=6.0,
        spike_duration_s=60.0,
    )

    occupancy_sensor = SimulatedAnalogSensor(
        name="occupancy_z3",
        location=(12.0, 8.0, 2.5),
        base=6.0,
        min_value=0.0,
        max_value=20.0,
        noise_std=1.2,
        spike_probability=0.04,
        spike_delta=8.0,
        spike_duration_s=120.0,
    )

    pattern = CleanroomRisk(
        name="ISO7_bio_room_3",
        zone=zone,
        particle_sensor=particle_sensor,
        dp_sensors={"anteroom": dp_anteroom, "corridor": dp_corridor},
        airlock_sensors=[airlock_3a, airlock_3b],
        temperature_sensor=temp_sensor,
        humidity_sensor=rh_sensor,
        occupancy_sensor=occupancy_sensor,
    )

    recent_events: List[str] = []
    particle_peak = 0.0
    particle_duration = 0.0
    last_particle_over = None
    breach_anteroom = 0.0
    breach_corridor = 0.0

    print("Starting cleanroom demo. Press Ctrl+C to stop.")
    try:
        while True:
            events = pattern.update(0.1, {})

            for event in events:
                if isinstance(event, ContaminationRiskUpdated):
                    breach_anteroom = event.breach_seconds * 0.65
                    breach_corridor = event.breach_seconds - breach_anteroom
                if isinstance(event, ParticleExcursion):
                    particle_peak = max(particle_peak, event.count_per_m3)
                    now = time.time()
                    if last_particle_over is None:
                        last_particle_over = now
                if isinstance(event, PressureBreach):
                    recent_events.insert(
                        0,
                        f"[{time.strftime('%H:%M:%S')}] PressureBreach {event.boundary}",
                    )
                if isinstance(event, AirlockViolation):
                    recent_events.insert(
                        0,
                        f"[{time.strftime('%H:%M:%S')}] AirlockViolation {event.airlock_id}",
                    )
                if isinstance(event, HighRiskMovement):
                    recent_events.insert(
                        0,
                        f"[{time.strftime('%H:%M:%S')}] HighRiskMovement occupancy={event.occupancy:.0f}",
                    )

            if particle_peak > 0 and last_particle_over is not None:
                particle_duration = max(0.0, (time.time() - last_particle_over) / 60.0)
            else:
                last_particle_over = None

            cri = pattern._last_cri or 0.0
            bar_count = int(cri * 10)
            cri_bar = "█" * bar_count + "░" * (10 - bar_count)

            if cri >= 0.7:
                status = "⚠ ELEVATED RISK"
                recommendations = [
                    "1. Delay batch start 15 minutes for particle settle",
                    "2. Schedule airlock procedure refresher",
                    "3. Check anteroom HEPA differential pressure",
                ]
            else:
                status = "✓ NORMAL"
                recommendations = [
                    "1. Continue monitoring",
                    "2. Verify next gowning audit schedule",
                    "3. Review next maintenance window",
                ]

            if not recent_events:
                recent_events = ["(no events yet)"]
            recent_events = recent_events[:5]

            snapshot = {
                "cri_bar": cri_bar,
                "cri_value": f"{cri:.2f} / 1.00",
                "status": status,
                "breach_seconds": f"{breach_anteroom + breach_corridor:6.1f}",
                "breach_anteroom": f"{breach_anteroom:6.1f}",
                "breach_corridor": f"{breach_corridor:6.1f}",
                "particle_excursion": f"{pattern._particle_excursion():.1e}",
                "particle_peak": f"{particle_peak:,.0f}",
                "particle_duration": f"{particle_duration:4.1f}",
                "airlock_violations": f"{pattern._airlock_violations():2d}",
                "recent_events": recent_events,
                "recommendations": recommendations,
            }

            _print_dashboard(snapshot)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nExiting cleanroom demo.")


if __name__ == "__main__":
    main()

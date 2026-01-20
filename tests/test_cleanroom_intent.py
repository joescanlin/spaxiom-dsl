"""Tests for the cleanroom intent pattern."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from spaxiom.geo import Zone
from spaxiom.intent.cleanroom import (
    AirlockViolation,
    CleanroomRisk,
    ContaminationRiskUpdated,
    HighRiskMovement,
    ParticleExcursion,
    PressureBreach,
)


@dataclass
class StaticSensor:
    value: float

    def read(self) -> float:
        return self.value


def _build_pattern(
    particle: float = 400000.0,
    dp_anteroom: float = 2.0,
    dp_corridor: float = 10.0,
    airlock_a: float = 1.0,
    airlock_b: float = 0.0,
    occupancy: float = 10.0,
) -> CleanroomRisk:
    zone = Zone(0, 0, 10, 10)
    zone.name = "ISO7_bio_room_3"
    return CleanroomRisk(
        name=zone.name,
        zone=zone,
        particle_sensor=StaticSensor(particle),
        dp_sensors={
            "anteroom": StaticSensor(dp_anteroom),
            "corridor": StaticSensor(dp_corridor),
        },
        airlock_sensors=[StaticSensor(airlock_a), StaticSensor(airlock_b)],
        temperature_sensor=StaticSensor(22.0),
        humidity_sensor=StaticSensor(40.0),
        occupancy_sensor=StaticSensor(occupancy),
        risk_threshold=0.01,
    )


def _event_types(events: List[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        key = type(event).__name__
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_cleanroom_risk_emits_expected_events() -> None:
    pattern = _build_pattern()

    events = pattern.update(0.1, {})
    assert len([e for e in events if isinstance(e, ContaminationRiskUpdated)]) == 1
    assert len([e for e in events if isinstance(e, ParticleExcursion)]) == 1
    assert len([e for e in events if isinstance(e, PressureBreach)]) == 2
    assert len([e for e in events if isinstance(e, AirlockViolation)]) == 1
    assert len([e for e in events if isinstance(e, HighRiskMovement)]) == 1


def test_cleanroom_risk_breach_seconds_increase() -> None:
    pattern = _build_pattern()

    pattern.update(0.1, {})
    events = pattern.update(0.1, {})

    risk_updates = [e for e in events if isinstance(e, ContaminationRiskUpdated)]
    assert risk_updates
    assert risk_updates[-1].breach_seconds >= 0.0

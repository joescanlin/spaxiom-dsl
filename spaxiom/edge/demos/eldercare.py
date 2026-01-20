"""Elder-care ADL demo seed for edge UI and CLI."""

from __future__ import annotations

from typing import Dict, Tuple

from spaxiom.edge.database import (
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
)


def _ensure_sensor(
    repo: SensorRepository,
    name: str,
    sensor_type: str,
    location: Tuple[float, float, float],
    config: Dict,
) -> str:
    existing = repo.get_by_name(name)
    if existing:
        return existing.id
    record = repo.create(
        name=name,
        sensor_type=sensor_type,
        location=location,
        config=config,
        enabled=True,
    )
    return record.id


def _ensure_zone(repo: ZoneRepository, name: str, geometry: Dict) -> str:
    existing = repo.get_by_name(name)
    if existing:
        return existing.id
    record = repo.create(
        name=name,
        zone_type="rectangle",
        geometry=geometry,
        metadata={"demo": "eldercare"},
    )
    return record.id


def _ensure_pattern(
    repo: PatternRepository,
    name: str,
    pattern_type: str,
    config: Dict,
    zones: list,
    sensors: list,
) -> str:
    existing = repo.get_by_name(name)
    if existing:
        return existing.id
    record = repo.create(
        name=name,
        pattern_type=pattern_type,
        config=config,
        zones=zones,
        sensors=sensors,
        enabled=True,
    )
    return record.id


def _ensure_agent(
    repo: AgentRepository, name: str, pattern_id: str, config: Dict
) -> str:
    existing = repo.get_all()
    for agent in existing:
        if agent.name == name:
            return agent.id
    record = repo.create(
        name=name,
        pattern_id=pattern_id,
        config=config,
    )
    return record.id


def seed_eldercare_demo(db: EdgeDatabase) -> Dict[str, str]:
    """Seed elder-care ADL demo sensors, zones, pattern, and agent."""
    sensors = SensorRepository(db)
    zones = ZoneRepository(db)
    patterns = PatternRepository(db)
    agents = AgentRepository(db)

    unit_zone_id = _ensure_zone(
        zones,
        name="Apartment_12B",
        geometry={"x": 0, "y": 0, "width": 16, "height": 12},
    )

    bed_id = _ensure_sensor(
        sensors,
        name="bed_mat_12b",
        sensor_type="sim_binary",
        location=(3.0, 9.0, 0.5),
        config={
            "probability_on": 0.4,
            "min_on_s": 120.0,
            "min_off_s": 300.0,
            "seed": 21,
        },
    )

    fridge_id = _ensure_sensor(
        sensors,
        name="fridge_door_12b",
        sensor_type="sim_binary",
        location=(12.0, 8.0, 0.5),
        config={
            "probability_on": 0.2,
            "min_on_s": 5.0,
            "min_off_s": 180.0,
            "seed": 31,
        },
    )

    bath_id = _ensure_sensor(
        sensors,
        name="bath_humidity_12b",
        sensor_type="sim_analog",
        location=(13.5, 2.5, 1.8),
        config={
            "base": 45.0,
            "min_value": 35.0,
            "max_value": 85.0,
            "noise_std": 2.0,
            "spike_probability": 0.08,
            "spike_delta": 25.0,
            "spike_duration_s": 600.0,
            "seed": 11,
        },
    )

    hall_id = _ensure_sensor(
        sensors,
        name="hall_floor_grid_12b",
        sensor_type="sim_binary",
        location=(7.5, 5.0, 0.0),
        config={
            "probability_on": 0.3,
            "min_on_s": 10.0,
            "min_off_s": 60.0,
            "seed": 41,
        },
    )

    pattern_id = _ensure_pattern(
        patterns,
        name="ElderCare ADL Tracker",
        pattern_type="adl_tracker",
        config={"name": "Apartment_12B"},
        zones=[unit_zone_id],
        sensors=[bed_id, fridge_id, bath_id, hall_id],
    )

    agent_id = _ensure_agent(
        agents,
        name="Daily Living Agent",
        pattern_id=pattern_id,
        config={"demo": "eldercare"},
    )

    return {
        "zone_id": unit_zone_id,
        "pattern_id": pattern_id,
        "agent_id": agent_id,
    }

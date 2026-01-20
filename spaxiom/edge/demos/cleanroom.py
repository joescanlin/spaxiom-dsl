"""Cleanroom demo seed for edge UI and CLI."""

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
        metadata={"demo": "cleanroom"},
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


def seed_cleanroom_demo(db: EdgeDatabase) -> Dict[str, str]:
    """Seed cleanroom demo sensors, zones, pattern, and agent.

    Returns:
        Dict with ids: zone_id, pattern_id, agent_id
    """
    sensors = SensorRepository(db)
    zones = ZoneRepository(db)
    patterns = PatternRepository(db)
    agents = AgentRepository(db)

    zone_id = _ensure_zone(
        zones,
        name="ISO7_bio_room_3",
        geometry={"x": 0, "y": 0, "width": 30, "height": 20},
    )

    particle_id = _ensure_sensor(
        sensors,
        name="particle_counter_z3",
        sensor_type="sim_analog",
        location=(12.5, 8.2, 2.8),
        config={
            "base": 280000.0,
            "min_value": 10000.0,
            "max_value": 600000.0,
            "noise_std": 15000.0,
            "spike_probability": 0.05,
            "spike_delta": 120000.0,
            "spike_duration_s": 20.0,
        },
    )

    dp_anteroom_id = _ensure_sensor(
        sensors,
        name="dp_z3_anteroom",
        sensor_type="sim_analog",
        location=(11.5, 7.5, 2.8),
        config={
            "base": 8.0,
            "min_value": 0.0,
            "max_value": 20.0,
            "noise_std": 0.8,
            "spike_probability": 0.06,
            "spike_delta": -6.0,
            "spike_duration_s": 10.0,
        },
    )

    dp_corridor_id = _ensure_sensor(
        sensors,
        name="dp_z3_corridor",
        sensor_type="sim_analog",
        location=(13.5, 7.5, 2.8),
        config={
            "base": 13.0,
            "min_value": 0.0,
            "max_value": 25.0,
            "noise_std": 0.8,
            "spike_probability": 0.05,
            "spike_delta": -7.0,
            "spike_duration_s": 10.0,
        },
    )

    airlock_3a_id = _ensure_sensor(
        sensors,
        name="airlock_3a_violation",
        sensor_type="sim_binary",
        location=(9.0, 4.0, 0.0),
        config={
            "probability_on": 0.03,
            "min_on_s": 2.0,
            "min_off_s": 10.0,
        },
    )

    airlock_3b_id = _ensure_sensor(
        sensors,
        name="airlock_3b_violation",
        sensor_type="sim_binary",
        location=(16.0, 4.0, 0.0),
        config={
            "probability_on": 0.02,
            "min_on_s": 2.0,
            "min_off_s": 12.0,
        },
    )

    temp_id = _ensure_sensor(
        sensors,
        name="temp_z3",
        sensor_type="sim_analog",
        location=(12.5, 8.2, 2.0),
        config={
            "base": 21.5,
            "min_value": 19.0,
            "max_value": 24.0,
            "noise_std": 0.2,
            "spike_probability": 0.01,
            "spike_delta": 1.2,
            "spike_duration_s": 60.0,
        },
    )

    rh_id = _ensure_sensor(
        sensors,
        name="rh_z3",
        sensor_type="sim_analog",
        location=(12.8, 8.2, 2.0),
        config={
            "base": 42.0,
            "min_value": 30.0,
            "max_value": 55.0,
            "noise_std": 1.5,
            "spike_probability": 0.02,
            "spike_delta": 6.0,
            "spike_duration_s": 60.0,
        },
    )

    occupancy_id = _ensure_sensor(
        sensors,
        name="occupancy_z3",
        sensor_type="sim_analog",
        location=(12.0, 8.0, 2.5),
        config={
            "base": 6.0,
            "min_value": 0.0,
            "max_value": 20.0,
            "noise_std": 1.2,
            "spike_probability": 0.04,
            "spike_delta": 8.0,
            "spike_duration_s": 120.0,
        },
    )

    pattern_id = _ensure_pattern(
        patterns,
        name="Cleanroom Risk Monitor",
        pattern_type="cleanroom_risk",
        config={
            "zone_name": "ISO7_bio_room_3",
            "max_particles": 352000,
            "min_dp_anteroom_pa": 5.0,
            "min_dp_corridor_pa": 12.5,
            "alpha": 1e-3,
            "beta": 1e-6,
            "gamma": 1.0,
        },
        zones=[zone_id],
        sensors=[
            particle_id,
            dp_anteroom_id,
            dp_corridor_id,
            airlock_3a_id,
            airlock_3b_id,
            temp_id,
            rh_id,
            occupancy_id,
        ],
    )

    agent_id = _ensure_agent(
        agents,
        name="Cleanroom Risk Agent",
        pattern_id=pattern_id,
        config={"demo": "cleanroom"},
    )

    return {
        "zone_id": zone_id,
        "pattern_id": pattern_id,
        "agent_id": agent_id,
    }

"""Facilities management demo seed for edge UI and CLI."""

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
        metadata={"demo": "facilities"},
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


def seed_facilities_demo(db: EdgeDatabase) -> Dict[str, str]:
    """Seed facilities management demo sensors, zones, pattern, and agent."""
    sensors = SensorRepository(db)
    zones = ZoneRepository(db)
    patterns = PatternRepository(db)
    agents = AgentRepository(db)

    zone_id = _ensure_zone(
        zones,
        name="Restroom_2A",
        geometry={"x": 0, "y": 0, "width": 18, "height": 12},
    )

    door_counter_id = _ensure_sensor(
        sensors,
        name="door_counter_2a",
        sensor_type="sim_analog",
        location=(1.5, 6.0, 1.2),
        config={
            "base": 120.0,
            "min_value": 0.0,
            "max_value": 2000.0,
            "noise_std": 2.0,
            "drift_per_s": 0.03,
            "seed": 7,
        },
    )

    towel_supply_id = _ensure_sensor(
        sensors,
        name="towel_supply_2a",
        sensor_type="sim_analog",
        location=(2.5, 10.0, 1.6),
        config={
            "base": 55.0,
            "min_value": 0.0,
            "max_value": 100.0,
            "noise_std": 1.5,
            "drift_per_s": -0.01,
            "seed": 8,
        },
    )

    bin_fill_id = _ensure_sensor(
        sensors,
        name="bin_fill_2a",
        sensor_type="sim_analog",
        location=(3.5, 2.5, 0.2),
        config={
            "base": 45.0,
            "min_value": 0.0,
            "max_value": 100.0,
            "noise_std": 1.0,
            "drift_per_s": 0.02,
            "seed": 9,
        },
    )

    air_quality_id = _ensure_sensor(
        sensors,
        name="air_quality_2a",
        sensor_type="sim_analog",
        location=(9.0, 6.0, 2.4),
        config={
            "base": 8.0,
            "min_value": 0.0,
            "max_value": 40.0,
            "noise_std": 1.0,
            "spike_probability": 0.05,
            "spike_delta": 15.0,
            "spike_duration_s": 300.0,
            "seed": 12,
        },
    )

    floor_wet_id = _ensure_sensor(
        sensors,
        name="floor_wet_2a",
        sensor_type="sim_binary",
        location=(7.0, 6.0, 0.0),
        config={
            "probability_on": 0.05,
            "min_on_s": 30.0,
            "min_off_s": 600.0,
            "seed": 15,
        },
    )

    pattern_id = _ensure_pattern(
        patterns,
        name="Facilities Steward - Restroom 2A",
        pattern_type="fm_steward",
        config={
            "entries_threshold": 140,
            "towel_threshold_pct": 20.0,
            "bin_threshold_pct": 80.0,
            "gas_threshold_ppm": 20.0,
        },
        zones=[zone_id],
        sensors=[
            door_counter_id,
            towel_supply_id,
            bin_fill_id,
            air_quality_id,
            floor_wet_id,
        ],
    )

    agent_id = _ensure_agent(
        agents,
        name="Facilities Service Agent",
        pattern_id=pattern_id,
        config={"demo": "facilities"},
    )

    return {
        "zone_id": zone_id,
        "pattern_id": pattern_id,
        "agent_id": agent_id,
    }

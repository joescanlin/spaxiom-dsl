"""Pattern API endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    PatternCreate,
    PatternUpdate,
    PatternResponse,
    PatternTypeInfo,
    PatternTestResult,
)
from spaxiom.edge.api.dependencies import (
    get_pattern_repo,
    get_zone_repo,
    get_sensor_repo,
)
from spaxiom.edge.database import PatternRepository, ZoneRepository, SensorRepository

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

# Pattern types with full metadata and config schemas
PATTERN_TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "occupancy_field": {
        "name": "Occupancy Field",
        "description": "Tracks occupancy levels across zones using sensor data",
        "config_schema": {
            "type": "object",
            "properties": {
                "decay_rate": {
                    "type": "number",
                    "default": 0.1,
                    "description": "Rate at which occupancy decays over time",
                },
                "threshold_low": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Low occupancy threshold",
                },
                "threshold_high": {
                    "type": "number",
                    "default": 0.7,
                    "description": "High occupancy threshold",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": ["occupancy_changed", "zone_entered", "zone_exited"],
    },
    "queue_flow": {
        "name": "Queue Flow",
        "description": "Monitors queue formation and estimates wait times",
        "config_schema": {
            "type": "object",
            "properties": {
                "max_queue_length": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum expected queue length",
                },
                "alert_wait_time_seconds": {
                    "type": "number",
                    "default": 300,
                    "description": "Wait time threshold for alerts (seconds)",
                },
                "service_rate": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Expected service rate (customers per minute)",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": [
            "queue_length_changed",
            "wait_time_exceeded",
            "queue_cleared",
        ],
    },
    "adl_tracker": {
        "name": "ADL Tracker",
        "description": "Tracks Activities of Daily Living for eldercare applications",
        "config_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "default": "adl_tracker",
                    "description": "Display name for the ADL tracker",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": ["ADLEvent"],
    },
    "fm_steward": {
        "name": "Facility Management Steward",
        "description": "Monitors facility conditions and maintenance needs",
        "config_schema": {
            "type": "object",
            "properties": {
                "thresholds": {
                    "type": "object",
                    "description": "Sensor thresholds for alerts",
                },
                "check_interval_minutes": {
                    "type": "integer",
                    "default": 15,
                    "description": "How often to check conditions",
                },
            },
        },
        "requires_zones": False,
        "requires_sensors": True,
        "events_emitted": ["threshold_exceeded", "maintenance_due", "condition_normal"],
    },
    "cleanroom_risk": {
        "name": "Cleanroom Risk Monitor",
        "description": "Fuses pressure, particles, airlocks, and occupancy into CRI",
        "config_schema": {
            "type": "object",
            "properties": {
                "zone_name": {
                    "type": "string",
                    "default": "ISO7_bio_room_3",
                    "description": "Display name for the zone",
                },
                "max_particles": {
                    "type": "number",
                    "default": 352000,
                    "description": "ISO class particle limit",
                },
                "min_dp_anteroom_pa": {
                    "type": "number",
                    "default": 5.0,
                    "description": "Minimum anteroom differential pressure",
                },
                "min_dp_corridor_pa": {
                    "type": "number",
                    "default": 12.5,
                    "description": "Minimum corridor differential pressure",
                },
                "alpha": {
                    "type": "number",
                    "default": 0.001,
                    "description": "Breach-seconds weight",
                },
                "beta": {
                    "type": "number",
                    "default": 0.000001,
                    "description": "Particle excursion weight",
                },
                "gamma": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Airlock violations weight",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": [
            "contamination_risk_updated",
            "pressure_breach",
            "particle_excursion",
            "airlock_violation",
            "high_risk_movement",
        ],
    },
    "dwell_monitor": {
        "name": "Dwell Monitor",
        "description": "Monitors how long entities stay in zones",
        "config_schema": {
            "type": "object",
            "properties": {
                "min_dwell_seconds": {
                    "type": "number",
                    "default": 5,
                    "description": "Minimum time to count as dwelling",
                },
                "alert_dwell_seconds": {
                    "type": "number",
                    "default": 300,
                    "description": "Dwell time threshold for alerts",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": ["dwell_started", "dwell_ended", "long_dwell_alert"],
    },
    "path_tracker": {
        "name": "Path Tracker",
        "description": "Analyzes movement paths through zones",
        "config_schema": {
            "type": "object",
            "properties": {
                "track_history_minutes": {
                    "type": "integer",
                    "default": 30,
                    "description": "How long to keep path history",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": ["path_completed", "unusual_path_detected"],
    },
    "crowd_density": {
        "name": "Crowd Density",
        "description": "Monitors crowd density and flow patterns",
        "config_schema": {
            "type": "object",
            "properties": {
                "max_density": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Maximum safe density (people per square meter)",
                },
                "alert_density": {
                    "type": "number",
                    "default": 0.8,
                    "description": "Density threshold for alerts",
                },
            },
        },
        "requires_zones": True,
        "requires_sensors": True,
        "events_emitted": ["density_changed", "overcrowding_alert", "density_normal"],
    },
    "custom": {
        "name": "Custom Pattern",
        "description": "User-defined custom pattern with arbitrary configuration",
        "config_schema": {
            "type": "object",
            "additionalProperties": True,
        },
        "requires_zones": False,
        "requires_sensors": False,
        "events_emitted": [],
    },
}

# Simple mapping for backward compatibility
PATTERN_TYPES = {k: v["description"] for k, v in PATTERN_TYPE_REGISTRY.items()}


def _record_to_response(record) -> PatternResponse:
    """Convert a PatternRecord to PatternResponse."""
    return PatternResponse(
        id=record.id,
        name=record.name,
        pattern_type=record.pattern_type,
        config=record.config,
        zones=record.zones,
        sensors=record.sensors,
        enabled=record.enabled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/types", response_model=List[PatternTypeInfo])
async def list_pattern_types():
    """List available pattern types with full metadata."""
    return [
        PatternTypeInfo(
            type_id=type_id,
            name=info["name"],
            description=info["description"],
            config_schema=info["config_schema"],
            requires_zones=info["requires_zones"],
            requires_sensors=info["requires_sensors"],
            events_emitted=info["events_emitted"],
        )
        for type_id, info in PATTERN_TYPE_REGISTRY.items()
    ]


@router.get("/types/{type_id}", response_model=PatternTypeInfo)
async def get_pattern_type(type_id: str):
    """Get schema and info for a specific pattern type."""
    if type_id not in PATTERN_TYPE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern type '{type_id}' not found",
        )

    info = PATTERN_TYPE_REGISTRY[type_id]
    return PatternTypeInfo(
        type_id=type_id,
        name=info["name"],
        description=info["description"],
        config_schema=info["config_schema"],
        requires_zones=info["requires_zones"],
        requires_sensors=info["requires_sensors"],
        events_emitted=info["events_emitted"],
    )


@router.get("", response_model=List[PatternResponse])
async def list_patterns(
    enabled_only: bool = False,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """List all patterns."""
    records = repo.get_all(enabled_only=enabled_only)
    return [_record_to_response(r) for r in records]


@router.post("", response_model=PatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    pattern: PatternCreate,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """Create a new pattern."""
    # Check if pattern with this name exists
    existing = repo.get_by_name(pattern.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pattern with name '{pattern.name}' already exists",
        )

    # Validate pattern type
    if pattern.pattern_type not in PATTERN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern type. Available types: {list(PATTERN_TYPES.keys())}",
        )

    try:
        record = repo.create(
            name=pattern.name,
            pattern_type=pattern.pattern_type,
            config=pattern.config or {},
            zones=pattern.zones or [],
            sensors=pattern.sensors or [],
            enabled=pattern.enabled,
        )
        return _record_to_response(record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create pattern: {str(e)}",
        )


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(
    pattern_id: str,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """Get a pattern by ID."""
    record = repo.get(pattern_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )
    return _record_to_response(record)


@router.put("/{pattern_id}", response_model=PatternResponse)
async def update_pattern(
    pattern_id: str,
    pattern: PatternUpdate,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """Update a pattern."""
    record = repo.get(pattern_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )

    updates = pattern.model_dump(exclude_unset=True)

    # Validate pattern type if being updated
    if "pattern_type" in updates and updates["pattern_type"] not in PATTERN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern type. Available types: {list(PATTERN_TYPES.keys())}",
        )

    updated = repo.update(pattern_id, **updates)
    return _record_to_response(updated)


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: str,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """Delete a pattern."""
    deleted = repo.delete(pattern_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )


@router.post("/{pattern_id}/toggle", response_model=PatternResponse)
async def toggle_pattern(
    pattern_id: str,
    repo: PatternRepository = Depends(get_pattern_repo),
):
    """Toggle pattern enabled state."""
    record = repo.get(pattern_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )

    updated = repo.update(pattern_id, enabled=not record.enabled)
    return _record_to_response(updated)


@router.post("/{pattern_id}/test", response_model=PatternTestResult)
async def test_pattern(
    pattern_id: str,
    pattern_repo: PatternRepository = Depends(get_pattern_repo),
    zone_repo: ZoneRepository = Depends(get_zone_repo),
    sensor_repo: SensorRepository = Depends(get_sensor_repo),
):
    """Test a pattern configuration (dry run).

    Validates that the pattern configuration is correct and all
    referenced zones/sensors exist.
    """
    record = pattern_repo.get(pattern_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )

    errors = []
    warnings = []

    # Get pattern type info
    type_info = PATTERN_TYPE_REGISTRY.get(record.pattern_type)
    if not type_info:
        errors.append(f"Unknown pattern type: {record.pattern_type}")
        return PatternTestResult(
            pattern_id=pattern_id,
            valid=False,
            errors=errors,
            warnings=warnings,
        )

    # Check zones if required
    resolved_zones = []
    if type_info["requires_zones"]:
        if not record.zones:
            errors.append("Pattern requires zones but none are configured")
        else:
            for zone_id in record.zones:
                zone = zone_repo.get(zone_id)
                if zone:
                    resolved_zones.append({"id": zone.id, "name": zone.name})
                else:
                    errors.append(f"Zone '{zone_id}' not found")

    # Check sensors if required
    resolved_sensors = []
    if type_info["requires_sensors"]:
        if not record.sensors:
            errors.append("Pattern requires sensors but none are configured")
        else:
            for sensor_id in record.sensors:
                sensor = sensor_repo.get(sensor_id)
                if sensor:
                    resolved_sensors.append({"id": sensor.id, "name": sensor.name})
                else:
                    errors.append(f"Sensor '{sensor_id}' not found")

    # Validate config against schema
    config_schema = type_info.get("config_schema", {})
    if config_schema.get("properties"):
        for prop_name, prop_def in config_schema["properties"].items():
            if prop_name not in record.config:
                if prop_def.get("default") is not None:
                    warnings.append(
                        f"Config '{prop_name}' not set, will use default: {prop_def['default']}"
                    )

    return PatternTestResult(
        pattern_id=pattern_id,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        resolved_zones=resolved_zones,
        resolved_sensors=resolved_sensors,
        events_emitted=type_info.get("events_emitted", []),
    )

"""Sensor API endpoints."""

import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from spaxiom.edge.api.models.schemas import (
    SensorCreate,
    SensorUpdate,
    SensorResponse,
    SensorHealth,
    SensorTest,
)
from spaxiom.edge.api.dependencies import get_sensor_repo, get_sensor_registry
from spaxiom.edge.database import SensorRepository
from spaxiom.edge.sensor_registry import PersistentSensorRegistry

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


def _record_to_response(record) -> SensorResponse:
    """Convert a SensorRecord to SensorResponse."""
    return SensorResponse(
        id=record.id,
        name=record.name,
        sensor_type=record.sensor_type,
        location=record.location,
        config=record.config,
        enabled=record.enabled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/types")
async def list_sensor_types():
    """List available sensor types."""
    return [
        "random",
        "toggling",
        "sim_analog",
        "sim_binary",
        "gpio_digital",
        "gpio_analog",
        "mqtt",
        "file",
        "http",
        "modbus",
    ]


@router.get("", response_model=List[SensorResponse])
async def list_sensors(
    enabled_only: bool = Query(False, description="Only return enabled sensors"),
    repo: SensorRepository = Depends(get_sensor_repo),
):
    """List all sensors."""
    records = repo.get_all(enabled_only=enabled_only)
    return [_record_to_response(r) for r in records]


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def create_sensor(
    sensor: SensorCreate,
    repo: SensorRepository = Depends(get_sensor_repo),
    registry: PersistentSensorRegistry = Depends(get_sensor_registry),
):
    """Create a new sensor."""
    # Check if sensor with this name exists
    existing = repo.get_by_name(sensor.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sensor with name '{sensor.name}' already exists",
        )

    try:
        record = repo.create(
            name=sensor.name,
            sensor_type=sensor.sensor_type,
            location=sensor.location,
            config=sensor.config or {},
            enabled=sensor.enabled,
        )

        # Instantiate the sensor in the registry (don't re-create DB record)
        if sensor.enabled and sensor.location:
            try:
                registry.instantiate_from_record(record)
            except Exception:
                # Log but don't fail - sensor saved to DB
                pass

        return _record_to_response(record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create sensor: {str(e)}",
        )


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(
    sensor_id: str,
    repo: SensorRepository = Depends(get_sensor_repo),
):
    """Get a sensor by ID."""
    record = repo.get(sensor_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{sensor_id}' not found",
        )
    return _record_to_response(record)


@router.put("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: str,
    sensor: SensorUpdate,
    repo: SensorRepository = Depends(get_sensor_repo),
):
    """Update a sensor."""
    record = repo.get(sensor_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{sensor_id}' not found",
        )

    updates = sensor.model_dump(exclude_unset=True)
    updated = repo.update(sensor_id, **updates)
    return _record_to_response(updated)


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(
    sensor_id: str,
    repo: SensorRepository = Depends(get_sensor_repo),
    registry: PersistentSensorRegistry = Depends(get_sensor_registry),
):
    """Delete a sensor."""
    record = repo.get(sensor_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{sensor_id}' not found",
        )

    # Remove from registry
    registry.remove(record.name)

    # Delete from database
    repo.delete(sensor_id)


@router.post("/{sensor_id}/test", response_model=SensorTest)
async def test_sensor(
    sensor_id: str,
    repo: SensorRepository = Depends(get_sensor_repo),
    registry: PersistentSensorRegistry = Depends(get_sensor_registry),
):
    """Test a sensor by reading its value."""
    record = repo.get(sensor_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{sensor_id}' not found",
        )

    # Try to get sensor from registry by name
    sensor = registry.get_by_name(record.name)
    if not sensor:
        # Try to instantiate it if it has a location
        if record.location:
            try:
                success = registry.instantiate_from_record(record)
                if success:
                    sensor = registry.get_by_name(record.name)
            except Exception as e:
                return SensorTest(
                    sensor_id=sensor_id,
                    success=False,
                    error=f"Failed to instantiate sensor: {str(e)}",
                )

            if not sensor:
                return SensorTest(
                    sensor_id=sensor_id,
                    success=False,
                    error="Failed to instantiate sensor",
                )
        else:
            return SensorTest(
                sensor_id=sensor_id,
                success=False,
                error="Sensor not in registry and has no location",
            )

    # Read the sensor
    try:
        start = time.perf_counter()
        value = sensor.read()
        elapsed_ms = (time.perf_counter() - start) * 1000

        return SensorTest(
            sensor_id=sensor_id,
            success=True,
            value=value,
            read_time_ms=elapsed_ms,
        )
    except Exception as e:
        return SensorTest(
            sensor_id=sensor_id,
            success=False,
            error=str(e),
        )


@router.get("/{sensor_id}/health", response_model=SensorHealth)
async def get_sensor_health(
    sensor_id: str,
    repo: SensorRepository = Depends(get_sensor_repo),
    registry: PersistentSensorRegistry = Depends(get_sensor_registry),
):
    """Get health status for a sensor."""
    record = repo.get(sensor_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{sensor_id}' not found",
        )

    # Check if sensor is in registry
    sensor = registry.get_by_name(record.name)
    if not sensor:
        return SensorHealth(
            sensor_id=sensor_id,
            status="unknown",
            message="Sensor not in active registry",
        )

    # Get health from registry
    health = registry.check_health_for(record.name)
    return SensorHealth(
        sensor_id=sensor_id,
        status=health.get("status", "unknown"),
        last_read=health.get("last_read"),
        last_value=health.get("last_value"),
        read_count=health.get("read_count", 0),
        error_count=health.get("error_count", 0),
        avg_read_time_ms=health.get("avg_read_time_ms"),
    )

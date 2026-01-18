"""Zone API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
    ZonePreview,
)
from spaxiom.edge.api.dependencies import get_zone_repo, get_sensor_repo
from spaxiom.edge.database import ZoneRepository, SensorRepository

router = APIRouter(prefix="/api/zones", tags=["zones"])

# Zone type definitions
ZONE_TYPES = {
    "rectangle": {
        "name": "Rectangle",
        "description": "Rectangular zone defined by x, y, width, height",
        "geometry_schema": {
            "x": {"type": "number", "description": "X coordinate of top-left corner"},
            "y": {"type": "number", "description": "Y coordinate of top-left corner"},
            "width": {"type": "number", "description": "Width of rectangle"},
            "height": {"type": "number", "description": "Height of rectangle"},
        },
    },
    "polygon": {
        "name": "Polygon",
        "description": "Polygon defined by a list of points",
        "geometry_schema": {
            "points": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
                "description": "List of [x, y] points",
            },
        },
    },
    "circle": {
        "name": "Circle",
        "description": "Circular zone defined by center point and radius",
        "geometry_schema": {
            "center_x": {"type": "number", "description": "X coordinate of center"},
            "center_y": {"type": "number", "description": "Y coordinate of center"},
            "radius": {"type": "number", "description": "Radius of circle"},
        },
    },
}


def _record_to_response(record) -> ZoneResponse:
    """Convert a ZoneRecord to ZoneResponse."""
    return ZoneResponse(
        id=record.id,
        name=record.name,
        zone_type=record.zone_type,
        geometry=record.geometry,
        parent_zone=record.parent_zone,
        created_at=record.created_at,
    )


@router.get("/types")
async def list_zone_types():
    """List available zone types."""
    return ZONE_TYPES


@router.get("/preview", response_model=ZonePreview)
async def get_zone_preview(
    zone_repo: ZoneRepository = Depends(get_zone_repo),
    sensor_repo: SensorRepository = Depends(get_sensor_repo),
):
    """Get zone visualization data for the editor.

    Returns all zones and sensor positions for canvas rendering.
    """
    zones = zone_repo.get_all()
    sensors = sensor_repo.get_all()

    # Calculate bounds from all zones
    min_x, min_y = 0, 0
    max_x, max_y = 100, 100  # Default canvas size

    zone_data = []
    for zone in zones:
        geom = zone.geometry or {}
        zone_info = {
            "id": zone.id,
            "name": zone.name,
            "type": zone.zone_type,
            "geometry": geom,
            "parent_zone": zone.parent_zone,
        }

        # Update bounds based on geometry
        if zone.zone_type == "rectangle":
            x, y = geom.get("x", 0), geom.get("y", 0)
            w, h = geom.get("width", 10), geom.get("height", 10)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
        elif zone.zone_type == "circle":
            cx, cy = geom.get("center_x", 0), geom.get("center_y", 0)
            r = geom.get("radius", 5)
            max_x = max(max_x, cx + r)
            max_y = max(max_y, cy + r)
        elif zone.zone_type == "polygon":
            points = geom.get("points", [])
            for p in points:
                if len(p) >= 2:
                    max_x = max(max_x, p[0])
                    max_y = max(max_y, p[1])

        zone_data.append(zone_info)

    # Get sensor positions
    sensor_data = []
    for sensor in sensors:
        if sensor.location:
            sensor_data.append(
                {
                    "id": sensor.id,
                    "name": sensor.name,
                    "x": sensor.location[0] if len(sensor.location) > 0 else 0,
                    "y": sensor.location[1] if len(sensor.location) > 1 else 0,
                    "type": sensor.sensor_type,
                }
            )

    return ZonePreview(
        zones=zone_data,
        sensors=sensor_data,
        bounds={"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y},
        grid_size=10,  # Default grid size
    )


@router.get("", response_model=List[ZoneResponse])
async def list_zones(
    repo: ZoneRepository = Depends(get_zone_repo),
):
    """List all zones."""
    records = repo.get_all()
    return [_record_to_response(r) for r in records]


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone: ZoneCreate,
    repo: ZoneRepository = Depends(get_zone_repo),
):
    """Create a new zone."""
    # Check if zone with this name exists
    existing = repo.get_by_name(zone.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Zone with name '{zone.name}' already exists",
        )

    try:
        record = repo.create(
            name=zone.name,
            zone_type=zone.zone_type,
            geometry=zone.geometry,
            parent_zone=zone.parent_zone,
        )
        return _record_to_response(record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create zone: {str(e)}",
        )


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    repo: ZoneRepository = Depends(get_zone_repo),
):
    """Get a zone by ID."""
    record = repo.get(zone_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found",
        )
    return _record_to_response(record)


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: str,
    zone: ZoneUpdate,
    repo: ZoneRepository = Depends(get_zone_repo),
):
    """Update a zone."""
    record = repo.get(zone_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found",
        )

    updates = zone.model_dump(exclude_unset=True)
    updated = repo.update(zone_id, **updates)
    return _record_to_response(updated)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: str,
    repo: ZoneRepository = Depends(get_zone_repo),
):
    """Delete a zone."""
    deleted = repo.delete(zone_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found",
        )

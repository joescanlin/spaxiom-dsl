"""Zone API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
)
from spaxiom.edge.api.dependencies import get_zone_repo
from spaxiom.edge.database import ZoneRepository

router = APIRouter(prefix="/api/zones", tags=["zones"])


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

"""Pattern API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    PatternCreate,
    PatternUpdate,
    PatternResponse,
)
from spaxiom.edge.api.dependencies import get_pattern_repo
from spaxiom.edge.database import PatternRepository

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

# Pattern types available in Spaxiom
PATTERN_TYPES = {
    "occupancy_field": "Real-time spatial occupancy tracking",
    "queue_flow": "Queue detection and wait time estimation",
    "adl_tracker": "Activities of Daily Living tracking for eldercare",
    "fm_steward": "Facilities management and space utilization",
    "dwell_monitor": "Dwell time monitoring in zones",
    "path_tracker": "Movement path analysis",
    "crowd_density": "Crowd density and flow analysis",
    "custom": "Custom user-defined pattern",
}


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


@router.get("/types")
async def list_pattern_types():
    """List available pattern types."""
    return PATTERN_TYPES


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

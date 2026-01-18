"""Events API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Query

from spaxiom.edge.api.models.schemas import EventResponse
from spaxiom.edge.api.dependencies import get_event_repo
from spaxiom.edge.database import EventRepository

router = APIRouter(prefix="/api/events", tags=["events"])


def _record_to_response(record) -> EventResponse:
    """Convert an EventRecord to EventResponse."""
    return EventResponse(
        id=record.id,
        timestamp=record.timestamp,
        event_type=record.event_type,
        source=record.source,
        data=record.data,
        severity=record.severity,
    )


@router.get("", response_model=List[EventResponse])
async def list_events(
    event_type: str = Query(None, description="Filter by event type"),
    source: str = Query(None, description="Filter by source"),
    severity: str = Query(None, description="Filter by severity"),
    since: str = Query(None, description="Filter events after this timestamp"),
    until: str = Query(None, description="Filter events before this timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    repo: EventRepository = Depends(get_event_repo),
):
    """Query events with optional filters."""
    records = repo.query(
        event_type=event_type,
        source=source,
        severity=severity,
        since=since,
        until=until,
        limit=limit,
    )
    return [_record_to_response(r) for r in records]


@router.get("/types")
async def list_event_types(
    repo: EventRepository = Depends(get_event_repo),
):
    """Get list of distinct event types."""
    # Query distinct event types
    # For now, return common types
    return [
        "system_startup",
        "system_shutdown",
        "sensor_read",
        "sensor_error",
        "pattern_event",
        "agent_started",
        "agent_stopped",
        "agent_error",
        "config_changed",
    ]


@router.get("/count")
async def get_event_count(
    repo: EventRepository = Depends(get_event_repo),
):
    """Get total event count."""
    return {"count": repo.count()}

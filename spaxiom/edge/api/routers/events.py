"""Events API endpoints."""

import asyncio
import json
from typing import Any, AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

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


def get_agent_manager(request: Request) -> Optional[Any]:
    """Get agent manager from app state."""
    return getattr(request.app.state, "agent_manager", None)


async def event_generator(
    event_queue: asyncio.Queue,
    agent_manager: Any,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from the event queue.

    Args:
        event_queue: Queue to receive events from
        agent_manager: Agent manager to unsubscribe on disconnect

    Yields:
        SSE formatted event strings
    """
    try:
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if agent_manager:
            agent_manager.event_bus.unsubscribe(event_queue)


@router.get("/stream")
async def event_stream(request: Request):
    """Stream events via Server-Sent Events (SSE).

    Returns a continuous stream of events from running agents.
    Connect using EventSource in JavaScript:

    ```javascript
    const eventSource = new EventSource('/api/events/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """
    agent_manager = get_agent_manager(request)

    if not agent_manager:
        return StreamingResponse(
            iter(['data: {"error": "Agent manager not available"}\n\n']),
            media_type="text/event-stream",
        )

    # Subscribe to event bus
    event_queue = agent_manager.event_bus.subscribe()

    return StreamingResponse(
        event_generator(event_queue, agent_manager),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

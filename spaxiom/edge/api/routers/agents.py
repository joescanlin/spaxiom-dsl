"""Agent API endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from spaxiom.edge.api.models.schemas import (
    AgentCreate,
    AgentResponse,
    AgentStats,
)
from spaxiom.edge.api.dependencies import get_agent_repo, get_pattern_repo
from spaxiom.edge.database import AgentRepository, PatternRepository

router = APIRouter(prefix="/api/agents", tags=["agents"])


def get_agent_manager(request: Request) -> Optional[Any]:
    """Get agent manager from app state."""
    return getattr(request.app.state, "agent_manager", None)


def _record_to_response(record, running_stats: Optional[Dict] = None) -> AgentResponse:
    """Convert an AgentRecord to AgentResponse."""
    response = AgentResponse(
        id=record.id,
        name=record.name,
        pattern_id=record.pattern_id,
        status=record.status,
        pid=record.pid,
        started_at=record.started_at,
        stopped_at=record.stopped_at,
        last_error=record.last_error,
        config=record.config,
    )

    # Overlay running stats if available
    if running_stats:
        response.status = running_stats.get("status", response.status)
        if running_stats.get("started_at"):
            response.started_at = running_stats["started_at"]

    return response


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    request: Request,
    status_filter: str = None,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """List all agents."""
    records = repo.get_all(status=status_filter)
    agent_manager = get_agent_manager(request)

    responses = []
    for r in records:
        running_stats = None
        if agent_manager:
            running_stats = agent_manager.get_status(r.id)
        responses.append(_record_to_response(r, running_stats))

    return responses


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: Request,
    agent: AgentCreate,
    agent_repo: AgentRepository = Depends(get_agent_repo),
    pattern_repo: PatternRepository = Depends(get_pattern_repo),
):
    """Create and deploy a new agent from a pattern."""
    # Verify pattern exists
    pattern = pattern_repo.get(agent.pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{agent.pattern_id}' not found",
        )

    agent_manager = get_agent_manager(request)

    if agent_manager:
        # Deploy via agent manager
        try:
            agent_id = await agent_manager.deploy(
                pattern_id=agent.pattern_id,
                name=agent.name,
                config_overrides=agent.config,
            )
            record = agent_repo.get(agent_id)
            running_stats = agent_manager.get_status(agent_id)
            return _record_to_response(record, running_stats)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deploy agent: {str(e)}",
            )
    else:
        # Fallback: just create record without running
        name = agent.name or f"agent_{pattern.name}"
        try:
            record = agent_repo.create(
                name=name,
                pattern_id=agent.pattern_id,
                config=agent.config,
            )
            return _record_to_response(record)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create agent: {str(e)}",
            )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Get an agent by ID."""
    record = repo.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    agent_manager = get_agent_manager(request)
    running_stats = agent_manager.get_status(agent_id) if agent_manager else None

    return _record_to_response(record, running_stats)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Stop and delete an agent."""
    agent_manager = get_agent_manager(request)

    # Stop agent if running
    if agent_manager:
        await agent_manager.stop_agent(agent_id)

    deleted = repo.delete(agent_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )


@router.post("/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Start a stopped agent."""
    record = repo.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    agent_manager = get_agent_manager(request)

    if agent_manager:
        running_stats = agent_manager.get_status(agent_id)
        if running_stats.get("status") == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' is already running",
            )

        success = await agent_manager.start_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start agent",
            )

        record = repo.get(agent_id)
        running_stats = agent_manager.get_status(agent_id)
        return _record_to_response(record, running_stats)
    else:
        # Fallback: just update status
        if record.status == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' is already running",
            )
        updated = repo.update_status(agent_id, "running", pid=0)
        return _record_to_response(updated)


@router.post("/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Stop a running agent."""
    record = repo.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    agent_manager = get_agent_manager(request)

    if agent_manager:
        running_stats = agent_manager.get_status(agent_id)
        if running_stats.get("status") != "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' is not running",
            )

        success = await agent_manager.stop_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop agent",
            )

        record = repo.get(agent_id)
        running_stats = agent_manager.get_status(agent_id)
        return _record_to_response(record, running_stats)
    else:
        # Fallback: just update status
        if record.status == "stopped":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' is already stopped",
            )
        updated = repo.update_status(agent_id, "stopped")
        return _record_to_response(updated)


@router.post("/{agent_id}/restart", response_model=AgentResponse)
async def restart_agent(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Restart an agent."""
    record = repo.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    agent_manager = get_agent_manager(request)

    if agent_manager:
        success = await agent_manager.restart_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restart agent",
            )

        record = repo.get(agent_id)
        running_stats = agent_manager.get_status(agent_id)
        return _record_to_response(record, running_stats)
    else:
        # Fallback: just update status
        updated = repo.update_status(agent_id, "running", pid=0)
        return _record_to_response(updated)


@router.get("/{agent_id}/stats", response_model=AgentStats)
async def get_agent_stats(
    request: Request,
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Get statistics for an agent."""
    record = repo.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    agent_manager = get_agent_manager(request)

    if agent_manager:
        running_stats = agent_manager.get_status(agent_id)
        return AgentStats(
            agent_id=agent_id,
            status=running_stats.get("status", record.status),
            tick_count=running_stats.get("tick_count", 0),
            uptime_seconds=0,  # TODO: calculate from started_at
            avg_tick_ms=running_stats.get("avg_tick_ms", 0),
            sensors_read_total=0,
            events_emitted_total=running_stats.get("events_emitted", 0),
            callbacks_dispatched_total=0,
            callback_failures=running_stats.get("errors", 0),
        )
    else:
        return AgentStats(
            agent_id=agent_id,
            status=record.status,
            tick_count=0,
            uptime_seconds=0,
            avg_tick_ms=0,
            sensors_read_total=0,
            events_emitted_total=0,
            callbacks_dispatched_total=0,
            callback_failures=0,
        )

"""Agent API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    AgentCreate,
    AgentResponse,
    AgentStats,
)
from spaxiom.edge.api.dependencies import get_agent_repo, get_pattern_repo
from spaxiom.edge.database import AgentRepository, PatternRepository

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _record_to_response(record) -> AgentResponse:
    """Convert an AgentRecord to AgentResponse."""
    return AgentResponse(
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


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    status_filter: str = None,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """List all agents."""
    records = repo.get_all(status=status_filter)
    return [_record_to_response(r) for r in records]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    agent_repo: AgentRepository = Depends(get_agent_repo),
    pattern_repo: PatternRepository = Depends(get_pattern_repo),
):
    """Create a new agent (deploy a pattern)."""
    # Verify pattern exists
    pattern = pattern_repo.get(agent.pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{agent.pattern_id}' not found",
        )

    # Create agent name from pattern if not provided
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
    return _record_to_response(record)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),
):
    """Delete an agent."""
    # TODO: Stop agent if running before deleting
    deleted = repo.delete(agent_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )


@router.post("/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
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

    if record.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_id}' is already running",
        )

    # TODO: Actually start the agent via AgentManager
    # For now, just update status
    updated = repo.update_status(agent_id, "running", pid=0)
    return _record_to_response(updated)


@router.post("/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
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

    if record.status == "stopped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_id}' is already stopped",
        )

    # TODO: Actually stop the agent via AgentManager
    # For now, just update status
    updated = repo.update_status(agent_id, "stopped")
    return _record_to_response(updated)


@router.post("/{agent_id}/restart", response_model=AgentResponse)
async def restart_agent(
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

    # TODO: Actually restart the agent via AgentManager
    # For now, just update status
    updated = repo.update_status(agent_id, "running", pid=0)
    return _record_to_response(updated)


@router.get("/{agent_id}/stats", response_model=AgentStats)
async def get_agent_stats(
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

    # TODO: Get actual stats from AgentManager
    # For now, return placeholder stats
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

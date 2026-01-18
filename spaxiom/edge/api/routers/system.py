"""System API endpoints."""

import platform
import sys
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from spaxiom.edge.api.models.schemas import (
    SystemHealth,
    SystemInfo,
    SettingsUpdate,
)
from spaxiom.edge.api.dependencies import get_app_state

router = APIRouter(prefix="/api/system", tags=["system"])

# Track startup time for uptime calculation
_startup_time = time.time()


def get_uptime_seconds() -> float:
    """Get application uptime in seconds."""
    return time.time() - _startup_time


def get_disk_usage() -> float:
    """Get disk usage percentage."""
    try:
        import shutil

        total, used, free = shutil.disk_usage("/")
        return (used / total) * 100
    except Exception:
        return 0.0


def get_memory_usage() -> float:
    """Get memory usage percentage."""
    try:
        # Try psutil if available
        import psutil

        return psutil.virtual_memory().percent
    except ImportError:
        # Fallback: read from /proc on Linux
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
                mem_total = int(lines[0].split()[1])
                mem_available = int(lines[2].split()[1])
                return ((mem_total - mem_available) / mem_total) * 100
        except Exception:
            return 0.0


@router.get("/health", response_model=SystemHealth)
async def get_health(state: Dict[str, Any] = Depends(get_app_state)):
    """Get overall system health."""
    db = state.get("db")
    sensor_registry = state.get("sensor_registry")
    agent_repo = state.get("agent_repo")

    # Database health
    db_health = db.check_health() if db else {"status": "unknown"}

    # Sensor health summary
    sensor_health = {"total": 0, "healthy": 0, "unhealthy": 0}
    if sensor_registry:
        all_health = sensor_registry.check_health()
        sensor_health["total"] = len(all_health)
        sensor_health["healthy"] = sum(
            1 for h in all_health.values() if h.get("status") == "ok"
        )
        sensor_health["unhealthy"] = sensor_health["total"] - sensor_health["healthy"]

    # Agent health summary
    agent_health = {"total": 0, "running": 0, "stopped": 0, "error": 0}
    if agent_repo:
        all_agents = agent_repo.get_all()
        agent_health["total"] = len(all_agents)
        for agent in all_agents:
            if agent.status == "running":
                agent_health["running"] += 1
            elif agent.status == "error":
                agent_health["error"] += 1
            else:
                agent_health["stopped"] += 1

    # Determine overall status
    overall_status = "healthy"
    if db_health.get("status") != "ok":
        overall_status = "unhealthy"
    elif sensor_health["unhealthy"] > 0 or agent_health["error"] > 0:
        overall_status = "degraded"

    return SystemHealth(
        status=overall_status,
        uptime_seconds=get_uptime_seconds(),
        database=db_health,
        sensors=sensor_health,
        agents=agent_health,
        disk_usage_percent=get_disk_usage(),
        memory_usage_percent=get_memory_usage(),
    )


@router.get("/info", response_model=SystemInfo)
async def get_info(state: Dict[str, Any] = Depends(get_app_state)):
    """Get system information."""
    import spaxiom

    db = state.get("db")
    sensor_registry = state.get("sensor_registry")
    pattern_repo = state.get("pattern_repo")
    agent_repo = state.get("agent_repo")

    return SystemInfo(
        version=getattr(spaxiom, "__version__", "unknown"),
        hostname=platform.node(),
        platform=platform.system(),
        python_version=sys.version.split()[0],
        uptime_seconds=get_uptime_seconds(),
        db_path=str(db.db_path) if db else "unknown",
        log_path=state.get("log_path", "unknown"),
        api_port=state.get("api_port", 8080),
        sensors_count=sensor_registry.count_all() if sensor_registry else 0,
        patterns_count=pattern_repo.count() if pattern_repo else 0,
        agents_count=agent_repo.count() if agent_repo else 0,
    )


@router.get("/settings")
async def get_settings(state: Dict[str, Any] = Depends(get_app_state)):
    """Get all settings."""
    settings_repo = state.get("settings_repo")
    if not settings_repo:
        return {}
    return settings_repo.get_all()


@router.put("/settings")
async def update_settings(
    update: SettingsUpdate,
    state: Dict[str, Any] = Depends(get_app_state),
):
    """Update settings."""
    settings_repo = state.get("settings_repo")
    if not settings_repo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Settings repository not available",
        )

    for key, value in update.settings.items():
        settings_repo.set(key, value)

    return {"updated": list(update.settings.keys())}


@router.post("/restart")
async def restart_service():
    """Request service restart."""
    # This endpoint would typically signal the process manager
    # For now, just return a message
    return {
        "message": "Restart requested. Service will restart shortly.",
        "note": "Restart must be handled by systemd or process manager.",
    }

"""FastAPI dependency injection for Spaxiom Edge API."""

from typing import Any, Dict

from fastapi import Request

from spaxiom.edge.database import (
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
    SettingsRepository,
)
from spaxiom.edge.sensor_registry import PersistentSensorRegistry


def get_app_state(request: Request) -> Dict[str, Any]:
    """Get the application state from the request."""
    return request.app.state._state


def get_db(request: Request):
    """Get the database instance."""
    return request.app.state.db


def get_sensor_registry(request: Request) -> PersistentSensorRegistry:
    """Get the sensor registry."""
    return request.app.state.sensor_registry


def get_sensor_repo(request: Request) -> SensorRepository:
    """Get the sensor repository."""
    return request.app.state.sensor_repo


def get_zone_repo(request: Request) -> ZoneRepository:
    """Get the zone repository."""
    return request.app.state.zone_repo


def get_pattern_repo(request: Request) -> PatternRepository:
    """Get the pattern repository."""
    return request.app.state.pattern_repo


def get_agent_repo(request: Request) -> AgentRepository:
    """Get the agent repository."""
    return request.app.state.agent_repo


def get_event_repo(request: Request) -> EventRepository:
    """Get the event repository."""
    return request.app.state.event_repo


def get_settings_repo(request: Request) -> SettingsRepository:
    """Get the settings repository."""
    return request.app.state.settings_repo

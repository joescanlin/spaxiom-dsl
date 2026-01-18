"""Pydantic schemas for API request/response models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Sensor schemas
class SensorCreate(BaseModel):
    """Schema for creating a sensor."""

    name: str = Field(..., min_length=1, max_length=255)
    sensor_type: str = Field(..., min_length=1, max_length=50)
    location: Optional[List[float]] = Field(None, description="[x, y, z] coordinates")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    enabled: bool = True


class SensorUpdate(BaseModel):
    """Schema for updating a sensor."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sensor_type: Optional[str] = Field(None, min_length=1, max_length=50)
    location: Optional[List[float]] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class SensorResponse(BaseModel):
    """Schema for sensor response."""

    id: str
    name: str
    sensor_type: str
    location: Optional[List[float]] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SensorHealth(BaseModel):
    """Schema for sensor health status."""

    sensor_id: str
    status: str  # ok, error, timeout, unknown
    last_read: Optional[float] = None  # Unix timestamp
    last_value: Optional[Any] = None
    read_count: int = 0
    error_count: int = 0
    avg_read_time_ms: Optional[float] = None
    message: Optional[str] = None


class SensorTest(BaseModel):
    """Schema for sensor test result."""

    sensor_id: str
    success: bool
    value: Optional[Any] = None
    read_time_ms: Optional[float] = None
    error: Optional[str] = None


# Zone schemas
class ZoneCreate(BaseModel):
    """Schema for creating a zone."""

    name: str = Field(..., min_length=1, max_length=255)
    zone_type: str = Field(..., min_length=1, max_length=50)
    geometry: Dict[str, Any] = Field(
        default_factory=dict, description="Zone geometry (bounds, polygon, etc.)"
    )
    parent_zone: Optional[str] = None


class ZoneUpdate(BaseModel):
    """Schema for updating a zone."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    zone_type: Optional[str] = Field(None, min_length=1, max_length=50)
    geometry: Optional[Dict[str, Any]] = None
    parent_zone: Optional[str] = None


class ZoneResponse(BaseModel):
    """Schema for zone response."""

    id: str
    name: str
    zone_type: str
    geometry: Dict[str, Any] = Field(default_factory=dict)
    parent_zone: Optional[str] = None
    created_at: Optional[str] = None


# Pattern schemas
class PatternCreate(BaseModel):
    """Schema for creating a pattern."""

    name: str = Field(..., min_length=1, max_length=255)
    pattern_type: str = Field(..., min_length=1, max_length=50)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    zones: Optional[List[str]] = Field(default_factory=list, description="Zone IDs")
    sensors: Optional[List[str]] = Field(default_factory=list, description="Sensor IDs")
    enabled: bool = True


class PatternUpdate(BaseModel):
    """Schema for updating a pattern."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    pattern_type: Optional[str] = Field(None, min_length=1, max_length=50)
    config: Optional[Dict[str, Any]] = None
    zones: Optional[List[str]] = None
    sensors: Optional[List[str]] = None
    enabled: Optional[bool] = None


class PatternResponse(BaseModel):
    """Schema for pattern response."""

    id: str
    name: str
    pattern_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    zones: List[str] = Field(default_factory=list)
    sensors: List[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Agent schemas
class AgentCreate(BaseModel):
    """Schema for creating an agent (deploying a pattern)."""

    pattern_id: str
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: str
    name: str
    pattern_id: str
    status: str  # stopped, running, error
    pid: Optional[int] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    last_error: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentStats(BaseModel):
    """Schema for agent statistics."""

    agent_id: str
    status: str
    tick_count: int = 0
    uptime_seconds: float = 0
    avg_tick_ms: float = 0
    sensors_read_total: int = 0
    events_emitted_total: int = 0
    callbacks_dispatched_total: int = 0
    callback_failures: int = 0


# System schemas
class SystemHealth(BaseModel):
    """Schema for system health status."""

    status: str  # healthy, degraded, unhealthy
    uptime_seconds: float
    database: Dict[str, Any]
    sensors: Dict[str, int]
    agents: Dict[str, int]
    disk_usage_percent: float = 0
    memory_usage_percent: float = 0


class SystemInfo(BaseModel):
    """Schema for system information."""

    version: str
    hostname: str
    platform: str
    python_version: str
    uptime_seconds: float
    db_path: str
    log_path: str
    api_port: int
    sensors_count: int
    patterns_count: int
    agents_count: int


class SettingsUpdate(BaseModel):
    """Schema for updating settings."""

    settings: Dict[str, Any]


# Event schemas
class EventResponse(BaseModel):
    """Schema for event response."""

    id: str
    timestamp: str
    event_type: str
    source: str
    data: Optional[Dict[str, Any]] = None
    severity: str = "info"

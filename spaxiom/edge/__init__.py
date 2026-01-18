"""
Spaxiom Edge - Edge deployment package for customer devices.

This package provides:
- Persistent storage (SQLite)
- REST API for configuration
- Web UI for non-technical users
- Agent lifecycle management
- System service integration
"""

from spaxiom.edge.database import (
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
    SettingsRepository,
    SensorRecord,
    ZoneRecord,
    PatternRecord,
    AgentRecord,
    EventRecord,
)
from spaxiom.edge.sensor_registry import PersistentSensorRegistry
from spaxiom.edge.app import SpaxiomEdge, main
from spaxiom.edge.logging_config import setup_logging, EdgeLogger

__all__ = [
    # Database
    "EdgeDatabase",
    "SensorRepository",
    "ZoneRepository",
    "PatternRepository",
    "AgentRepository",
    "EventRepository",
    "SettingsRepository",
    # Records
    "SensorRecord",
    "ZoneRecord",
    "PatternRecord",
    "AgentRecord",
    "EventRecord",
    # Registry
    "PersistentSensorRegistry",
    # Application
    "SpaxiomEdge",
    "main",
    # Logging
    "setup_logging",
    "EdgeLogger",
]

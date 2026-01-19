"""API routers package."""

from spaxiom.edge.api.routers.sensors import router as sensors_router
from spaxiom.edge.api.routers.zones import router as zones_router
from spaxiom.edge.api.routers.patterns import router as patterns_router
from spaxiom.edge.api.routers.agents import router as agents_router
from spaxiom.edge.api.routers.system import router as system_router
from spaxiom.edge.api.routers.events import router as events_router
from spaxiom.edge.api.routers.auth import router as auth_router

__all__ = [
    "sensors_router",
    "zones_router",
    "patterns_router",
    "agents_router",
    "system_router",
    "events_router",
    "auth_router",
]

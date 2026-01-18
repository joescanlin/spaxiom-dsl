"""FastAPI application factory for Spaxiom Edge."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from spaxiom.edge.api.routers import (
    sensors_router,
    zones_router,
    patterns_router,
    agents_router,
    system_router,
    events_router,
)

logger = logging.getLogger(__name__)

# Global app instance for module-level access
_app: Optional[FastAPI] = None


def create_app(
    title: str = "Spaxiom Edge",
    description: str = "Edge AI Agent Configuration API",
    version: str = "0.1.0",
    static_dir: Optional[str] = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        title: API title
        description: API description
        version: API version
        static_dir: Path to static files directory

    Returns:
        Configured FastAPI application
    """
    global _app

    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(sensors_router)
    app.include_router(zones_router)
    app.include_router(patterns_router)
    app.include_router(agents_router)
    app.include_router(system_router)
    app.include_router(events_router)

    # Mount static files if directory exists
    if static_dir:
        static_path = Path(static_dir)
        if static_path.exists():
            app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
            logger.info(f"Mounted static files from {static_path}")

            # Serve index.html at root
            @app.get("/", include_in_schema=False)
            async def serve_index():
                index_path = static_path / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                return {"message": "Spaxiom Edge API", "docs": "/api/docs"}

    # Health check at root if no static files
    if not static_dir:

        @app.get("/")
        async def root():
            return {
                "name": "Spaxiom Edge",
                "version": version,
                "docs": "/api/docs",
                "health": "/api/system/health",
            }

    # Store global reference
    _app = app

    return app


def get_app() -> Optional[FastAPI]:
    """Get the global FastAPI app instance."""
    return _app


def setup_app_state(
    app: FastAPI,
    db,
    sensor_registry,
    sensor_repo,
    zone_repo,
    pattern_repo,
    agent_repo,
    event_repo,
    settings_repo,
    log_path: str = "",
    api_port: int = 8080,
) -> None:
    """Setup application state with dependencies.

    Args:
        app: FastAPI application
        db: EdgeDatabase instance
        sensor_registry: PersistentSensorRegistry instance
        sensor_repo: SensorRepository instance
        zone_repo: ZoneRepository instance
        pattern_repo: PatternRepository instance
        agent_repo: AgentRepository instance
        event_repo: EventRepository instance
        settings_repo: SettingsRepository instance
        log_path: Path to log file
        api_port: API server port
    """
    app.state.db = db
    app.state.sensor_registry = sensor_registry
    app.state.sensor_repo = sensor_repo
    app.state.zone_repo = zone_repo
    app.state.pattern_repo = pattern_repo
    app.state.agent_repo = agent_repo
    app.state.event_repo = event_repo
    app.state.settings_repo = settings_repo
    app.state.log_path = log_path
    app.state.api_port = api_port

    # Also store in _state dict for get_app_state dependency
    app.state._state = {
        "db": db,
        "sensor_registry": sensor_registry,
        "sensor_repo": sensor_repo,
        "zone_repo": zone_repo,
        "pattern_repo": pattern_repo,
        "agent_repo": agent_repo,
        "event_repo": event_repo,
        "settings_repo": settings_repo,
        "log_path": log_path,
        "api_port": api_port,
    }

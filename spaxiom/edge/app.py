"""
Spaxiom Edge Application Entry Point.

Main application controller that manages:
- Database initialization
- Sensor registry
- Agent lifecycle (Phase 4)
- API server (Phase 2)
- Signal handling and graceful shutdown
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from spaxiom.edge.database import (
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
    SettingsRepository,
)
from spaxiom.edge.sensor_registry import PersistentSensorRegistry
from spaxiom.edge.logging_config import setup_logging, get_default_log_path

logger = logging.getLogger(__name__)

# Check if FastAPI/uvicorn are available
try:
    import uvicorn
    from spaxiom.edge.api.app import create_app, setup_app_state

    HAS_API = True
except ImportError:
    HAS_API = False
    logger.debug("FastAPI/uvicorn not installed. API server disabled.")


class SpaxiomEdge:
    """Main edge application controller.

    Manages the lifecycle of all edge deployment components:
    - Database and persistence
    - Sensor registry
    - Agent manager (Phase 4)
    - API server (Phase 2)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        log_path: Optional[str] = None,
        log_level: str = "INFO",
        api_host: str = "0.0.0.0",
        api_port: int = 8080,
    ):
        """Initialize the edge application.

        Args:
            db_path: Path to SQLite database file
            log_path: Path to log file
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            api_host: API server host
            api_port: API server port
        """
        # Determine paths
        self.db_path = db_path or self._get_default_db_path()
        self.log_path = log_path or get_default_log_path()
        self.log_level = log_level
        self.api_host = api_host
        self.api_port = api_port

        # Initialize components (not started yet)
        self.db: Optional[EdgeDatabase] = None
        self.sensor_registry: Optional[PersistentSensorRegistry] = None

        # Repositories (initialized after db)
        self.sensors: Optional[SensorRepository] = None
        self.zones: Optional[ZoneRepository] = None
        self.patterns: Optional[PatternRepository] = None
        self.agents: Optional[AgentRepository] = None
        self.events: Optional[EventRepository] = None
        self.settings: Optional[SettingsRepository] = None

        # Runtime state
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._tasks: list = []
        self._api_server = None
        self._api_app = None

    @staticmethod
    def _get_default_db_path() -> str:
        """Get default database path based on environment."""
        env_path = os.environ.get("SPAXIOM_DB_PATH")
        if env_path:
            return env_path

        if sys.platform.startswith("linux"):
            db_dir = Path("/var/lib/spaxiom")
            if db_dir.exists() or os.access(db_dir.parent, os.W_OK):
                return str(db_dir / "spaxiom.db")

        home = Path.home()
        db_dir = home / ".spaxiom" / "data"
        return str(db_dir / "spaxiom.db")

    async def startup(self) -> None:
        """Initialize all subsystems.

        Called before the main event loop starts.
        """
        logger.info("Starting Spaxiom Edge...")

        # Initialize database
        logger.info(f"Initializing database at {self.db_path}")
        self.db = EdgeDatabase(self.db_path)
        self.db.init()

        # Initialize repositories
        self.sensors = SensorRepository(self.db)
        self.zones = ZoneRepository(self.db)
        self.patterns = PatternRepository(self.db)
        self.agents = AgentRepository(self.db)
        self.events = EventRepository(self.db)
        self.settings = SettingsRepository(self.db)

        # Initialize sensor registry and load sensors
        logger.info("Loading sensors from database...")
        self.sensor_registry = PersistentSensorRegistry(self.db)
        sensor_count = self.sensor_registry.load()
        logger.info(f"Loaded {sensor_count} sensors")

        # Log startup event
        self.events.log(
            event_type="system_startup",
            source="spaxiom_edge",
            data={
                "db_path": self.db_path,
                "sensors_loaded": sensor_count,
            },
            severity="info",
        )

        # Setup API server if available
        if HAS_API:
            self._setup_api()

        logger.info("Spaxiom Edge startup complete")

    def _setup_api(self) -> None:
        """Setup the FastAPI application."""
        if not HAS_API:
            return

        # Get static files directory
        static_dir = Path(__file__).parent / "static"

        # Create FastAPI app
        self._api_app = create_app(
            static_dir=str(static_dir) if static_dir.exists() else None
        )

        # Setup app state with dependencies
        setup_app_state(
            self._api_app,
            db=self.db,
            sensor_registry=self.sensor_registry,
            sensor_repo=self.sensors,
            zone_repo=self.zones,
            pattern_repo=self.patterns,
            agent_repo=self.agents,
            event_repo=self.events,
            settings_repo=self.settings,
            log_path=self.log_path,
            api_port=self.api_port,
        )

        logger.info(f"API server configured on {self.api_host}:{self.api_port}")

    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems."""
        logger.info("Shutting down Spaxiom Edge...")

        # Stop API server if running
        if self._api_server:
            self._api_server.should_exit = True

        # Cancel running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Log shutdown event
        if self.events:
            self.events.log(
                event_type="system_shutdown",
                source="spaxiom_edge",
                severity="info",
            )

        logger.info("Spaxiom Edge shutdown complete")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def signal_handler(sig: signal.Signals) -> None:
            logger.info(f"Received signal {sig.name}, initiating shutdown...")
            self._running = False
            if self._shutdown_event:
                self._shutdown_event.set()

        # Handle SIGTERM and SIGINT
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: signal_handler(signal.Signals(s)))

    async def _run_event_cleanup(self, interval_hours: int = 24) -> None:
        """Periodically clean up old events.

        Args:
            interval_hours: Hours between cleanup runs
        """
        while self._running:
            try:
                await asyncio.sleep(interval_hours * 3600)
                if self.events and self.settings:
                    retention_days = self.settings.get("event_retention_days", 30)
                    deleted = self.events.cleanup(max_age_days=retention_days)
                    if deleted > 0:
                        logger.info(f"Cleaned up {deleted} old events")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event cleanup: {e}")

    async def _run_api_server(self) -> None:
        """Run the uvicorn API server."""
        if not HAS_API or not self._api_app:
            return

        config = uvicorn.Config(
            self._api_app,
            host=self.api_host,
            port=self.api_port,
            log_level="warning",  # Reduce uvicorn logging noise
        )
        self._api_server = uvicorn.Server(config)

        logger.info(f"Starting API server at http://{self.api_host}:{self.api_port}")
        await self._api_server.serve()

    async def run(self) -> None:
        """Run the edge application main loop."""
        self._running = True
        self._shutdown_event = asyncio.Event()

        # Setup signal handlers
        self._setup_signal_handlers()

        try:
            # Startup
            await self.startup()

            # Start background tasks
            cleanup_task = asyncio.create_task(self._run_event_cleanup())
            self._tasks.append(cleanup_task)

            # Start API server if available
            if HAS_API and self._api_app:
                api_task = asyncio.create_task(self._run_api_server())
                self._tasks.append(api_task)
                logger.info(
                    f"Spaxiom Edge is running. Web UI at http://{self.api_host}:{self.api_port}"
                )
            else:
                logger.info(
                    "Spaxiom Edge is running (API disabled). Press Ctrl+C to stop."
                )

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise
        finally:
            await self.shutdown()

    def run_sync(self) -> None:
        """Run the application synchronously (blocking)."""
        # Setup logging
        setup_logging(
            log_path=self.log_path,
            level=self.log_level,
        )

        # Run async main loop
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    def get_status(self) -> Dict[str, Any]:
        """Get current application status.

        Returns:
            Status dictionary
        """
        status = {
            "running": self._running,
            "db_path": self.db_path,
            "log_path": self.log_path,
        }

        if self.db:
            status["database"] = self.db.check_health()

        if self.sensor_registry:
            status["sensors"] = {
                "active": self.sensor_registry.count(),
                "total": self.sensor_registry.count_all(),
            }

        if self.patterns:
            status["patterns"] = {"total": self.patterns.count()}

        if self.agents:
            status["agents"] = {"total": self.agents.count()}

        return status


def main() -> None:
    """CLI entry point for spaxiom-edge command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Spaxiom Edge - AI Agent Runtime for Edge Devices"
    )
    parser.add_argument(
        "--db-path",
        help="Path to SQLite database file",
        default=None,
    )
    parser.add_argument(
        "--log-path",
        help="Path to log file",
        default=None,
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    parser.add_argument(
        "--host",
        help="API server host",
        default="0.0.0.0",
    )
    parser.add_argument(
        "--port",
        help="API server port",
        type=int,
        default=8080,
    )

    args = parser.parse_args()

    app = SpaxiomEdge(
        db_path=args.db_path,
        log_path=args.log_path,
        log_level=args.log_level,
        api_host=args.host,
        api_port=args.port,
    )

    app.run_sync()


if __name__ == "__main__":
    main()

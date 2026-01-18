"""Tests for spaxiom.edge.app module."""

import os
import tempfile
import pytest

from spaxiom.core import SensorRegistry
from spaxiom.edge.app import SpaxiomEdge


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    # Clear the global singleton registry to avoid test pollution
    core_registry = SensorRegistry()
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        log_path = os.path.join(tmpdir, "test.log")
        yield {"db_path": db_path, "log_path": log_path, "tmpdir": tmpdir}

    # Clean up after test
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()


class TestSpaxiomEdge:
    """Tests for SpaxiomEdge class."""

    def test_init(self, temp_dirs):
        """Test SpaxiomEdge initialization."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )

        assert app.db_path == temp_dirs["db_path"]
        assert app.log_path == temp_dirs["log_path"]
        assert app.db is None  # Not initialized yet
        assert app._running is False

    @pytest.mark.asyncio
    async def test_startup(self, temp_dirs):
        """Test SpaxiomEdge startup."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )

        await app.startup()

        assert app.db is not None
        assert app.sensor_registry is not None
        assert app.sensors is not None
        assert app.zones is not None
        assert app.patterns is not None
        assert app.agents is not None
        assert app.events is not None
        assert app.settings is not None

        # Database file should exist
        assert os.path.exists(temp_dirs["db_path"])

    @pytest.mark.asyncio
    async def test_startup_shutdown(self, temp_dirs):
        """Test startup and shutdown cycle."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )

        await app.startup()

        # Add a sensor
        sensor_id = app.sensor_registry.register(
            name="test_sensor",
            sensor_type="random",
        )
        assert sensor_id is not None

        await app.shutdown()

    @pytest.mark.asyncio
    async def test_startup_logs_event(self, temp_dirs):
        """Test that startup logs a system event."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )

        await app.startup()

        events = app.events.query(event_type="system_startup")

        assert len(events) == 1
        assert events[0].source == "spaxiom_edge"

    @pytest.mark.asyncio
    async def test_get_status(self, temp_dirs):
        """Test getting application status."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )

        await app.startup()

        status = app.get_status()

        assert "running" in status
        assert "db_path" in status
        assert "database" in status
        assert status["database"]["status"] == "ok"
        assert "sensors" in status

    @pytest.mark.asyncio
    async def test_sensors_persist(self, temp_dirs):
        """Test that sensors persist across app restarts."""
        # Clear global registry before test
        core_registry = SensorRegistry()
        core_registry._sensors.clear()
        core_registry._private_sensors.clear()

        # First app instance
        app1 = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )
        await app1.startup()

        app1.sensor_registry.register(
            name="persistent_sensor",
            sensor_type="random",
            location=(0, 0, 0),
        )

        await app1.shutdown()

        # Clear global registry to simulate restart
        core_registry._sensors.clear()
        core_registry._private_sensors.clear()

        # Second app instance
        app2 = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_path=temp_dirs["log_path"],
        )
        await app2.startup()

        sensor = app2.sensor_registry.get_by_name("persistent_sensor")
        assert sensor is not None

        await app2.shutdown()


class TestSpaxiomEdgeDefaults:
    """Tests for default path handling."""

    def test_default_db_path_env(self, monkeypatch):
        """Test that environment variable overrides default db path."""
        monkeypatch.setenv("SPAXIOM_DB_PATH", "/custom/path/spaxiom.db")

        app = SpaxiomEdge()

        assert app.db_path == "/custom/path/spaxiom.db"

    def test_default_log_level(self, temp_dirs):
        """Test default log level."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
        )

        assert app.log_level == "INFO"

    def test_custom_log_level(self, temp_dirs):
        """Test custom log level."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            log_level="DEBUG",
        )

        assert app.log_level == "DEBUG"

    def test_default_api_settings(self, temp_dirs):
        """Test default API settings."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
        )

        assert app.api_host == "0.0.0.0"
        assert app.api_port == 8080

    def test_custom_api_settings(self, temp_dirs):
        """Test custom API settings."""
        app = SpaxiomEdge(
            db_path=temp_dirs["db_path"],
            api_host="127.0.0.1",
            api_port=9000,
        )

        assert app.api_host == "127.0.0.1"
        assert app.api_port == 9000

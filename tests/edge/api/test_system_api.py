"""Tests for system API endpoints."""

import os
import tempfile

import pytest

# Skip all tests in this module if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI not installed")
from fastapi.testclient import TestClient  # noqa: E402

from spaxiom.core import SensorRegistry  # noqa: E402
from spaxiom.edge.database import (  # noqa: E402
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
    SettingsRepository,
)
from spaxiom.edge.sensor_registry import PersistentSensorRegistry  # noqa: E402
from spaxiom.edge.api.app import create_app, setup_app_state  # noqa: E402


@pytest.fixture
def test_app():
    """Create a test FastAPI application with temp database."""
    # Clear global sensor registry
    core_registry = SensorRegistry()
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = EdgeDatabase(db_path)
    db.init()

    sensor_registry = PersistentSensorRegistry(db)

    app = create_app()
    setup_app_state(
        app,
        db=db,
        sensor_registry=sensor_registry,
        sensor_repo=SensorRepository(db),
        zone_repo=ZoneRepository(db),
        pattern_repo=PatternRepository(db),
        agent_repo=AgentRepository(db),
        event_repo=EventRepository(db),
        settings_repo=SettingsRepository(db),
        log_path="/tmp/test.log",
        api_port=8080,
    )

    yield app

    # Cleanup
    core_registry._sensors.clear()
    core_registry._private_sensors.clear()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestSystemAPI:
    """Tests for system API endpoints."""

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/api/system/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "uptime_seconds" in data
        assert "database" in data
        assert "sensors" in data
        assert "agents" in data

    def test_info(self, client):
        """Test info endpoint."""
        response = client.get("/api/system/info")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert "hostname" in data
        assert "platform" in data
        assert "python_version" in data
        assert "uptime_seconds" in data
        assert "db_path" in data
        assert "sensors_count" in data
        assert "patterns_count" in data
        assert "agents_count" in data

    def test_get_settings(self, client):
        """Test getting settings."""
        response = client.get("/api/system/settings")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_update_settings(self, client):
        """Test updating settings."""
        settings = {"test_key": "test_value", "another_key": 123}

        response = client.put("/api/system/settings", json={"settings": settings})
        assert response.status_code == 200
        assert "test_key" in response.json()["updated"]
        assert "another_key" in response.json()["updated"]

        # Verify settings were saved
        get_response = client.get("/api/system/settings")
        saved = get_response.json()
        assert saved["test_key"] == "test_value"
        assert saved["another_key"] == 123

    def test_restart(self, client):
        """Test restart endpoint."""
        response = client.post("/api/system/restart")
        assert response.status_code == 200
        assert "message" in response.json()


class TestHealthDetails:
    """Tests for health endpoint details."""

    def test_health_database_status(self, client):
        """Test that health includes database status."""
        response = client.get("/api/system/health")
        data = response.json()

        assert "database" in data
        assert data["database"]["status"] == "ok"

    def test_health_sensor_structure(self, client):
        """Test that health includes sensor structure."""
        response = client.get("/api/system/health")
        data = response.json()

        # Verify sensor health structure exists
        assert "sensors" in data
        assert "total" in data["sensors"]
        assert "healthy" in data["sensors"]
        assert "unhealthy" in data["sensors"]

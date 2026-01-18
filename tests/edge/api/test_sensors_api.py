"""Tests for sensor API endpoints."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from spaxiom.core import SensorRegistry
from spaxiom.edge.database import EdgeDatabase, SensorRepository
from spaxiom.edge.sensor_registry import PersistentSensorRegistry
from spaxiom.edge.api.app import create_app, setup_app_state


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

    sensor_repo = SensorRepository(db)
    sensor_registry = PersistentSensorRegistry(db)

    app = create_app()
    setup_app_state(
        app,
        db=db,
        sensor_registry=sensor_registry,
        sensor_repo=sensor_repo,
        zone_repo=None,
        pattern_repo=None,
        agent_repo=None,
        event_repo=None,
        settings_repo=None,
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


class TestSensorAPI:
    """Tests for sensor API endpoints."""

    def test_list_sensors_empty(self, client):
        """Test listing sensors when none exist."""
        response = client.get("/api/sensors")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_sensor(self, client):
        """Test creating a new sensor."""
        sensor_data = {
            "name": "test_sensor",
            "sensor_type": "random",
            "location": [1.0, 2.0, 0.0],
            "config": {"hz": 10},
            "enabled": True,
        }

        response = client.post("/api/sensors", json=sensor_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "test_sensor"
        assert data["sensor_type"] == "random"
        assert data["enabled"] is True
        assert "id" in data

    def test_create_sensor_duplicate_name(self, client):
        """Test that duplicate names are rejected."""
        sensor_data = {"name": "duplicate", "sensor_type": "random"}

        response1 = client.post("/api/sensors", json=sensor_data)
        assert response1.status_code == 201

        response2 = client.post("/api/sensors", json=sensor_data)
        assert response2.status_code == 400
        assert "already exist" in response2.json()["detail"].lower()

    def test_get_sensor(self, client):
        """Test getting a sensor by ID."""
        # Create sensor
        sensor_data = {"name": "get_test", "sensor_type": "random"}
        create_response = client.post("/api/sensors", json=sensor_data)
        sensor_id = create_response.json()["id"]

        # Get sensor
        response = client.get(f"/api/sensors/{sensor_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "get_test"

    def test_get_sensor_not_found(self, client):
        """Test getting a non-existent sensor."""
        response = client.get("/api/sensors/nonexistent-id")
        assert response.status_code == 404

    def test_update_sensor(self, client):
        """Test updating a sensor."""
        # Create sensor
        sensor_data = {"name": "update_test", "sensor_type": "random"}
        create_response = client.post("/api/sensors", json=sensor_data)
        sensor_id = create_response.json()["id"]

        # Update sensor
        update_data = {"name": "updated_name", "enabled": False}
        response = client.put(f"/api/sensors/{sensor_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "updated_name"
        assert response.json()["enabled"] is False

    def test_delete_sensor(self, client):
        """Test deleting a sensor."""
        # Create sensor
        sensor_data = {"name": "delete_test", "sensor_type": "random"}
        create_response = client.post("/api/sensors", json=sensor_data)
        sensor_id = create_response.json()["id"]

        # Delete sensor
        response = client.delete(f"/api/sensors/{sensor_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/sensors/{sensor_id}")
        assert get_response.status_code == 404

    def test_delete_sensor_not_found(self, client):
        """Test deleting a non-existent sensor."""
        response = client.delete("/api/sensors/nonexistent-id")
        assert response.status_code == 404

    def test_test_sensor(self, client):
        """Test testing a sensor."""
        # Create sensor
        sensor_data = {
            "name": "test_me",
            "sensor_type": "random",
            "location": [0, 0, 0],
        }
        create_response = client.post("/api/sensors", json=sensor_data)
        sensor_id = create_response.json()["id"]

        # Test sensor
        response = client.post(f"/api/sensors/{sensor_id}/test")
        assert response.status_code == 200

        data = response.json()
        assert data["sensor_id"] == sensor_id
        assert data["success"] is True
        assert data["value"] is not None
        assert data["read_time_ms"] is not None

    def test_get_sensor_health(self, client):
        """Test getting sensor health."""
        # Create sensor
        sensor_data = {
            "name": "health_test",
            "sensor_type": "random",
            "location": [0, 0, 0],
        }
        create_response = client.post("/api/sensors", json=sensor_data)
        sensor_id = create_response.json()["id"]

        # Get health
        response = client.get(f"/api/sensors/{sensor_id}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["sensor_id"] == sensor_id
        assert data["status"] in ["ok", "error", "timeout", "unknown"]

    def test_list_sensor_types(self, client):
        """Test listing available sensor types."""
        response = client.get("/api/sensors/types")
        assert response.status_code == 200

        types = response.json()
        assert "random" in types
        assert "toggling" in types

    def test_list_sensors_with_filter(self, client):
        """Test listing sensors with enabled_only filter."""
        # Create enabled and disabled sensors
        client.post(
            "/api/sensors",
            json={"name": "enabled", "sensor_type": "random", "enabled": True},
        )
        client.post(
            "/api/sensors",
            json={"name": "disabled", "sensor_type": "random", "enabled": False},
        )

        # List all
        all_response = client.get("/api/sensors")
        assert len(all_response.json()) == 2

        # List enabled only
        enabled_response = client.get("/api/sensors?enabled_only=true")
        assert len(enabled_response.json()) == 1
        assert enabled_response.json()[0]["name"] == "enabled"

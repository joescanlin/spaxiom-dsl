"""Tests for spaxiom.edge.database module."""

import os
import tempfile
import pytest

from spaxiom.edge.database import (
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
    SettingsRepository,
    SensorRecord,
    SCHEMA_VERSION,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = EdgeDatabase(db_path)
    db.init()

    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestEdgeDatabase:
    """Tests for EdgeDatabase class."""

    def test_init_creates_database(self, temp_db):
        """Test that init creates the database file."""
        assert temp_db.db_path.exists()

    def test_schema_version(self, temp_db):
        """Test schema version tracking."""
        version = temp_db.get_schema_version()
        assert version == SCHEMA_VERSION

    def test_health_check(self, temp_db):
        """Test database health check."""
        health = temp_db.check_health()
        assert health["status"] == "ok"
        assert health["schema_version"] == SCHEMA_VERSION
        assert "size_bytes" in health

    def test_connection_context_manager(self, temp_db):
        """Test connection context manager."""
        with temp_db.connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1


class TestSensorRepository:
    """Tests for SensorRepository class."""

    def test_create_sensor(self, temp_db):
        """Test creating a sensor."""
        repo = SensorRepository(temp_db)

        sensor = repo.create(
            name="test_sensor",
            sensor_type="random",
            location=(1.0, 2.0, 3.0),
            config={"min_val": 0, "max_val": 100},
        )

        assert sensor.id is not None
        assert sensor.name == "test_sensor"
        assert sensor.sensor_type == "random"
        assert sensor.location == (1.0, 2.0, 3.0)
        assert sensor.config == {"min_val": 0, "max_val": 100}
        assert sensor.enabled is True

    def test_get_sensor(self, temp_db):
        """Test getting a sensor by ID."""
        repo = SensorRepository(temp_db)
        created = repo.create(name="get_test", sensor_type="random")

        fetched = repo.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == created.name

    def test_get_sensor_by_name(self, temp_db):
        """Test getting a sensor by name."""
        repo = SensorRepository(temp_db)
        repo.create(name="named_sensor", sensor_type="random")

        fetched = repo.get_by_name("named_sensor")

        assert fetched is not None
        assert fetched.name == "named_sensor"

    def test_get_all_sensors(self, temp_db):
        """Test getting all sensors."""
        repo = SensorRepository(temp_db)
        repo.create(name="sensor1", sensor_type="random", enabled=True)
        repo.create(name="sensor2", sensor_type="random", enabled=False)

        all_sensors = repo.get_all()
        enabled_sensors = repo.get_all(enabled_only=True)

        assert len(all_sensors) == 2
        assert len(enabled_sensors) == 1

    def test_update_sensor(self, temp_db):
        """Test updating a sensor."""
        repo = SensorRepository(temp_db)
        created = repo.create(name="update_test", sensor_type="random")

        updated = repo.update(
            created.id,
            name="updated_name",
            config={"new_key": "new_value"},
        )

        assert updated is not None
        assert updated.name == "updated_name"
        assert updated.config == {"new_key": "new_value"}

    def test_delete_sensor(self, temp_db):
        """Test deleting a sensor."""
        repo = SensorRepository(temp_db)
        created = repo.create(name="delete_test", sensor_type="random")

        deleted = repo.delete(created.id)
        fetched = repo.get(created.id)

        assert deleted is True
        assert fetched is None

    def test_count_sensors(self, temp_db):
        """Test counting sensors."""
        repo = SensorRepository(temp_db)

        assert repo.count() == 0

        repo.create(name="sensor1", sensor_type="random")
        repo.create(name="sensor2", sensor_type="random")

        assert repo.count() == 2


class TestZoneRepository:
    """Tests for ZoneRepository class."""

    def test_create_zone(self, temp_db):
        """Test creating a zone."""
        repo = ZoneRepository(temp_db)

        zone = repo.create(
            name="test_zone",
            zone_type="rectangle",
            geometry={"x": 0, "y": 0, "width": 10, "height": 10},
            metadata={"floor": 1},
        )

        assert zone.id is not None
        assert zone.name == "test_zone"
        assert zone.zone_type == "rectangle"
        assert zone.geometry == {"x": 0, "y": 0, "width": 10, "height": 10}

    def test_get_zone(self, temp_db):
        """Test getting a zone by ID."""
        repo = ZoneRepository(temp_db)
        created = repo.create(
            name="get_zone",
            zone_type="rectangle",
            geometry={"x": 0, "y": 0},
        )

        fetched = repo.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_update_zone(self, temp_db):
        """Test updating a zone."""
        repo = ZoneRepository(temp_db)
        created = repo.create(
            name="update_zone",
            zone_type="rectangle",
            geometry={"x": 0, "y": 0},
        )

        updated = repo.update(
            created.id,
            geometry={"x": 5, "y": 5, "width": 20, "height": 20},
        )

        assert updated is not None
        assert updated.geometry["x"] == 5

    def test_delete_zone(self, temp_db):
        """Test deleting a zone."""
        repo = ZoneRepository(temp_db)
        created = repo.create(
            name="delete_zone",
            zone_type="rectangle",
            geometry={"x": 0, "y": 0},
        )

        deleted = repo.delete(created.id)

        assert deleted is True
        assert repo.get(created.id) is None


class TestPatternRepository:
    """Tests for PatternRepository class."""

    def test_create_pattern(self, temp_db):
        """Test creating a pattern."""
        repo = PatternRepository(temp_db)

        pattern = repo.create(
            name="test_pattern",
            pattern_type="occupancy_field",
            config={"threshold": 0.5},
            zones=["zone1", "zone2"],
            sensors=["sensor1"],
        )

        assert pattern.id is not None
        assert pattern.name == "test_pattern"
        assert pattern.pattern_type == "occupancy_field"
        assert pattern.zones == ["zone1", "zone2"]
        assert pattern.sensors == ["sensor1"]

    def test_get_pattern(self, temp_db):
        """Test getting a pattern by ID."""
        repo = PatternRepository(temp_db)
        created = repo.create(
            name="get_pattern",
            pattern_type="queue_flow",
            config={},
        )

        fetched = repo.get(created.id)

        assert fetched is not None
        assert fetched.pattern_type == "queue_flow"

    def test_update_pattern(self, temp_db):
        """Test updating a pattern."""
        repo = PatternRepository(temp_db)
        created = repo.create(
            name="update_pattern",
            pattern_type="occupancy_field",
            config={"old": "value"},
        )

        updated = repo.update(
            created.id,
            config={"new": "value"},
            enabled=False,
        )

        assert updated is not None
        assert updated.config == {"new": "value"}
        assert updated.enabled is False


class TestAgentRepository:
    """Tests for AgentRepository class."""

    def test_create_agent(self, temp_db):
        """Test creating an agent."""
        # First create a pattern
        pattern_repo = PatternRepository(temp_db)
        pattern = pattern_repo.create(
            name="agent_pattern",
            pattern_type="occupancy_field",
            config={},
        )

        agent_repo = AgentRepository(temp_db)
        agent = agent_repo.create(
            name="test_agent",
            pattern_id=pattern.id,
            config={"tick_rate": 10},
        )

        assert agent.id is not None
        assert agent.name == "test_agent"
        assert agent.pattern_id == pattern.id
        assert agent.status == "stopped"

    def test_update_agent_status(self, temp_db):
        """Test updating agent status."""
        pattern_repo = PatternRepository(temp_db)
        pattern = pattern_repo.create(
            name="status_pattern",
            pattern_type="occupancy_field",
            config={},
        )

        agent_repo = AgentRepository(temp_db)
        agent = agent_repo.create(
            name="status_agent",
            pattern_id=pattern.id,
        )

        # Start agent
        updated = agent_repo.update_status(agent.id, "running", pid=12345)
        assert updated.status == "running"
        assert updated.pid == 12345
        assert updated.started_at is not None

        # Stop agent
        updated = agent_repo.update_status(agent.id, "stopped")
        assert updated.status == "stopped"
        assert updated.pid is None
        assert updated.stopped_at is not None

    def test_get_agents_by_status(self, temp_db):
        """Test getting agents by status."""
        pattern_repo = PatternRepository(temp_db)
        pattern = pattern_repo.create(
            name="multi_pattern",
            pattern_type="occupancy_field",
            config={},
        )

        agent_repo = AgentRepository(temp_db)
        agent1 = agent_repo.create(name="agent1", pattern_id=pattern.id)
        agent_repo.create(
            name="agent2", pattern_id=pattern.id
        )  # Second agent stays stopped

        agent_repo.update_status(agent1.id, "running", pid=111)

        running = agent_repo.get_all(status="running")
        stopped = agent_repo.get_all(status="stopped")

        assert len(running) == 1
        assert len(stopped) == 1


class TestEventRepository:
    """Tests for EventRepository class."""

    def test_log_event(self, temp_db):
        """Test logging an event."""
        repo = EventRepository(temp_db)

        event = repo.log(
            event_type="sensor_read",
            source="sensor1",
            data={"value": 42.5},
            severity="info",
        )

        assert event.id is not None
        assert event.event_type == "sensor_read"
        assert event.data == {"value": 42.5}

    def test_query_events(self, temp_db):
        """Test querying events."""
        repo = EventRepository(temp_db)

        repo.log(event_type="type_a", source="source1")
        repo.log(event_type="type_b", source="source1")
        repo.log(event_type="type_a", source="source2")

        type_a = repo.query(event_type="type_a")
        source1 = repo.query(source="source1")

        assert len(type_a) == 2
        assert len(source1) == 2

    def test_event_count(self, temp_db):
        """Test counting events."""
        repo = EventRepository(temp_db)

        assert repo.count() == 0

        repo.log(event_type="test")
        repo.log(event_type="test")

        assert repo.count() == 2


class TestSettingsRepository:
    """Tests for SettingsRepository class."""

    def test_set_and_get(self, temp_db):
        """Test setting and getting a value."""
        repo = SettingsRepository(temp_db)

        repo.set("my_key", {"nested": "value", "number": 42})

        value = repo.get("my_key")

        assert value == {"nested": "value", "number": 42}

    def test_get_default(self, temp_db):
        """Test getting with default value."""
        repo = SettingsRepository(temp_db)

        value = repo.get("nonexistent", default="default_value")

        assert value == "default_value"

    def test_update_setting(self, temp_db):
        """Test updating an existing setting."""
        repo = SettingsRepository(temp_db)

        repo.set("update_key", "original")
        repo.set("update_key", "updated")

        value = repo.get("update_key")

        assert value == "updated"

    def test_delete_setting(self, temp_db):
        """Test deleting a setting."""
        repo = SettingsRepository(temp_db)

        repo.set("delete_key", "value")
        deleted = repo.delete("delete_key")

        assert deleted is True
        assert repo.get("delete_key") is None

    def test_get_all_settings(self, temp_db):
        """Test getting all settings."""
        repo = SettingsRepository(temp_db)

        repo.set("key1", "value1")
        repo.set("key2", "value2")

        all_settings = repo.get_all()

        assert all_settings == {"key1": "value1", "key2": "value2"}


class TestRecordDataclasses:
    """Tests for record dataclasses."""

    def test_sensor_record_location(self):
        """Test SensorRecord location property."""
        record = SensorRecord(
            id="1",
            name="test",
            sensor_type="random",
            location_x=1.0,
            location_y=2.0,
            location_z=3.0,
        )

        assert record.location == (1.0, 2.0, 3.0)

        record_no_loc = SensorRecord(
            id="2",
            name="test2",
            sensor_type="random",
        )

        assert record_no_loc.location is None

    def test_record_to_dict(self):
        """Test record serialization."""
        record = SensorRecord(
            id="1",
            name="test",
            sensor_type="random",
            config={"key": "value"},
        )

        d = record.to_dict()

        assert d["id"] == "1"
        assert d["name"] == "test"
        assert d["config"] == {"key": "value"}

"""Tests for AgentManager and PatternFactory."""

import asyncio
import pytest
import tempfile
from pathlib import Path

from spaxiom.edge.database import (
    EdgeDatabase,
    SensorRepository,
    ZoneRepository,
    PatternRepository,
    AgentRepository,
    EventRepository,
)
from spaxiom.edge.sensor_registry import PersistentSensorRegistry
from spaxiom.edge.pattern_factory import PatternFactory
from spaxiom.edge.agent_manager import AgentManager, EventBus


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = EdgeDatabase(db_path)
    db.init()
    yield db

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sensor_registry(temp_db):
    """Create a sensor registry."""
    return PersistentSensorRegistry(temp_db)


@pytest.fixture
def pattern_factory(temp_db, sensor_registry):
    """Create a pattern factory."""
    return PatternFactory(temp_db, sensor_registry)


@pytest.fixture
def repos(temp_db):
    """Create all repositories."""
    return {
        "sensor": SensorRepository(temp_db),
        "zone": ZoneRepository(temp_db),
        "pattern": PatternRepository(temp_db),
        "agent": AgentRepository(temp_db),
        "event": EventRepository(temp_db),
    }


@pytest.fixture
def agent_manager(temp_db, pattern_factory, repos):
    """Create an agent manager."""
    return AgentManager(
        db=temp_db,
        pattern_factory=pattern_factory,
        agent_repo=repos["agent"],
        pattern_repo=repos["pattern"],
        event_repo=repos["event"],
    )


class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_publish(self):
        """Test basic pub/sub."""
        bus = EventBus()
        queue = bus.subscribe()

        await bus.publish({"type": "test", "value": 42})

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "test"
        assert event["value"] == 42

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers receive the same event."""
        bus = EventBus()
        queue1 = bus.subscribe()
        queue2 = bus.subscribe()

        await bus.publish({"type": "broadcast"})

        event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert event1["type"] == "broadcast"
        assert event2["type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing removes from subscribers."""
        bus = EventBus()
        queue = bus.subscribe()

        assert len(bus._subscribers) == 1
        bus.unsubscribe(queue)
        assert len(bus._subscribers) == 0


class TestPatternFactory:
    """Tests for PatternFactory."""

    def test_validate_config_missing_zone(self, pattern_factory):
        """Test validation catches missing zones."""
        result = pattern_factory.validate_config(
            pattern_type="occupancy_field",
            config={},
            zone_ids=[],
            sensor_ids=[],
        )

        assert not result["valid"]
        assert "requires at least one zone" in str(result["errors"])

    def test_validate_config_missing_sensor(self, pattern_factory, repos):
        """Test validation catches missing sensors."""
        # Create a zone
        zone = repos["zone"].create(
            name="test_zone",
            zone_type="rectangle",
            geometry={"x": 0, "y": 0, "width": 10, "height": 10},
        )

        result = pattern_factory.validate_config(
            pattern_type="occupancy_field",
            config={},
            zone_ids=[zone.id],
            sensor_ids=[],
        )

        assert not result["valid"]
        assert "requires at least one sensor" in str(result["errors"])

    def test_validate_config_nonexistent_zone(self, pattern_factory):
        """Test validation catches nonexistent zones."""
        result = pattern_factory.validate_config(
            pattern_type="occupancy_field",
            config={},
            zone_ids=["nonexistent"],
            sensor_ids=[],
        )

        assert not result["valid"]
        assert "not found" in str(result["errors"])


class TestAgentManager:
    """Tests for AgentManager."""

    @pytest.mark.asyncio
    async def test_start_stop(self, agent_manager):
        """Test starting and stopping the agent manager."""
        await agent_manager.start()
        assert agent_manager._running
        assert agent_manager._watchdog_task is not None

        await agent_manager.stop()
        assert not agent_manager._running

    @pytest.mark.asyncio
    async def test_check_health(self, agent_manager):
        """Test health check."""
        await agent_manager.start()

        health = agent_manager.check_health()
        assert health["status"] == "healthy"
        assert health["running_agents"] == 0
        assert health["watchdog_active"]

        await agent_manager.stop()

    @pytest.mark.asyncio
    async def test_deploy_pattern_not_found(self, agent_manager):
        """Test deploying a nonexistent pattern raises error."""
        await agent_manager.start()

        with pytest.raises(ValueError, match="not found"):
            await agent_manager.deploy("nonexistent")

        await agent_manager.stop()

    @pytest.mark.asyncio
    async def test_get_status_unknown_agent(self, agent_manager):
        """Test getting status of unknown agent."""
        status = agent_manager.get_status("unknown")
        assert status["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_restore_agents_empty(self, agent_manager):
        """Test restore with no running agents."""
        await agent_manager.start()

        restored = await agent_manager.restore_agents()
        assert restored == 0

        await agent_manager.stop()

    @pytest.mark.asyncio
    async def test_get_all_status(self, agent_manager, repos):
        """Test getting all agent statuses."""
        # Create an agent record
        repos["pattern"].create(
            name="test_pattern",
            pattern_type="custom",
            config={},
        )

        pattern = repos["pattern"].get_by_name("test_pattern")
        repos["agent"].create(
            name="test_agent",
            pattern_id=pattern.id,
        )

        statuses = agent_manager.get_all_status()
        assert len(statuses) == 1

    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self, agent_manager):
        """Test stopping an agent that's not running."""
        result = await agent_manager.stop_agent("nonexistent")
        assert not result

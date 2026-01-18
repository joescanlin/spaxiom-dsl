"""
Agent Manager for Edge Deployment.

Manages the lifecycle of deployed agents including:
- Deployment from patterns
- Start/stop/restart operations
- Status monitoring
- Auto-restore on startup
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from spaxiom.edge.database import (
        EdgeDatabase,
        AgentRepository,
        PatternRepository,
        EventRepository,
    )
    from spaxiom.edge.pattern_factory import PatternFactory
    from spaxiom.intent.pattern import Pattern

logger = logging.getLogger(__name__)


@dataclass
class AgentStats:
    """Runtime statistics for an agent."""

    tick_count: int = 0
    events_emitted: int = 0
    last_tick_time: Optional[float] = None
    avg_tick_ms: float = 0.0
    started_at: Optional[datetime] = None
    errors: int = 0
    last_error: Optional[str] = None


@dataclass
class RunningAgent:
    """Represents a running agent instance."""

    agent_id: str
    pattern_id: str
    pattern: Pattern
    task: Optional[asyncio.Task] = None
    stats: AgentStats = field(default_factory=AgentStats)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)


class EventBus:
    """Simple pub/sub event bus for agent events."""

    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def publish(self, event: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass  # Drop events if subscriber is slow

    def subscribe(self, maxsize: int = 100) -> asyncio.Queue:
        """Subscribe to events.

        Returns:
            Queue that will receive events
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)


class AgentManager:
    """Manages lifecycle of deployed agents."""

    def __init__(
        self,
        db: EdgeDatabase,
        pattern_factory: PatternFactory,
        agent_repo: AgentRepository,
        pattern_repo: PatternRepository,
        event_repo: EventRepository,
    ):
        """Initialize the agent manager.

        Args:
            db: Database connection
            pattern_factory: Factory for creating patterns
            agent_repo: Repository for agent records
            pattern_repo: Repository for pattern records
            event_repo: Repository for event logging
        """
        self.db = db
        self.factory = pattern_factory
        self.agents = agent_repo
        self.patterns = pattern_repo
        self.events = event_repo

        self._running_agents: Dict[str, RunningAgent] = {}
        self._event_bus = EventBus()
        self._watchdog_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def event_bus(self) -> EventBus:
        """Get the event bus for subscribing to agent events."""
        return self._event_bus

    async def start(self) -> None:
        """Start the agent manager."""
        self._running = True
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        logger.info("Agent manager started")

    async def stop(self) -> None:
        """Stop the agent manager and all running agents."""
        self._running = False

        # Stop watchdog
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass

        # Stop all running agents
        agent_ids = list(self._running_agents.keys())
        for agent_id in agent_ids:
            await self.stop_agent(agent_id)

        logger.info("Agent manager stopped")

    async def deploy(
        self,
        pattern_id: str,
        name: Optional[str] = None,
        config_overrides: Optional[Dict] = None,
    ) -> str:
        """Deploy a pattern as a running agent.

        Args:
            pattern_id: ID of the pattern to deploy
            name: Optional custom name for the agent
            config_overrides: Optional config overrides

        Returns:
            Agent ID

        Raises:
            ValueError: If pattern not found or invalid
        """
        # Load pattern
        pattern_record = self.patterns.get(pattern_id)
        if not pattern_record:
            raise ValueError(f"Pattern '{pattern_id}' not found")

        if not pattern_record.enabled:
            raise ValueError(f"Pattern '{pattern_id}' is disabled")

        # Create pattern instance
        pattern = self.factory.create(pattern_record)
        if not pattern:
            raise ValueError("Failed to create pattern instance")

        # Create agent record
        agent_name = name or f"{pattern_record.name} Agent"
        agent_record = self.agents.create(
            name=agent_name,
            pattern_id=pattern_id,
            config=config_overrides or {},
        )

        # Create running agent
        running_agent = RunningAgent(
            agent_id=agent_record.id,
            pattern_id=pattern_id,
            pattern=pattern,
            stats=AgentStats(started_at=datetime.now()),
        )

        # Start the agent task
        running_agent.task = asyncio.create_task(
            self._run_agent(running_agent),
            name=f"agent-{agent_record.id}",
        )
        self._running_agents[agent_record.id] = running_agent

        # Update status
        self.agents.update_status(agent_record.id, "running")

        # Log event
        self.events.log(
            event_type="agent_deployed",
            source=agent_record.id,
            data={
                "pattern_id": pattern_id,
                "pattern_name": pattern_record.name,
                "agent_name": agent_name,
            },
            severity="info",
        )

        await self._event_bus.publish(
            {
                "type": "agent_deployed",
                "agent_id": agent_record.id,
                "pattern_id": pattern_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"Deployed agent '{agent_name}' (id={agent_record.id})")
        return agent_record.id

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a running agent.

        Args:
            agent_id: ID of the agent to stop

        Returns:
            True if agent was stopped
        """
        running = self._running_agents.get(agent_id)
        if not running:
            return False

        # Signal stop
        running.stop_event.set()

        # Wait for task to complete
        if running.task and not running.task.done():
            running.task.cancel()
            try:
                await asyncio.wait_for(running.task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Remove from running agents
        del self._running_agents[agent_id]

        # Update status
        self.agents.update_status(agent_id, "stopped")

        # Log event
        self.events.log(
            event_type="agent_stopped",
            source=agent_id,
            severity="info",
        )

        await self._event_bus.publish(
            {
                "type": "agent_stopped",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"Stopped agent {agent_id}")
        return True

    async def restart_agent(self, agent_id: str) -> bool:
        """Restart an agent.

        Args:
            agent_id: ID of the agent to restart

        Returns:
            True if agent was restarted
        """
        # Get agent info before stopping
        agent_record = self.agents.get(agent_id)
        if not agent_record:
            return False

        pattern_id = agent_record.pattern_id
        config = agent_record.config

        # Stop if running
        if agent_id in self._running_agents:
            await self.stop_agent(agent_id)

        # Re-deploy
        try:
            await self.deploy(
                pattern_id, name=agent_record.name, config_overrides=config
            )
            return True
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False

    async def start_agent(self, agent_id: str) -> bool:
        """Start a stopped agent.

        Args:
            agent_id: ID of the agent to start

        Returns:
            True if agent was started
        """
        # Check if already running
        if agent_id in self._running_agents:
            return True

        # Get agent record
        agent_record = self.agents.get(agent_id)
        if not agent_record:
            return False

        # Deploy the agent's pattern
        try:
            pattern_record = self.patterns.get(agent_record.pattern_id)
            if not pattern_record:
                raise ValueError("Pattern not found")

            pattern = self.factory.create(pattern_record)
            if not pattern:
                raise ValueError("Failed to create pattern")

            # Create running agent
            running_agent = RunningAgent(
                agent_id=agent_id,
                pattern_id=agent_record.pattern_id,
                pattern=pattern,
                stats=AgentStats(started_at=datetime.now()),
            )

            # Start the agent task
            running_agent.task = asyncio.create_task(
                self._run_agent(running_agent),
                name=f"agent-{agent_id}",
            )
            self._running_agents[agent_id] = running_agent

            # Update status
            self.agents.update_status(agent_id, "running")

            logger.info(f"Started agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
            self.agents.update_status(agent_id, "error", error=str(e))
            return False

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status including runtime stats.

        Args:
            agent_id: ID of the agent

        Returns:
            Status dictionary
        """
        running = self._running_agents.get(agent_id)
        if running:
            return {
                "status": "running",
                "tick_count": running.stats.tick_count,
                "events_emitted": running.stats.events_emitted,
                "avg_tick_ms": running.stats.avg_tick_ms,
                "started_at": (
                    running.stats.started_at.isoformat()
                    if running.stats.started_at
                    else None
                ),
                "errors": running.stats.errors,
                "last_error": running.stats.last_error,
            }

        # Check database for stopped agent
        record = self.agents.get(agent_id)
        if record:
            return {
                "status": record.status,
                "started_at": record.started_at,
                "stopped_at": record.stopped_at,
                "last_error": record.last_error,
            }

        return {"status": "unknown"}

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents.

        Returns:
            Dictionary mapping agent IDs to status
        """
        result = {}

        # Get all agent records
        records = self.agents.get_all()
        for record in records:
            result[record.id] = self.get_status(record.id)

        return result

    async def restore_agents(self) -> int:
        """Restore agents that were running before shutdown.

        Returns:
            Number of agents restored
        """
        restored = 0
        records = self.agents.get_all(status="running")

        for record in records:
            try:
                logger.info(f"Restoring agent {record.id} ({record.name})")
                success = await self.start_agent(record.id)
                if success:
                    restored += 1
                else:
                    self.agents.update_status(
                        record.id, "error", error="Failed to restore"
                    )
            except Exception as e:
                logger.error(f"Failed to restore agent {record.id}: {e}")
                self.agents.update_status(record.id, "error", error=str(e))

        if restored > 0:
            logger.info(f"Restored {restored} agents")

        return restored

    async def _run_agent(self, agent: RunningAgent) -> None:
        """Run an agent's main loop.

        Args:
            agent: Running agent instance
        """
        tick_times: List[float] = []

        try:
            while not agent.stop_event.is_set():
                start_time = time.monotonic()

                try:
                    # Update the pattern
                    dt = 0.1  # 100ms tick
                    events = agent.pattern.update(dt, {})

                    # Process emitted events
                    if events:
                        for event in events:
                            agent.stats.events_emitted += 1
                            await self._event_bus.publish(
                                {
                                    "type": "pattern_event",
                                    "agent_id": agent.agent_id,
                                    "event": (
                                        event.to_dict()
                                        if hasattr(event, "to_dict")
                                        else str(event)
                                    ),
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

                    agent.stats.tick_count += 1

                except Exception as e:
                    agent.stats.errors += 1
                    agent.stats.last_error = str(e)
                    logger.error(f"Agent {agent.agent_id} tick error: {e}")

                # Track timing
                elapsed = (time.monotonic() - start_time) * 1000
                tick_times.append(elapsed)
                if len(tick_times) > 100:
                    tick_times.pop(0)
                agent.stats.avg_tick_ms = sum(tick_times) / len(tick_times)
                agent.stats.last_tick_time = time.monotonic()

                # Wait for next tick
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} crashed: {e}")
            agent.stats.last_error = str(e)
            self.agents.update_status(agent.agent_id, "error", error=str(e))

            await self._event_bus.publish(
                {
                    "type": "agent_error",
                    "agent_id": agent.agent_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    async def _watchdog_loop(self) -> None:
        """Watchdog loop to monitor agent health."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                for agent_id, agent in list(self._running_agents.items()):
                    # Check if task is still running
                    if agent.task and agent.task.done():
                        exc = agent.task.exception()
                        if exc:
                            logger.error(f"Agent {agent_id} task died: {exc}")
                            self.agents.update_status(agent_id, "error", error=str(exc))

                            # Attempt restart
                            logger.info(f"Attempting to restart agent {agent_id}")
                            del self._running_agents[agent_id]
                            await self.start_agent(agent_id)

                    # Check for stalled agents
                    if agent.stats.last_tick_time:
                        time_since_tick = time.monotonic() - agent.stats.last_tick_time
                        if time_since_tick > 60:  # No tick in 60 seconds
                            logger.warning(f"Agent {agent_id} appears stalled")
                            await self._event_bus.publish(
                                {
                                    "type": "agent_stalled",
                                    "agent_id": agent_id,
                                    "seconds_since_tick": time_since_tick,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}")

    def check_health(self) -> Dict[str, Any]:
        """Check health of agent manager.

        Returns:
            Health status dictionary
        """
        running_count = len(self._running_agents)
        total_records = self.agents.count()

        return {
            "status": "healthy" if self._running else "stopped",
            "running_agents": running_count,
            "total_agents": total_records,
            "watchdog_active": self._watchdog_task is not None
            and not self._watchdog_task.done(),
        }

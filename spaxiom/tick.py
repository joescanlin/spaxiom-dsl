"""
Phased tick runtime for Spaxiom DSL.

Implements the deterministic 4-phase tick execution model:
1. Sensor reads (concurrent)
2. Pattern updates (dependency-ordered)
3. Condition evaluation (polling or event-driven)
4. Callback dispatch (isolated)

This module provides:
- TickStats: per-tick instrumentation data
- TickProfiler: collects and aggregates stats across ticks
- PhasedTickRunner: the phased tick loop

MIGRATION STATUS (as of Step 4):
---------------------------------
This is the NEW runtime foundation with full pattern integration.

COMPLETED:
- Step 2: 4-phase tick execution, profiling
- Step 3: Condition dependency tracking, event-driven evaluation
- Step 4: Pattern base class integration, topological update ordering

After Step 4, spaxiom/runtime.py's start_runtime() and start_blocking() will
delegate to PhasedTickRunner.run() internally.

See also: spaxiom/runtime.py (legacy runtime with signal handling and CLI integration)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from collections import deque

from spaxiom.core import SensorRegistry, Sensor
from spaxiom.events import EVENT_HANDLERS

logger = logging.getLogger(__name__)


@dataclass
class TickStats:
    """Per-tick instrumentation data."""

    tick_number: int
    tick_start_time: float
    tick_duration_ms: float = 0.0

    # Phase timings in milliseconds
    phase1_sensor_read_ms: float = 0.0
    phase2_pattern_update_ms: float = 0.0
    phase3_condition_eval_ms: float = 0.0
    phase4_callback_dispatch_ms: float = 0.0

    # Counts
    sensors_read: int = 0
    patterns_updated: int = 0
    events_emitted: int = 0
    conditions_evaluated: int = 0
    callbacks_dispatched: int = 0
    callback_failures: int = 0

    # Safety monitoring
    safety_monitors_checked: int = 0
    safety_violations: int = 0
    safety_violation_events: List[Any] = field(default_factory=list)

    # Phase ordering proof
    phase_order: List[str] = field(default_factory=list)

    # Events emitted this tick (for inspection)
    pattern_events: List[Any] = field(default_factory=list)


class TickProfiler:
    """Collects and aggregates tick statistics."""

    def __init__(self, max_history: int = 1000):
        self._history: deque = deque(maxlen=max_history)
        self._total_ticks: int = 0
        self._total_callback_failures: int = 0
        self._enabled: bool = False

    def enable(self) -> None:
        """Enable profiling."""
        self._enabled = True

    def disable(self) -> None:
        """Disable profiling."""
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled

    def record_tick(self, stats: TickStats) -> None:
        """Record stats for a completed tick."""
        if not self._enabled:
            return
        self._history.append(stats)
        self._total_ticks += 1
        self._total_callback_failures += stats.callback_failures

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics.

        Returns:
            Dict with keys:
            - tick_count: total ticks recorded
            - avg_tick_ms: average tick duration
            - phase1_sensor_read_avg_ms: average sensor read phase time
            - phase2_pattern_update_avg_ms: average pattern update phase time
            - phase3_condition_eval_avg_ms: average condition eval phase time
            - phase4_callback_dispatch_avg_ms: average callback dispatch phase time
            - callback_failures: total callback failures
            - sensors_read_total: total sensor reads
            - conditions_evaluated_total: total condition evaluations
            - callbacks_dispatched_total: total callbacks dispatched
        """
        if not self._history:
            return {
                "tick_count": 0,
                "avg_tick_ms": 0.0,
                "phase1_sensor_read_avg_ms": 0.0,
                "phase2_pattern_update_avg_ms": 0.0,
                "phase3_condition_eval_avg_ms": 0.0,
                "phase4_callback_dispatch_avg_ms": 0.0,
                "callback_failures": 0,
                "sensors_read_total": 0,
                "conditions_evaluated_total": 0,
                "callbacks_dispatched_total": 0,
            }

        count = len(self._history)
        return {
            "tick_count": self._total_ticks,
            "avg_tick_ms": sum(s.tick_duration_ms for s in self._history) / count,
            "phase1_sensor_read_avg_ms": sum(
                s.phase1_sensor_read_ms for s in self._history
            )
            / count,
            "phase2_pattern_update_avg_ms": sum(
                s.phase2_pattern_update_ms for s in self._history
            )
            / count,
            "phase3_condition_eval_avg_ms": sum(
                s.phase3_condition_eval_ms for s in self._history
            )
            / count,
            "phase4_callback_dispatch_avg_ms": sum(
                s.phase4_callback_dispatch_ms for s in self._history
            )
            / count,
            "callback_failures": self._total_callback_failures,
            "sensors_read_total": sum(s.sensors_read for s in self._history),
            "conditions_evaluated_total": sum(
                s.conditions_evaluated for s in self._history
            ),
            "callbacks_dispatched_total": sum(
                s.callbacks_dispatched for s in self._history
            ),
        }

    def get_last_tick(self) -> Optional[TickStats]:
        """Get the most recent tick stats."""
        if not self._history:
            return None
        return self._history[-1]

    def clear(self) -> None:
        """Clear all recorded stats."""
        self._history.clear()
        self._total_ticks = 0
        self._total_callback_failures = 0


class PhasedTickRunner:
    """Runs the phased tick loop.

    The tick loop executes 4 phases in deterministic order:
    1. Sensor reads - concurrent via asyncio.gather()
    2. Pattern updates - in dependency order (topological sort)
    3. Condition evaluation - polling all registered conditions
    4. Callback dispatch - isolated, exceptions don't propagate
    """

    def __init__(
        self,
        tick_rate_hz: float = 10.0,
        history_length: int = 1000,
    ):
        """Initialize the phased tick runner.

        Args:
            tick_rate_hz: Target tick rate in Hz (default 10.0 = 100ms per tick)
            history_length: Maximum condition history entries to keep
        """
        self.tick_rate_hz = tick_rate_hz
        self.tick_period_s = 1.0 / tick_rate_hz
        self.history_length = history_length

        self.profiler = TickProfiler()
        self._tick_count = 0
        self._running = False
        self._patterns: List[Any] = []  # Will hold Pattern instances when available
        self._safety_monitors: List[Any] = []  # Will hold SafetyMonitor instances

        # Condition state tracking
        self._previous_states: Dict[int, bool] = {}
        self._condition_history: deque = deque(maxlen=history_length)

        # Callbacks for extensibility
        self._on_tick_start: Optional[Callable[[int], None]] = None
        self._on_tick_end: Optional[Callable[[TickStats], None]] = None

        # Governance hooks (Step 6)
        self._retention_policy: Optional[Any] = None
        self._consent_manager: Optional[Any] = None
        self._authorizer: Optional[Any] = None
        self._audit_logger: Optional[Any] = None

    @property
    def tick_count(self) -> int:
        """Get the current tick count."""
        return self._tick_count

    @property
    def running(self) -> bool:
        """Check if the runner is running."""
        return self._running

    def register_pattern(self, pattern: Any) -> None:
        """Register a pattern for phase 2 updates.

        Args:
            pattern: A pattern instance (must have update() method)
        """
        self._patterns.append(pattern)

    def clear_patterns(self) -> None:
        """Clear all registered patterns."""
        self._patterns.clear()

    def register_safety_monitor(self, monitor: Any) -> None:
        """Register a safety monitor for runtime checking.

        Args:
            monitor: A SafetyMonitor instance
        """
        self._safety_monitors.append(monitor)

    def clear_safety_monitors(self) -> None:
        """Clear all registered safety monitors."""
        self._safety_monitors.clear()

    def set_retention_policy(self, policy: Any) -> None:
        """Set retention policy for history buffers.

        Args:
            policy: RetentionPolicy instance
        """
        self._retention_policy = policy

    def set_consent_manager(self, manager: Any) -> None:
        """Set consent manager for data collection controls.

        Args:
            manager: ConsentManager instance
        """
        self._consent_manager = manager

    def set_authorizer(self, authorizer: Any) -> None:
        """Set authorizer for access control.

        Args:
            authorizer: Authorizer instance
        """
        self._authorizer = authorizer

    def set_audit_logger(self, logger: Any) -> None:
        """Set audit logger for governance events.

        Args:
            logger: AuditLogger instance
        """
        self._audit_logger = logger

    def _check_safety_monitors(self, context: Optional[Dict[str, Any]] = None) -> tuple:
        """Check all registered safety monitors.

        Args:
            context: Optional context dict for VerifiableConditions

        Returns:
            Tuple of (monitors_checked, violations_count, violation_events)
        """
        context = context or {}
        violations = 0
        violation_events = []

        for monitor in self._safety_monitors:
            try:
                initial_violation_count = len(monitor.violations)
                is_safe = monitor.check(context)
                if not is_safe:
                    # Check if a new violation occurred
                    new_violations = monitor.violations[initial_violation_count:]
                    for v in new_violations:
                        violations += 1
                        violation_events.append(v)
            except Exception as e:
                logger.error(
                    f"Error checking safety monitor "
                    f"{getattr(monitor, 'name', monitor)}: {e}"
                )

        return len(self._safety_monitors), violations, violation_events

    async def _phase1_sensor_reads(self, sensors: List[Sensor]) -> tuple:
        """Phase 1: Read all sensors concurrently.

        Args:
            sensors: List of sensors to read

        Returns:
            Tuple of (number of sensors read, list of updated sensors)
        """
        if not sensors:
            return 0, []

        updated_sensors: list = []

        async def read_sensor(sensor: Sensor) -> bool:
            """Read a single sensor, return True on success."""
            try:
                # Track previous value for change detection
                prev_value = getattr(sensor, "last_value", None)

                # Run synchronous read in executor to not block
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, sensor.read)

                # Check if value changed (for event-driven mode)
                new_value = getattr(sensor, "last_value", None)
                if prev_value != new_value:
                    updated_sensors.append(sensor)

                return True
            except Exception as e:
                logger.error(f"Error reading sensor {sensor.name}: {e}")
                return False

        # Concurrent reads with asyncio.gather
        results = await asyncio.gather(
            *[read_sensor(s) for s in sensors], return_exceptions=True
        )
        return sum(1 for r in results if r is True), updated_sensors

    def _topological_sort_patterns(self) -> List[Any]:
        """Sort patterns in topological order based on depends_on().

        Returns:
            List of patterns in dependency order (dependencies first)
        """
        if not self._patterns:
            return []

        # Build dependency graph using object ids (patterns may not be hashable)
        pattern_ids = {id(p): p for p in self._patterns}
        in_degree = {id(p): 0 for p in self._patterns}
        dependents: Dict[int, List[int]] = {id(p): [] for p in self._patterns}

        for pattern in self._patterns:
            deps = []
            if hasattr(pattern, "depends_on"):
                deps = pattern.depends_on() or []
            for dep in deps:
                dep_id = id(dep)
                if dep_id in pattern_ids:
                    # dep must come before pattern
                    dependents[dep_id].append(id(pattern))
                    in_degree[id(pattern)] += 1

        # Kahn's algorithm for topological sort
        result = []
        queue = [pid for pid, deg in in_degree.items() if deg == 0]

        while queue:
            pid = queue.pop(0)
            result.append(pattern_ids[pid])
            for dependent_id in dependents[pid]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # If we couldn't sort all patterns, there's a cycle - just use registration order
        if len(result) != len(self._patterns):
            logger.warning(
                "Cycle detected in pattern dependencies, using registration order"
            )
            return list(self._patterns)

        return result

    def _phase2_pattern_updates(self, dt: float) -> tuple:
        """Phase 2: Update patterns in dependency order and collect events.

        Args:
            dt: Time delta since last tick in seconds

        Returns:
            Tuple of (patterns_updated, events_emitted, pattern_events_list)
        """
        # Sort patterns by dependencies
        sorted_patterns = self._topological_sort_patterns()

        count = 0
        all_events = []

        for pattern in sorted_patterns:
            if hasattr(pattern, "update"):
                try:
                    pattern.update(dt, {})
                    count += 1

                    # Collect events if pattern has emit()
                    if hasattr(pattern, "emit"):
                        events = pattern.emit()
                        if events:
                            all_events.extend(events)
                except Exception as e:
                    logger.error(
                        f"Error updating pattern {getattr(pattern, 'name', pattern)}: {e}"
                    )

        return count, len(all_events), all_events

    def _phase3_condition_eval(self, updated_sensors: Optional[list] = None) -> tuple:
        """Phase 3: Evaluate conditions based on their mode.

        For polling mode: evaluate every tick
        For event-driven mode: only evaluate if dependencies changed

        Args:
            updated_sensors: List of sensors that were updated in phase 1.
                           Used for event-driven condition optimization.

        Returns:
            Tuple of (conditions_evaluated, callbacks_to_fire)
        """
        callbacks_to_fire = []
        count = 0
        updated_sensors = updated_sensors or []

        # Build id set of updated sensors for fast lookup
        updated_sensor_ids = {id(s) for s in updated_sensors}

        for i, (condition, callback) in enumerate(EVENT_HANDLERS):
            try:
                # Check if we should evaluate this condition
                should_evaluate = True

                # Get effective mode (handles 'auto' mode)
                effective_mode = getattr(condition, "_effective_mode", "polling")

                if effective_mode == "event-driven":
                    # Only evaluate if dependencies changed
                    deps = getattr(condition, "dependencies", None)
                    if deps and len(deps) > 0:
                        if updated_sensor_ids:
                            # Check if any dependency was updated (by id)
                            dep_ids = {id(d) for d in deps}
                            should_evaluate = bool(dep_ids & updated_sensor_ids)
                        else:
                            # Has dependencies but nothing updated - skip
                            should_evaluate = False
                    # If no dependencies declared, fall back to polling behavior

                if not should_evaluate:
                    # Skip this condition but keep previous state
                    continue

                # Get previous state
                prev_state = self._previous_states.get(i, False)

                # Evaluate current state
                try:
                    current_state = bool(condition())
                except Exception as e:
                    logger.error(f"Error evaluating condition: {e}")
                    current_state = False

                # Record in history
                self._condition_history.append((time.monotonic(), i, current_state))

                # Detect rising edge
                if current_state and not prev_state:
                    callbacks_to_fire.append(callback)

                # Update previous state
                self._previous_states[i] = current_state
                count += 1

            except Exception as e:
                logger.error(f"Error in condition evaluation: {e}")

        return count, callbacks_to_fire

    async def _phase4_callback_dispatch(self, callbacks: List[Callable]) -> tuple:
        """Phase 4: Dispatch callbacks with isolation.

        Args:
            callbacks: List of callbacks to dispatch

        Returns:
            Tuple of (dispatched_count, failure_count)
        """
        if not callbacks:
            return 0, 0

        dispatched = 0
        failures = 0

        for callback in callbacks:
            try:
                # Run callback in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, callback)
                dispatched += 1
                logger.debug(f"Callback {callback.__name__} executed")
            except Exception as e:
                failures += 1
                logger.error(f"Callback {callback.__name__} failed: {e}")

        return dispatched, failures

    async def run_single_tick(self) -> TickStats:
        """Execute a single tick with all 4 phases.

        Returns:
            TickStats for the completed tick
        """
        tick_start = time.perf_counter()
        stats = TickStats(
            tick_number=self._tick_count,
            tick_start_time=time.monotonic(),
        )

        # Get sensors
        registry = SensorRegistry()
        sensors = list(registry.list_all().values())

        # Phase 1: Sensor reads
        stats.phase_order.append("sensor_read")
        phase1_start = time.perf_counter()
        sensors_read, updated_sensors = await self._phase1_sensor_reads(sensors)
        stats.sensors_read = sensors_read
        stats.phase1_sensor_read_ms = (time.perf_counter() - phase1_start) * 1000

        # Phase 2: Pattern updates (dependency-ordered with event collection)
        stats.phase_order.append("pattern_update")
        phase2_start = time.perf_counter()
        patterns_updated, events_emitted, pattern_events = self._phase2_pattern_updates(
            self.tick_period_s
        )
        stats.patterns_updated = patterns_updated
        stats.events_emitted = events_emitted
        stats.pattern_events = pattern_events
        stats.phase2_pattern_update_ms = (time.perf_counter() - phase2_start) * 1000

        # Phase 3: Condition evaluation (pass updated sensors for event-driven mode)
        stats.phase_order.append("condition_eval")
        phase3_start = time.perf_counter()
        stats.conditions_evaluated, callbacks_to_fire = self._phase3_condition_eval(
            updated_sensors
        )
        stats.phase3_condition_eval_ms = (time.perf_counter() - phase3_start) * 1000

        # Phase 4: Callback dispatch + safety monitoring
        stats.phase_order.append("callback_dispatch")
        phase4_start = time.perf_counter()
        dispatched, failures = await self._phase4_callback_dispatch(callbacks_to_fire)
        stats.callbacks_dispatched = dispatched
        stats.callback_failures = failures

        # Check safety monitors (part of phase 4)
        monitors_checked, violations, violation_events = self._check_safety_monitors()
        stats.safety_monitors_checked = monitors_checked
        stats.safety_violations = violations
        stats.safety_violation_events = violation_events

        stats.phase4_callback_dispatch_ms = (time.perf_counter() - phase4_start) * 1000

        # Total tick duration
        stats.tick_duration_ms = (time.perf_counter() - tick_start) * 1000

        # Record in profiler
        self.profiler.record_tick(stats)

        self._tick_count += 1

        # Call hook if registered
        if self._on_tick_end:
            self._on_tick_end(stats)

        return stats

    async def run(self, max_ticks: Optional[int] = None) -> None:
        """Run the tick loop.

        Args:
            max_ticks: Maximum number of ticks to run (None = infinite)
        """
        self._running = True
        self._tick_count = 0

        try:
            while self._running:
                if max_ticks is not None and self._tick_count >= max_ticks:
                    break

                tick_start = time.perf_counter()

                # Call hook if registered
                if self._on_tick_start:
                    self._on_tick_start(self._tick_count)

                # Execute the tick
                await self.run_single_tick()

                # Sleep to maintain tick rate
                elapsed = time.perf_counter() - tick_start
                sleep_time = self.tick_period_s - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.debug("Tick runner cancelled")
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the runner to stop."""
        self._running = False


def enable_profiling(runner: PhasedTickRunner) -> None:
    """Enable profiling on a PhasedTickRunner.

    Args:
        runner: The runner to enable profiling on
    """
    runner.profiler.enable()

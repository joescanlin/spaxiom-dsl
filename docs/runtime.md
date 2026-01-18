# Runtime and Tick Execution

Spaxiom provides a deterministic phased tick execution model that processes sensors, patterns, conditions, and callbacks in a predictable order. This page documents the `PhasedTickRunner` and related profiling tools.

## Overview

The runtime executes a 4-phase tick loop:

1. **Phase 1: Sensor Reads** - Read all sensors concurrently
2. **Phase 2: Pattern Updates** - Update patterns in dependency order
3. **Phase 3: Condition Evaluation** - Evaluate conditions (polling or event-driven)
4. **Phase 4: Callback Dispatch** - Execute triggered callbacks with isolation

## PhasedTickRunner

The `PhasedTickRunner` class implements the phased tick loop.

### Basic Usage

```python
import asyncio
from spaxiom import PhasedTickRunner, Sensor, Condition, on

# Setup sensors and conditions
sensor = Sensor("temp", "temperature", (0, 0, 0))
temp_high = Condition(lambda: sensor.read() > 30)

@on(temp_high)
def alert():
    print("Temperature is high!")

# Create and run the tick runner
async def main():
    runner = PhasedTickRunner(tick_rate_hz=10.0)
    await runner.run(max_ticks=100)

asyncio.run(main())
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tick_rate_hz` | Target tick rate in Hz | 10.0 |
| `history_length` | Maximum condition history entries | 1000 |

### Running a Single Tick

For testing or manual control, you can run individual ticks:

```python
async def run_one():
    runner = PhasedTickRunner()
    stats = await runner.run_single_tick()
    print(f"Tick {stats.tick_number} took {stats.tick_duration_ms:.2f}ms")
```

### Stopping the Runner

```python
runner.stop()  # Signal the runner to stop after current tick
```

## Registering Patterns

INTENT patterns are updated in Phase 2 in dependency order:

```python
from spaxiom import PhasedTickRunner, OccupancyField

runner = PhasedTickRunner()

# Create and register patterns
occupancy = OccupancyField(zones=["zone_a", "zone_b"])
runner.register_pattern(occupancy)

# Clear all patterns if needed
runner.clear_patterns()
```

Patterns are automatically sorted using topological sort based on their `depends_on()` method.

## Safety Monitors Integration

Safety monitors are checked at the end of each tick:

```python
from spaxiom import PhasedTickRunner
from spaxiom.safety import SafetyMonitor, verifiable, compare

# Create safety property
pressure_ok = verifiable(compare("pressure", "<", 150), name="pressure_limit")

def failsafe(violation):
    print(f"SAFETY VIOLATION: {violation.message}")

monitor = SafetyMonitor(
    name="pressure_safety",
    property=pressure_ok,
    on_violation=failsafe
)

runner = PhasedTickRunner()
runner.register_safety_monitor(monitor)
```

## Governance Integration

The runner supports governance hooks:

```python
from spaxiom import PhasedTickRunner
from spaxiom.governance import RetentionPolicy, ConsentManager, Authorizer, AuditLogger

runner = PhasedTickRunner()

# Set retention policy for history buffers
runner.set_retention_policy(RetentionPolicy(default_days=30))

# Set consent manager for data collection controls
runner.set_consent_manager(ConsentManager())

# Set authorizer for access control
runner.set_authorizer(Authorizer())

# Set audit logger for governance events
runner.set_audit_logger(AuditLogger())
```

## Tick Profiling

Enable profiling to collect performance statistics across ticks.

### Enabling Profiling

```python
from spaxiom import PhasedTickRunner, enable_profiling

runner = PhasedTickRunner()
enable_profiling(runner)  # Or: runner.profiler.enable()

# Run some ticks...
await runner.run(max_ticks=100)

# Get aggregated stats
stats = runner.profiler.get_stats()
print(f"Average tick: {stats['avg_tick_ms']:.2f}ms")
print(f"Phase 1 (sensors): {stats['phase1_sensor_read_avg_ms']:.2f}ms")
print(f"Phase 2 (patterns): {stats['phase2_pattern_update_avg_ms']:.2f}ms")
print(f"Phase 3 (conditions): {stats['phase3_condition_eval_avg_ms']:.2f}ms")
print(f"Phase 4 (callbacks): {stats['phase4_callback_dispatch_avg_ms']:.2f}ms")
```

### TickStats

Each tick produces a `TickStats` object with detailed instrumentation:

```python
@dataclass
class TickStats:
    tick_number: int
    tick_start_time: float
    tick_duration_ms: float
    
    # Phase timings
    phase1_sensor_read_ms: float
    phase2_pattern_update_ms: float
    phase3_condition_eval_ms: float
    phase4_callback_dispatch_ms: float
    
    # Counts
    sensors_read: int
    patterns_updated: int
    events_emitted: int
    conditions_evaluated: int
    callbacks_dispatched: int
    callback_failures: int
    
    # Safety monitoring
    safety_monitors_checked: int
    safety_violations: int
    safety_violation_events: List[Any]
    
    # Phase ordering proof
    phase_order: List[str]
    
    # Events emitted this tick
    pattern_events: List[Any]
```

### Getting the Last Tick

```python
last_tick = runner.profiler.get_last_tick()
if last_tick:
    print(f"Last tick: {last_tick.tick_number}")
    print(f"Callbacks fired: {last_tick.callbacks_dispatched}")
```

### Profiler Stats

The profiler provides aggregated statistics:

| Statistic | Description |
|-----------|-------------|
| `tick_count` | Total ticks recorded |
| `avg_tick_ms` | Average tick duration |
| `phase1_sensor_read_avg_ms` | Average sensor read phase time |
| `phase2_pattern_update_avg_ms` | Average pattern update phase time |
| `phase3_condition_eval_avg_ms` | Average condition eval phase time |
| `phase4_callback_dispatch_avg_ms` | Average callback dispatch phase time |
| `callback_failures` | Total callback failures |
| `sensors_read_total` | Total sensor reads |
| `conditions_evaluated_total` | Total condition evaluations |
| `callbacks_dispatched_total` | Total callbacks dispatched |

## Condition Evaluation Modes

Conditions can operate in different evaluation modes:

### Polling Mode (Default)

Conditions are evaluated every tick:

```python
from spaxiom import Condition

# Evaluated every tick
temp_high = Condition(lambda: sensor.read() > 30)
```

### Event-Driven Mode

Conditions are only evaluated when their dependencies change:

```python
# Set dependencies for event-driven evaluation
temp_high = Condition(lambda: sensor.read() > 30)
temp_high.dependencies = [sensor]  # Only evaluate when sensor changes
temp_high._effective_mode = "event-driven"
```

## Tick Callbacks

Register callbacks for tick lifecycle events:

```python
def on_tick_start(tick_number):
    print(f"Starting tick {tick_number}")

def on_tick_end(stats):
    print(f"Tick {stats.tick_number} completed in {stats.tick_duration_ms:.2f}ms")

runner._on_tick_start = on_tick_start
runner._on_tick_end = on_tick_end
```

## Example: Complete Setup

```python
import asyncio
from spaxiom import (
    PhasedTickRunner,
    Sensor,
    Condition,
    on,
    OccupancyField,
    enable_profiling,
)
from spaxiom.safety import SafetyMonitor, verifiable, compare
from spaxiom.governance import RetentionPolicy, AuditLogger

async def main():
    # Create sensors
    motion = Sensor("motion", "motion", (5, 5, 0))
    
    # Create condition
    motion_detected = Condition(lambda: motion.read() > 0.5)
    
    @on(motion_detected)
    def handle_motion():
        print("Motion detected!")
    
    # Create runner
    runner = PhasedTickRunner(tick_rate_hz=10.0)
    
    # Enable profiling
    enable_profiling(runner)
    
    # Register patterns
    occupancy = OccupancyField(zones=["lobby"])
    runner.register_pattern(occupancy)
    
    # Register safety monitor
    safe = verifiable(compare("motion", "<", 1.0), name="motion_limit")
    monitor = SafetyMonitor("motion_safety", safe)
    runner.register_safety_monitor(monitor)
    
    # Set governance
    runner.set_retention_policy(RetentionPolicy(default_days=7))
    runner.set_audit_logger(AuditLogger())
    
    # Run for 100 ticks
    await runner.run(max_ticks=100)
    
    # Print stats
    stats = runner.profiler.get_stats()
    print(f"\nProfile Summary:")
    print(f"  Ticks: {stats['tick_count']}")
    print(f"  Avg tick: {stats['avg_tick_ms']:.2f}ms")

asyncio.run(main())
```

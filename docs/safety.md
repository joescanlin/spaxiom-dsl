# Safety Verification

The Safety module provides runtime monitoring and formal verification support for Spaxiom applications. It enables you to define safety properties that must always hold, monitor them at runtime, and export them to UPPAAL for formal verification.

## Overview

The safety module consists of three main components:

1. **Verifiable Conditions (IR)** - A restricted subset of conditions that can be formally verified
2. **SafetyMonitor** - Runtime monitoring with violation callbacks
3. **UPPAAL Export** - Export to timed automata for formal verification

## Verifiable Conditions

Unlike regular Spaxiom conditions that can wrap arbitrary Python lambdas, verifiable conditions are built from a restricted set of IR (Intermediate Representation) nodes that can be exported to UPPAAL.

### Building Verifiable Conditions

```python
from spaxiom.safety import signal, const, compare, within, verifiable

# Create a condition: temperature < 100
temp_safe = verifiable(
    compare("temperature", "<", 100),
    name="temp_limit"
)

# Temporal condition: motion sustained for 5 seconds
motion_sustained = verifiable(
    within(compare("motion", ">", 0.5), 5.0),
    name="motion_5s"
)

# Combine conditions with boolean operators
combined = temp_safe & motion_sustained
negated = ~temp_safe
either = temp_safe | motion_sustained
```

### Available IR Nodes

| Node | Description | Example |
|------|-------------|---------|
| `signal(name)` | Reference to a sensor value | `signal("temperature")` |
| `const(value)` | Constant value | `const(100)` |
| `compare(left, op, right)` | Comparison | `compare("temp", "<", 100)` |
| `within(cond, seconds)` | Temporal constraint | `within(cond, 5.0)` |

### Evaluating Conditions

```python
# Provide a context with signal values
context = {"temperature": 85, "motion": 0.7}

# Evaluate
result = temp_safe.evaluate(context)  # True (85 < 100)
```

## SafetyMonitor

The `SafetyMonitor` class provides runtime monitoring of safety properties with automatic violation detection and callbacks.

### Basic Usage

```python
from spaxiom.safety import SafetyMonitor, verifiable, compare

# Define a safety property (must always be true)
arm_safe = verifiable(
    compare("arm_speed", "<", 100),
    name="arm_speed_limit"
)

# Create violation handler
def emergency_stop(violation):
    print(f"SAFETY VIOLATION: {violation.message}")
    robot.stop()

# Create monitor
monitor = SafetyMonitor(
    name="arm_safety",
    property=arm_safe,
    on_violation=emergency_stop
)

# Check each tick
while running:
    context = {"arm_speed": read_arm_speed()}
    is_safe = monitor.check(context)
```

### Violation Records

When a violation occurs, a `SafetyViolation` record is created:

```python
@dataclass
class SafetyViolation:
    timestamp: float      # When violation occurred
    monitor_name: str     # Name of the monitor
    property_name: str    # Name of the violated property
    state: str           # "violated"
    previous_state: str  # "ok"
    context: dict        # Signal values at violation time
    message: str         # Human-readable message
```

### Accessing Audit Records

```python
# Get all recorded violations
violations = monitor.violations

# Get as serializable dicts (for JSON/logging)
audit_records = monitor.get_audit_records()
```

## UPPAAL Export

Verifiable conditions can be exported to UPPAAL XML format for formal verification using timed automata.

### Exporting a Monitor

```python
from spaxiom.safety import SafetyMonitor, verifiable, compare

# Create verifiable condition
temp_safe = verifiable(compare("temperature", "<", 100), name="temp_limit")

# Create monitor
monitor = SafetyMonitor(name="temp_monitor", property=temp_safe)

# Export to UPPAAL
automaton = monitor.compile_to_uppaal()
automaton.save("temp_monitor.xml")
```

### Exporting Multiple Conditions

```python
from spaxiom.safety.verify import compile_to_uppaal

conditions = [temp_safe, motion_safe, door_safe]
automaton = compile_to_uppaal(conditions, name="SafetyMonitor")
automaton.save("safety_monitor.xml")
```

### UPPAAL Automaton Structure

The exported automaton includes:

- **Clocks** - For temporal constraints (within operators)
- **Variables** - Boolean variables for each signal
- **Locations** - "safe" state and violation states for each property
- **Transitions** - Guards based on condition expressions

## Integration with Runtime

Safety monitors integrate with the Spaxiom runtime tick loop:

```python
from spaxiom import PhasedTickRunner
from spaxiom.safety import SafetyMonitor, verifiable, compare

# Create safety property
pressure_ok = verifiable(compare("pressure", "<", 150), name="pressure_limit")

# Create monitor with failsafe
def failsafe(violation):
    shutdown_system()

monitor = SafetyMonitor(
    name="pressure_safety",
    property=pressure_ok,
    on_violation=failsafe
)

# In your tick callback
def on_tick(context):
    monitor.check(context)
```

## Limitations

The verifiable subset has intentional limitations to enable formal verification:

- No arbitrary Python lambdas (use IR nodes instead)
- Only boolean operations, comparisons, and temporal operators
- All signal names must be known at definition time
- Clock values for temporal operators must be provided in context

For conditions that require full Python expressiveness, use regular `Condition` objects, but note these cannot be exported to UPPAAL.

# Spaxiom-DSL

<div align="center">
    <pre>
                ███████╗██████╗  █████╗ ██╗  ██╗██╗ ██████╗ ███╗   ███╗
                ██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝██║██╔═══██╗████╗ ████║
                ███████╗██████╔╝███████║ ╚███╔╝ ██║██║   ██║██╔████╔██║
                ╚════██║██╔═══╝ ██╔══██║ ██╔██╗ ██║██║   ██║██║╚██╔╝██║
                ███████║██║     ██║  ██║██╔╝ ██╗██║╚██████╔╝██║ ╚═╝ ██║
                ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
    </pre>
</div>

<p align="center">
  <a href="https://pypi.org/project/spaxiom/"><img src="https://badge.fury.io/py/spaxiom.svg" alt="PyPI version" /></a>
  <a href="https://github.com/joescanlin/spaxiom-dsl/actions/workflows/ci.yml"><img src="https://github.com/joescanlin/spaxiom-dsl/actions/workflows/ci.yml/badge.svg" alt="Spaxiom CI" /></a>
  <a href="https://github.com/joescanlin/spaxiom-dsl"><img src="https://img.shields.io/badge/Project%20Status-Beta-orange.svg" alt="Project Status: Beta" /></a>
</p>

An embedded domain-specific language for spatial sensor fusion, temporal reasoning, and real-time event detection.

## What is Spaxiom/INTENT?

Spaxiom is a Domain-Specific Language (DSL) for building intelligent spatial-temporal systems. It provides:

- **Spatial Data**: Zones, sensors, and physical spaces
- **Temporal Logic**: Time-based conditions and historical analysis
- **Event Processing**: Triggering actions based on complex conditions
- **INTENT Patterns**: High-level behavioral patterns (OccupancyField, QueueFlow, ADLTracker, FmSteward)
- **Safety Verification**: Verifiable subset with UPPAAL export for formal verification
- **Governance**: Retention policies, consent management, authorization, and audit logging

### Implementation Status

This implementation aims for parity with the INTENT/Spaxiom paper specification. Current status:

| Category | Status | Notes |
|----------|--------|-------|
| Runtime (Phased Tick) | Implemented | 4-phase deterministic execution |
| Conditions (Dependency Tracking) | Implemented | Polling, event-driven, auto modes |
| INTENT Patterns | Implemented | OccupancyField, QueueFlow, ADLTracker, FmSteward |
| Safety Verification | Implemented | SafetyMonitor, UPPAAL XML export |
| Governance | Implemented | Retention, consent, RBAC/ABAC, audit |

For detailed status, see [docs/paper_parity_checklist.md](docs/paper_parity_checklist.md).

## Installation

```bash
# Clone and install in development mode
git clone https://github.com/joescanlin/spaxiom-dsl.git
cd spaxiom-dsl
pip install -e .

# Or install from PyPI
pip install spaxiom
```

### Optional Dependencies

```bash
# For MQTT sensor support
pip install paho-mqtt>=2.0

# For GPIO sensor support (Raspberry Pi)
pip install gpiozero>=2.0
```

## Quick Start

### Basic Spatial & Temporal Logic

```python
from spaxiom import Sensor, Zone, Condition, on, within

# Define a zone and sensor
office_zone = Zone(0, 0, 10, 10)
motion_sensor = Sensor("motion1", "motion", (5, 5, 0))

# Create condition based on sensor data
motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

# Make it temporal - must be true for 5 seconds
sustained_motion = within(5.0, motion_detected)

# Register an event handler
@on(sustained_motion)
def alert_sustained_motion():
    print("Motion has been detected for 5 seconds!")
```

### Running Examples

```bash
# Run a minimal runtime example
python examples/paper/runtime_minimal.py

# Run the phased tick demo
python examples/paper/runtime_tick_phases.py

# Run INTENT pattern example
python examples/paper/intent_occupancyfield.py

# Run safety verification example
python examples/paper/safety_export_uppaal.py

# Run governance demo
python examples/paper/governance_demo.py
```

## Developer Commands

### Formatting & Linting

```bash
# Check formatting (runs in CI)
black --check .

# Auto-format code
black .

# Lint with ruff (runs in CI)
ruff check .

# Auto-fix lint issues
ruff check --fix .
```

### Running Tests

```bash
# Run full test suite (runs in CI)
pytest

# Run with verbose output
pytest -v

# Run paper parity tests only
pytest tests/paper_parity/ -v

# Run specific test file
pytest tests/paper_parity/test_governance_audit.py -v
```

### Coverage

```bash
# Run tests with coverage (runs in CI)
coverage run -m pytest

# Generate coverage report
coverage report -m

# Generate HTML coverage report
coverage html
# Open coverage_html_report/index.html

# CI enforces minimum 74% coverage (configured in pyproject.toml)
```

### CI Expectations

The CI pipeline runs on Python 3.10 and executes:
1. `ruff check .` - Linting
2. `black --check .` - Format checking
3. `coverage run -m pytest` - Tests with coverage
4. Coverage threshold check (74% minimum)

Optional dependencies (`paho-mqtt`) are installed in CI. Tests that require hardware (GPIO) are skipped gracefully.

## Key Examples

| Example | Description |
|---------|-------------|
| `examples/paper/runtime_tick_phases.py` | Demonstrates 4-phase tick execution |
| `examples/paper/conditions_event_driven.py` | Event-driven vs polling conditions |
| `examples/paper/intent_occupancyfield.py` | OccupancyField pattern usage |
| `examples/paper/intent_all_patterns.py` | All INTENT patterns together |
| `examples/paper/safety_export_uppaal.py` | SafetyMonitor and UPPAAL export |
| `examples/paper/governance_demo.py` | Retention, consent, auth, audit |

## Documentation

### Online Documentation

Full documentation: https://joescanlin.github.io/spaxiom-dsl/

### Local Documentation

```bash
# Install MkDocs
pip install mkdocs-material pymdown-extensions

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

Key documentation files:
- [Paper Parity Checklist](docs/paper_parity_checklist.md) - Implementation status vs paper
- [Temporal and Entity Operations](docs/temporal_and_entities.md)
- [Quick Start Guide](docs/quickstart.md)
- [CLI Usage](docs/cli_usage.md)

## Architecture

### Runtime (Phased Tick)

The runtime executes a deterministic 4-phase tick loop:

1. **Phase 1 - Sensor Reads**: Concurrent sensor polling via `asyncio.gather()`
2. **Phase 2 - Pattern Updates**: Dependency-ordered INTENT pattern updates
3. **Phase 3 - Condition Evaluation**: Evaluate conditions (polling or event-driven)
4. **Phase 4 - Callback Dispatch**: Isolated callback execution with exception handling

### INTENT Patterns

High-level behavioral abstractions:
- `OccupancyField`: Zone occupancy tracking
- `QueueFlow`: Queue/flow monitoring
- `ADLTracker`: Activity of Daily Living tracking
- `FmSteward`: Facilities management patterns

### Safety Verification

- `VerifiableCondition`: Restricted condition subset for formal verification
- `SafetyMonitor`: Runtime monitoring with failsafe callbacks
- UPPAAL XML export for model checking

### Governance

- `RetentionPolicy`: Bounded storage with TTL-based cleanup
- `ConsentManager`: Zone/entity opt-out management
- `Authorizer`: Combined RBAC + ABAC access control
- `AuditLogger`: Tamper-evident append-only logging with HMAC signing

## License

MIT

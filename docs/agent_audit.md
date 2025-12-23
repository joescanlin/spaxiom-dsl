# Spaxiom/INTENT Codebase Audit

**Generated:** 2024-12-23
**Purpose:** Baseline inventory of what exists today (Step 0 of AGENT_EXECUTION_PLAN.md)

---

## 1. Repository Structure Summary

```
spaxiom-dsl/
├── spaxiom/                    # Core library
│   ├── __init__.py             # Public API exports
│   ├── core.py                 # Sensor, SensorRegistry base classes
│   ├── sensor.py               # RandomSensor, TogglingSensor implementations
│   ├── zone.py                 # Zone, Point, distance()
│   ├── condition.py            # Condition class (basic version)
│   ├── logic.py                # Condition class (extended with timestamps), exists(), transitioned_to_true()
│   ├── events.py               # @on decorator, EVENT_HANDLERS, process_events()
│   ├── temporal.py             # TemporalWindow, SequencePattern, within(), sequence()
│   ├── runtime.py              # start_runtime(), start_blocking(), shutdown()
│   ├── plugins.py              # register_plugin(), discover_and_load_plugins()
│   ├── cli.py                  # CLI entrypoints (run, new)
│   ├── config.py               # YAML config loading
│   ├── entities.py             # Entity, EntitySet
│   ├── fusion.py               # WeightedFusion
│   ├── geo.py                  # intersection(), union()
│   ├── model.py                # StubModel, OnnxModel
│   ├── registry.py             # Additional registry functionality
│   ├── summarize.py            # RollingSummary
│   ├── units.py                # Quantity, ureg (pint integration)
│   ├── adaptors/               # Sensor adapters
│   │   ├── file_sensor.py      # FileSensor
│   │   ├── mqtt_sensor.py      # MQTTSensor (optional)
│   │   └── gpio_sensor.py      # GPIODigitalSensor (Linux only)
│   ├── actuators/              # Actuator implementations
│   │   └── gpio_output.py      # GPIOOutput (Linux only)
│   ├── intent/                 # INTENT patterns
│   │   ├── __init__.py
│   │   ├── occupancy_field.py  # OccupancyField
│   │   ├── queue_flow.py       # QueueFlow
│   │   ├── adl_tracker.py      # ADLTracker
│   │   └── fm_steward.py       # FmSteward
│   └── sim/                    # Simulation utilities
│       └── vec_sim.py          # SimVector
├── examples/                   # Example scripts
├── tests/                      # Test suite
├── docs/                       # Documentation
├── bench/                      # Benchmarks
└── pyproject.toml              # Project configuration
```

---

## 2. Runtime and Entrypoints

### 2.1 Async Runtime

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `start_runtime()` | `spaxiom/runtime.py:232` | Async entrypoint; spawns sensor polling tasks and condition evaluation |
| `_poll_sensor()` | `spaxiom/runtime.py:65` | Async sensor polling loop per sensor |
| `_evaluate_conditions()` | `spaxiom/runtime.py:102` | Continuous condition evaluation with rising-edge detection |
| `shutdown()` | `spaxiom/runtime.py:178` | Graceful async shutdown handler |

### 2.2 Blocking Runtime

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `start_blocking()` | `spaxiom/runtime.py:346` | Blocking wrapper; calls `asyncio.run(start_runtime())` |

### 2.3 Tick Loop Architecture

The current runtime does **NOT** implement a deterministic phased tick. Instead:

- Each sensor runs its own independent `asyncio` task (`_poll_sensor`)
- Condition evaluation runs in a separate async task (`_evaluate_conditions`) at 10ms intervals
- Callbacks are dispatched inline within the condition evaluation loop via `asyncio.create_task(asyncio.to_thread(callback))`

**Paper requirement (Section 2.5):** Deterministic 4-phase tick:
1. Sensor reads (concurrent)
2. Pattern updates (dependency-ordered)
3. Condition evaluation
4. Callback dispatch (concurrent, isolated)

**Current status:** PARTIAL - lacks phased tick ordering and pattern integration.

---

## 3. Sensor, Zone, Condition, and Decorators

### 3.1 Sensor Classes

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `Sensor` (base) | `spaxiom/core.py:14` | Base dataclass with `read()`, `_read_raw()`, `get_last_value()`, `fuse_with()` |
| `SensorRegistry` | `spaxiom/core.py:162` | Singleton registry with `add()`, `get()`, `list_all()`, `list_public()`, `list_private()` |
| `RandomSensor` | `spaxiom/sensor.py:12` | Random value generator sensor |
| `TogglingSensor` | `spaxiom/sensor.py:53` | Periodic toggle sensor |
| `FileSensor` | `spaxiom/adaptors/file_sensor.py` | File-based sensor |
| `MQTTSensor` | `spaxiom/adaptors/mqtt_sensor.py` | MQTT sensor (optional dependency) |
| `GPIODigitalSensor` | `spaxiom/adaptors/gpio_sensor.py` | GPIO sensor (Linux only) |

### 3.2 Zone Classes

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `Zone` | `spaxiom/zone.py:27` | Rectangular zone with `contains()` method |
| `Point` | `spaxiom/zone.py:10` | 2D point dataclass |
| `distance()` | `spaxiom/zone.py:72` | Euclidean distance function |

### 3.3 Condition Classes

Two implementations exist:

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `Condition` (basic) | `spaxiom/condition.py:8` | Simple wrapper with `&`, `|`, `~` operators |
| `Condition` (extended) | `spaxiom/logic.py:15` | Adds `last_value`, `last_changed`, `evaluate()`, `transitioned_to_true()`, `summary()` |

**Note:** The extended version in `logic.py` is the one exported via `__init__.py`.

### 3.4 Decorators

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `@on(condition)` | `spaxiom/events.py:19` | Registers callback to fire on condition rising edge |
| `EVENT_HANDLERS` | `spaxiom/events.py:14` | Global list of `(Condition, Callable)` tuples |
| `process_events()` | `spaxiom/events.py:52` | Manual event processing (not used by runtime) |
| `run_event_loop()` | `spaxiom/events.py:66` | Simple blocking event loop (legacy) |

---

## 4. Temporal Operations

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `within(seconds, cond)` | `spaxiom/temporal.py:183` | True when condition continuously true for duration |
| `sequence(*conds, within_s)` | `spaxiom/temporal.py:215` | True when conditions occur in sequence within window |
| `TemporalWindow` | `spaxiom/temporal.py:11` | Internal class for `within()` |
| `SequencePattern` | `spaxiom/temporal.py:80` | Internal class for `sequence()` |
| `exists(entity_set, predicate)` | `spaxiom/logic.py:227` | True when any entity satisfies predicate |
| `transitioned_to_true(cond)` | `spaxiom/logic.py:213` | Helper for rising-edge detection |

---

## 5. Plugin System

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `@register_plugin` | `spaxiom/plugins.py:23` | Decorator to register plugin functions |
| `PLUGINS` | `spaxiom/plugins.py:17` | Global list of registered plugin callables |
| `discover_and_load_plugins()` | `spaxiom/plugins.py:53` | Loads from `spaxiom_site_plugins` namespace |
| `initialize_plugins()` | `spaxiom/plugins.py:86` | Calls all registered plugin functions |
| `reset_plugins()` | `spaxiom/plugins.py:107` | Clears plugin registry (for testing) |

---

## 6. CLI Entrypoints and Commands

| Command | File Path | Description |
|---------|-----------|-------------|
| `spax-run` / `cli()` | `spaxiom/cli.py:19` | Main CLI group (Click) |
| `spax-run run <script>` | `spaxiom/cli.py:25` | Run a Spaxiom script with options `--poll-ms`, `--history-length`, `--config`, `--verbose` |
| `spax-run new <name>` | `spaxiom/cli.py:146` | Scaffold a new Spaxiom script with `--output-dir`, `--sensors`, `--zones`, `--privacy` |

**CLI entrypoint defined in `pyproject.toml`:**
```toml
[project.scripts]
spax-run = "spaxiom.cli:main"
```

---

## 7. INTENT Patterns

| Symbol | File Path | Description |
|--------|-----------|-------------|
| `OccupancyField` | `spaxiom/intent/occupancy_field.py:14` | 2D floor grid occupancy wrapper with `percent()`, `percent_above()`, `hotspots()` |
| `QueueFlow` | `spaxiom/intent/queue_flow.py:11` | Queue length/wait time estimator with `length()`, `arrival_rate()`, `service_rate()`, `wait_time()` |
| `ADLTracker` | `spaxiom/intent/adl_tracker.py:7` | Activities of Daily Living tracker with event callbacks |
| `FmSteward` | `spaxiom/intent/fm_steward.py:6` | Facilities management service trigger with `needs_service()`, `snapshot()` |

**Paper requirement:** Patterns should have `update(dt, context)`, `emit()`, `depends_on()` interface.
**Current status:** MISSING - Current patterns are passive wrappers, not runtime-integrated components.

---

## 8. Examples

| File | Description |
|------|-------------|
| `examples/sequence_demo.py` | Demonstrates sequence pattern detection |
| `examples/occupancy_demo.py` | OccupancyField usage |
| `examples/smart_building.py` | Multi-sensor smart building example |
| `examples/privacy_demo.py` | Privacy settings demonstration |
| `examples/privacy_runtime_demo.py` | Privacy in runtime context |
| `examples/file_sensor_demo.py` | FileSensor usage |
| `examples/file_feed_demo.py` | File-based data feed |
| `examples/plugin_demo.py` | Plugin system demonstration |
| `examples/custom_plugin_demo.py` | Custom plugin creation |
| `examples/config_demo.py` | YAML configuration |
| `examples/config_cli_demo.py` | CLI with config |
| `examples/co2_monitor.py` | CO2 monitoring example |
| `examples/co2_plugin.py` | CO2 plugin |
| `examples/units_demo.py` | Pint units integration |
| `examples/sim_vector_demo.py` | SimVector usage |
| `examples/gpio_sensor_demo.py` | GPIO sensor (Pi) |
| `examples/gpio_output_demo.py` | GPIO output (Pi) |
| `examples/geo_demo.py` | Geometry operations |
| `examples/summarize_demo.py` | RollingSummary |
| `examples/ai_stub_demo.py` | AI model stub |
| `examples/onnx_person_demo.py` | ONNX model usage |
| `examples/pi_door_demo.py` | Raspberry Pi door sensor |

**Paper examples folder:** NOT FOUND - `examples/paper/` does not exist.

---

## 9. Tests

| File | Description |
|------|-------------|
| `tests/test_runtime.py` | Runtime startup, shutdown, sensor polling |
| `tests/test_temporal.py` | `within()`, `sequence()`, temporal windows |
| `tests/test_sequence.py` | Sequence pattern tests |
| `tests/test_logic.py` | Condition operators, `transitioned_to_true()` |
| `tests/test_entities.py` | Entity, EntitySet |
| `tests/test_entity_logic.py` | `exists()` and entity predicates |
| `tests/test_zone.py` | Zone containment |
| `tests/test_geo.py` | Geometry operations |
| `tests/test_geo_union.py` | Union operations |
| `tests/test_fusion.py` | WeightedFusion |
| `tests/test_sensor_fusion_mixin.py` | Sensor fusion mixin |
| `tests/test_config.py` | YAML configuration |
| `tests/test_cli.py` | CLI commands |
| `tests/test_cli_scaffold.py` | CLI scaffolding |
| `tests/test_plugins.py` | Plugin system |
| `tests/test_shutdown.py` | Graceful shutdown |
| `tests/test_scheduler.py` | Scheduler tests |
| `tests/test_file_sensor.py` | FileSensor |
| `tests/test_mqtt_sensor.py` | MQTTSensor |
| `tests/test_gpio_sensor.py` | GPIODigitalSensor |
| `tests/test_gpio_output.py` | GPIOOutput |
| `tests/test_model.py` | StubModel |
| `tests/test_onnx_model.py` | OnnxModel |
| `tests/test_units.py` | Pint units |
| `tests/test_summarize.py` | RollingSummary |
| `tests/test_registry.py` | SensorRegistry |
| `tests/test_sim_vector.py` | SimVector |
| `tests/test_privacy.py` | Privacy features |

**Paper parity tests folder:** NOT FOUND - `tests/paper_parity/` does not exist.

---

## 10. Setup and Run Commands

### Install Dependencies
```bash
cd spaxiom-dsl
pip install -e .
# Or with Poetry:
poetry install
```

### Run Tests
```bash
pytest tests/
# With coverage:
pytest tests/ --cov=spaxiom --cov-report=term-missing
```

### Run Examples
```bash
# Direct execution:
python examples/sequence_demo.py

# Via CLI:
spax-run run examples/sequence_demo.py --poll-ms 50
```

### Create New Script
```bash
spax-run new my_app --sensors 3 --zones 2
```

---

## 11. Summary of Gaps (Paper vs Implementation)

### MISSING Components

1. **Phased tick runtime** - Paper specifies 4-phase deterministic tick; current implementation uses independent async tasks
2. **Pattern base class** - Paper specifies `Pattern.update(dt, context)`, `emit()`, `depends_on()`; NOT FOUND
3. **SafetyMonitor** - Paper specifies runtime safety monitor with failsafe callbacks; NOT FOUND
4. **UPPAAL export** - Paper specifies compilation to UPPAAL timed automata; NOT FOUND
5. **Verifiable subset IR** - Paper specifies internal representation for verifiable conditions; NOT FOUND
6. **Governance primitives**:
   - `RetentionPolicy` - NOT FOUND
   - `ConsentManager` - NOT FOUND
   - `RBAC`/`ABAC` authorizer - NOT FOUND
   - `AuditLogger` - NOT FOUND
7. **Event-driven condition evaluation mode** - Paper specifies `mode="event-driven"`; NOT FOUND
8. **Dependency tracking** - Paper specifies conditions track dependencies on sensors/patterns; PARTIAL (temporal patterns track internal state only)
9. **Per-tick instrumentation/profiler** - Paper specifies `enable_profiling()`, timing stats; NOT FOUND
10. **Paper examples folder** - `examples/paper/` NOT FOUND
11. **Paper parity tests folder** - `tests/paper_parity/` NOT FOUND

### PARTIAL Components

1. **INTENT patterns** - Exist but lack `update()/emit()/depends_on()` interface
2. **Condition evaluation** - Works but no event-driven mode or dependency tracking
3. **Runtime** - Works but not deterministic phased tick
4. **Privacy** - Basic public/private sensor flag exists; no zone-based consent

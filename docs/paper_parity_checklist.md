# Paper Parity Checklist

**Reference:** `docs/paper/intent_spaxiom_paper.html`
**Generated:** 2024-12-23

This checklist tracks implementation parity between the Spaxiom codebase and the paper specification.

---

## 1. Runtime

> **Runtime Architecture Note:**
>
> There are currently two runtime implementations:
> - **Primary entrypoints (legacy):** `spaxiom/runtime.py` provides `start_runtime()` and `start_blocking()`. These are used by the CLI and existing examples.
> - **New phased tick runner:** `spaxiom/tick.py` provides `PhasedTickRunner` with deterministic 4-phase execution per the paper specification.
>
> **Planned delegation:** After Step 3 (conditions) and Step 4 (patterns), `start_runtime()` and `start_blocking()` will delegate to `PhasedTickRunner.run()` internally, preserving backwards compatibility while using the new phased tick loop.

### 1.1 Phased Tick Execution

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Fixed tick rate (configurable Hz) | IMPLEMENTED | `spaxiom/tick.py:157` `PhasedTickRunner(tick_rate_hz=)` | Configurable Hz with tick_period_s property |
| Phase 1: Concurrent sensor reads | IMPLEMENTED | `spaxiom/tick.py:213` `_phase1_sensor_reads()` | Uses `asyncio.gather()` for concurrency |
| Phase 2: Pattern updates (dependency-ordered) | PARTIAL | `spaxiom/tick.py:234` `_phase2_pattern_updates()` | Updates in registration order; dependency sorting not yet implemented |
| Phase 3: Condition evaluation | IMPLEMENTED | `spaxiom/tick.py:252` `_phase3_condition_eval()` | Polling mode, evaluates all conditions |
| Phase 4: Callback dispatch (concurrent, isolated) | IMPLEMENTED | `spaxiom/tick.py:296` `_phase4_callback_dispatch()` | Isolated execution, failures logged but don't propagate |
| Deterministic ordering guarantee | IMPLEMENTED | `spaxiom/tick.py:318` `run_single_tick()` | 4 phases always execute in same order |

**Acceptance Criteria:**
- [x] Single tick loop with 4 explicit phases
- [x] Sensor reads batched with `asyncio.gather()`
- [ ] Patterns updated in topological order based on `depends_on()`
- [x] Conditions evaluated after pattern updates complete
- [x] Callbacks dispatched after all conditions evaluated

**Proving Test:** `tests/paper_parity/test_runtime_tick_ordering.py` (5 passing, 3 skipped)
**Proving Example:** `examples/paper/runtime_tick_phases.py`

---

### 1.2 Async and Blocking Entrypoints

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Async entrypoint | IMPLEMENTED | `spaxiom/runtime.py:232` `start_runtime()` | Works with `asyncio.run()` |
| Blocking wrapper | IMPLEMENTED | `spaxiom/runtime.py:346` `start_blocking()` | Wraps async with `asyncio.run()` |
| Graceful shutdown | IMPLEMENTED | `spaxiom/runtime.py:178` `shutdown()` | Handles SIGINT/SIGTERM |

**Acceptance Criteria:**
- [x] `start_runtime()` is async and awaitable
- [x] `start_blocking()` blocks until interrupted
- [x] Signal handlers cancel tasks gracefully

**Proving Test:** `tests/test_runtime.py`, `tests/test_shutdown.py`
**Proving Example:** Various existing examples

---

### 1.3 Per-Tick Instrumentation

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `enable_profiling(runtime)` | IMPLEMENTED | `spaxiom/tick.py:385` `enable_profiling()` | Enables profiler on PhasedTickRunner |
| Phase timing per tick | IMPLEMENTED | `spaxiom/tick.py:27` `TickStats` dataclass | Records ms for each phase |
| Sensor read latency stats | PARTIAL | `spaxiom/tick.py:56` `TickProfiler.get_stats()` | Averages collected, percentiles not yet |
| Callback failure counts | IMPLEMENTED | `spaxiom/tick.py:56` `TickProfiler` | Tracks `callback_failures` total |
| `runtime.profiler.get_stats()` | IMPLEMENTED | `spaxiom/tick.py:74` `TickProfiler.get_stats()` | Returns dict with all stats |

**Acceptance Criteria:**
- [x] `enable_profiling()` function exists
- [x] `get_stats()` returns dict with `avg_tick_ms`, `callback_failures`
- [ ] `get_stats()` returns `sensor_read_p99_ms` (percentiles not yet implemented)
- [ ] Profiling overhead < 1% (not yet measured)

**Proving Test:** `tests/paper_parity/test_runtime_instrumentation.py` (4 passing, 3 skipped)
**Proving Example:** `examples/paper/runtime_profiling.py`

---

## 2. Conditions

### 2.1 Condition Class

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Boolean function wrapper | IMPLEMENTED | `spaxiom/logic.py:15` `Condition` | Wraps callable |
| `&` (AND) operator | IMPLEMENTED | `spaxiom/logic.py:157` `__and__()` | Short-circuit |
| `\|` (OR) operator | IMPLEMENTED | `spaxiom/logic.py:176` `__or__()` | Short-circuit |
| `~` (NOT) operator | IMPLEMENTED | `spaxiom/logic.py:195` `__invert__()` | Works |
| `last_value` tracking | IMPLEMENTED | `spaxiom/logic.py:39` | Stored on instance |
| `last_changed` timestamp | IMPLEMENTED | `spaxiom/logic.py:40` | Updated on value change |
| `transitioned_to_true()` | IMPLEMENTED | `spaxiom/logic.py:138` | Rising edge detection |

**Acceptance Criteria:**
- [x] Conditions combine with `&`, `|`, `~`
- [x] Rising edge detection works

**Proving Test:** `tests/test_logic.py`
**Proving Example:** Multiple existing examples

---

### 2.2 Evaluation Modes

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Polling mode (default) | IMPLEMENTED | `spaxiom/runtime.py:102` | All conditions evaluated every tick |
| Event-driven mode | MISSING | - | No `mode="event-driven"` parameter |
| Auto mode selection | MISSING | - | No automatic mode switching |
| `Condition(..., mode="event-driven")` | MISSING | - | Not supported |

**Acceptance Criteria:**
- [ ] `Condition` accepts `mode` parameter
- [ ] Event-driven mode only evaluates on dependency changes
- [ ] Auto mode selects based on dependency complexity

**Proving Test:** `tests/paper_parity/test_event_driven_condition_selection.py`
**Proving Example:** `examples/paper/conditions_event_driven.py`

---

### 2.3 Dependency Tracking

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Conditions track sensor dependencies | MISSING | - | No dependency graph |
| Conditions track pattern dependencies | MISSING | - | No pattern integration |
| Conditions track temporal buffer dependencies | PARTIAL | `spaxiom/temporal.py` | Internal to temporal operators |
| Runtime invalidates affected conditions | MISSING | - | All conditions evaluated always |

**Acceptance Criteria:**
- [ ] `Condition.dependencies` returns set of sensors/patterns
- [ ] Runtime only evaluates conditions when dependencies change
- [ ] Unrelated conditions not evaluated (testable)

**Proving Test:** `tests/paper_parity/test_condition_dependency_tracking.py`
**Proving Example:** `examples/paper/conditions_dependencies.py`

---

## 3. INTENT Patterns

### 3.1 Pattern Base Class

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `Pattern` base class | MISSING | - | No base class |
| `update(dt, context)` method | MISSING | - | Patterns are passive |
| `emit()` method returning typed events | MISSING | - | No event emission |
| `depends_on()` method | MISSING | - | No dependency declaration |
| Stable event serialization (`to_dict()`) | MISSING | - | No event objects |

**Acceptance Criteria:**
- [ ] `Pattern` base class with abstract methods
- [ ] `update()` called by runtime each tick with `dt` and context
- [ ] `emit()` returns list of typed event objects
- [ ] `depends_on()` returns list of sensors/patterns
- [ ] Events have `to_dict()` for JSON serialization

**Proving Test:** `tests/paper_parity/test_intent_pattern_emits_event.py`
**Proving Example:** `examples/paper/intent_occupancyfield.py`

---

### 3.2 Implemented Patterns

| Pattern | Status | Code Pointer | Notes |
|---------|--------|--------------|-------|
| `OccupancyField` | PARTIAL | `spaxiom/intent/occupancy_field.py:14` | Passive wrapper, no `update()/emit()` |
| `QueueFlow` | PARTIAL | `spaxiom/intent/queue_flow.py:11` | Passive wrapper, no `update()/emit()` |
| `ADLTracker` | PARTIAL | `spaxiom/intent/adl_tracker.py:7` | Has `mark_*()` methods, no runtime integration |
| `FmSteward` | PARTIAL | `spaxiom/intent/fm_steward.py:6` | Passive `needs_service()` check |

**Acceptance Criteria:**
- [ ] All patterns inherit from `Pattern` base class
- [ ] All patterns implement `update(dt, context)`, `emit()`, `depends_on()`
- [ ] Patterns integrated into runtime tick loop

**Proving Test:** `tests/paper_parity/test_intent_patterns_interface.py`
**Proving Example:** `examples/paper/intent_all_patterns.py`

---

## 4. Safety Verification

### 4.1 Verifiable Subset

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Define verifiable subset of DSL | MISSING | - | No formal subset definition |
| Internal IR for verifiable conditions | MISSING | - | No IR representation |
| Restricted operators (no Python lambdas) | MISSING | - | Arbitrary lambdas allowed |
| Bounded iteration only | MISSING | - | No enforcement |

**Acceptance Criteria:**
- [ ] `SafeCondition` class or decorator for verifiable subset
- [ ] IR representation for conditions
- [ ] Validation that condition is in verifiable subset

**Proving Test:** `tests/paper_parity/test_verifiable_subset.py`
**Proving Example:** `examples/paper/safety_verifiable_subset.py`

---

### 4.2 UPPAAL Export

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `verify.compile_to_uppaal()` | MISSING | - | No export module |
| Timed automaton generation | MISSING | - | No automaton model |
| `.xml` file output | MISSING | - | No XML generation |
| Clock/timing modeling | MISSING | - | No timing model |

**Acceptance Criteria:**
- [ ] `from spaxiom.safety import verify` works
- [ ] `compile_to_uppaal(conditions, zones)` returns automaton object
- [ ] `automaton.save("file.xml")` produces valid UPPAAL XML
- [ ] XML parseable by UPPAAL tool

**Proving Test:** `tests/paper_parity/test_safety_export_uppaal.py`
**Proving Example:** `examples/paper/safety_export_uppaal.py`

---

### 4.3 SafetyMonitor

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `SafetyMonitor` class | MISSING | - | Not implemented |
| `property` parameter (safety condition) | MISSING | - | - |
| `on_violation` callback | MISSING | - | - |
| `compile_to_uppaal()` method | MISSING | - | - |
| Structured audit records | MISSING | - | - |
| Runtime monitoring loop | MISSING | - | - |

**Acceptance Criteria:**
- [ ] `SafetyMonitor(name, property, on_violation)` constructor
- [ ] Monitor integrated into runtime
- [ ] Violation triggers callback and logs audit event
- [ ] Audit events have structured schema

**Proving Test:** `tests/paper_parity/test_safety_monitor.py`
**Proving Example:** `examples/paper/safety_monitor_demo.py`

---

## 5. Governance

### 5.1 Retention Policy

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `RetentionPolicy` class | MISSING | - | Not implemented |
| `default_days` parameter | MISSING | - | - |
| `raw_events_days` parameter | MISSING | - | - |
| `exceptions` list for compliance events | MISSING | - | - |
| `runtime.set_retention_policy()` | MISSING | - | - |
| Automatic event purging | MISSING | - | - |

**Acceptance Criteria:**
- [ ] `from spaxiom.governance import RetentionPolicy`
- [ ] Policy enforced by history buffers
- [ ] Events older than policy are automatically purged
- [ ] Exception events retained longer

**Proving Test:** `tests/paper_parity/test_governance_retention.py`
**Proving Example:** `examples/paper/governance_retention.py`

---

### 5.2 Consent Manager

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `ConsentManager` class | MISSING | - | Not implemented |
| `opt_out(user_id, zones)` | MISSING | - | - |
| `is_opted_out(zone)` | MISSING | - | - |
| Zone-based consent checking | MISSING | - | - |
| Integration with event emission | MISSING | - | - |

**Acceptance Criteria:**
- [ ] `from spaxiom.governance import ConsentManager`
- [ ] Zone opt-out prevents event emission for that zone
- [ ] User-level opt-out for specific zones

**Proving Test:** `tests/paper_parity/test_governance_consent.py`
**Proving Example:** `examples/paper/governance_consent.py`

---

### 5.3 Authorization (RBAC/ABAC)

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `RBAC` class | MISSING | - | Not implemented |
| `Role` class | MISSING | - | - |
| `rbac.add_role()`, `assign_user()` | MISSING | - | - |
| `rbac.can(user, action)` | MISSING | - | - |
| `ABAC` class | MISSING | - | Not implemented |
| `Policy` class | MISSING | - | - |
| `abac.is_allowed(user, action, resource)` | MISSING | - | - |

**Acceptance Criteria:**
- [ ] `from spaxiom.security import RBAC, Role`
- [ ] `from spaxiom.security import ABAC, Policy`
- [ ] Authorization checks enforced on subscriptions and queries

**Proving Test:** `tests/paper_parity/test_governance_authorization.py`
**Proving Example:** `examples/paper/governance_authorization.py`

---

### 5.4 Audit Logging

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `AuditLogger` class | MISSING | - | Not implemented |
| `append_only_db` backend | MISSING | - | - |
| `audit.log(entry)` | MISSING | - | - |
| Cryptographic signing | MISSING | - | - |
| Tamper detection (`verify()`) | MISSING | - | - |
| Structured audit events | MISSING | - | - |

**Acceptance Criteria:**
- [ ] `from spaxiom.security import AuditLogger`
- [ ] Audit entries are append-only
- [ ] Entries can be cryptographically signed
- [ ] Tamper detection via signature verification

**Proving Test:** `tests/paper_parity/test_governance_audit.py`
**Proving Example:** `examples/paper/governance_audit.py`

---

## 6. Tooling

### 6.1 CLI

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `spax-run run <script>` | IMPLEMENTED | `spaxiom/cli.py:25` | Works |
| `--poll-ms` option | IMPLEMENTED | `spaxiom/cli.py:28` | Works |
| `--history-length` option | IMPLEMENTED | `spaxiom/cli.py:33` | Works |
| `--config` option | IMPLEMENTED | `spaxiom/cli.py:38` | YAML config loading |
| `--verbose` option | IMPLEMENTED | `spaxiom/cli.py:43` | Debug logging |
| `spax-run new <name>` | IMPLEMENTED | `spaxiom/cli.py:146` | Scaffolding |

**Acceptance Criteria:**
- [x] CLI runs scripts and starts runtime
- [x] YAML config loading works

**Proving Test:** `tests/test_cli.py`, `tests/test_cli_scaffold.py`
**Proving Example:** `examples/config_cli_demo.py`

---

### 6.2 Plugin System

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `@register_plugin` decorator | IMPLEMENTED | `spaxiom/plugins.py:23` | Works |
| `discover_and_load_plugins()` | IMPLEMENTED | `spaxiom/plugins.py:53` | Namespace-based discovery |
| `initialize_plugins()` | IMPLEMENTED | `spaxiom/plugins.py:86` | Called by runtime |

**Acceptance Criteria:**
- [x] Plugins discovered from `spaxiom_site_plugins` namespace
- [x] Plugins initialized on runtime startup

**Proving Test:** `tests/test_plugins.py`
**Proving Example:** `examples/plugin_demo.py`, `examples/custom_plugin_demo.py`

---

### 6.3 Type Hints and Docstrings

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Type hints on public functions | PARTIAL | Various | Most have hints, some missing |
| Docstrings on public APIs | PARTIAL | Various | Most have docstrings |

**Acceptance Criteria:**
- [ ] All public functions have type hints
- [ ] All public classes/functions have docstrings
- [ ] Verify with `mypy` and `pydocstyle`

**Proving Test:** CI linting configuration
**Proving Example:** N/A

---

## Summary Table

| Category | IMPLEMENTED | PARTIAL | MISSING | Total |
|----------|-------------|---------|---------|-------|
| Runtime | 3 | 4 | 4 | 11 |
| Conditions | 8 | 1 | 5 | 14 |
| INTENT Patterns | 0 | 4 | 6 | 10 |
| Safety Verification | 0 | 0 | 11 | 11 |
| Governance | 0 | 0 | 12 | 12 |
| Tooling | 8 | 2 | 0 | 10 |
| **Total** | **19** | **11** | **38** | **68** |

---

## Priority Order for Implementation

Based on dependencies and paper structure:

1. **Runtime phased tick** - Foundation for everything else
2. **Pattern base class** - Required for INTENT integration
3. **Condition dependency tracking** - Required for event-driven mode
4. **Event-driven evaluation mode** - Performance optimization
5. **SafetyMonitor** - Safety-critical capability
6. **UPPAAL export** - Formal verification
7. **Governance primitives** - Compliance requirements
8. **Instrumentation** - Production monitoring

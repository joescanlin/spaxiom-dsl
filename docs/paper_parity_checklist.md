# Paper Parity Checklist

**Reference:** `docs/paper/intent_spaxiom_paper.html`
**Generated:** 2024-12-23

This checklist tracks implementation parity between the Spaxiom codebase and the paper specification.

---

## 1. Runtime

> **Runtime Architecture (as of Step 8):**
>
> The runtime now supports two modes via `SPAXIOM_RUNTIME` environment variable or `--runtime` CLI flag:
>
> - **PHASED (default):** `start_runtime()` and `start_blocking()` delegate to `PhasedTickRunner.run()` for deterministic 4-phase tick execution per the paper specification.
> - **LEGACY:** Set `SPAXIOM_RUNTIME=legacy` or use `--runtime legacy` to use the original async task-based runtime for backwards compatibility.
>
> **Implementation:**
> - `spaxiom/runtime.py:475` `start_runtime()` - Delegates based on `RUNTIME_MODE`
> - `spaxiom/runtime.py:307` `_start_runtime_phased()` - Phased mode implementation
> - `spaxiom/runtime.py:379` `_start_runtime_legacy()` - Legacy mode implementation
> - `spaxiom/runtime.py:45` `get_runtime_mode()` / `set_runtime_mode()` - Mode selection API
>
> **Proving Test:** `tests/paper_parity/test_runtime_delegation.py` (11 passing)

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
| Polling mode (default) | IMPLEMENTED | `spaxiom/logic.py:30` `Condition.__init__(mode=)` | Default mode, all conditions evaluated every tick |
| Event-driven mode | IMPLEMENTED | `spaxiom/logic.py:30` `mode="event-driven"` | Only evaluates when dependencies change |
| Auto mode selection | IMPLEMENTED | `spaxiom/logic.py:72` `_effective_mode` | Selects event-driven if dependencies trackable, else polling |
| `Condition(..., mode="event-driven")` | IMPLEMENTED | `spaxiom/logic.py:30` | Supported via `mode` parameter |

**Acceptance Criteria:**
- [x] `Condition` accepts `mode` parameter
- [x] Event-driven mode only evaluates on dependency changes
- [x] Auto mode selects based on dependency complexity

**Proving Test:** `tests/paper_parity/test_event_driven_condition_selection.py`
**Proving Example:** `examples/paper/conditions_event_driven.py`

---

### 2.3 Dependency Tracking

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Conditions track sensor dependencies | IMPLEMENTED | `spaxiom/logic.py:56` `Condition.dependencies` | Manual via `depends_on` parameter |
| Conditions track pattern dependencies | IMPLEMENTED | `spaxiom/logic.py:56` `Condition.dependencies` | Manual via `depends_on` parameter |
| Conditions track temporal buffer dependencies | PARTIAL | `spaxiom/temporal.py` | Internal to temporal operators |
| Runtime invalidates affected conditions | IMPLEMENTED | `spaxiom/tick.py:280` `_phase3_condition_eval()` | Tracks updated sensors, skips unaffected conditions |

**Acceptance Criteria:**
- [x] `Condition.dependencies` returns set of sensors/patterns
- [x] Runtime only evaluates conditions when dependencies change (event-driven mode)
- [x] Unrelated conditions not evaluated (testable)

**Proving Test:** `tests/paper_parity/test_condition_dependency_tracking.py`
**Proving Example:** `examples/paper/conditions_dependencies.py`

---

## 3. INTENT Patterns

### 3.1 Pattern Base Class

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `Pattern` base class | IMPLEMENTED | `spaxiom/intent/pattern.py:20` `Pattern` | ABC with update/emit/depends_on |
| `update(dt, context)` method | IMPLEMENTED | `spaxiom/intent/pattern.py:45` | Called by runtime each tick |
| `emit()` method returning typed events | IMPLEMENTED | `spaxiom/intent/pattern.py:55` | Returns list of PatternEvent |
| `depends_on()` method | IMPLEMENTED | `spaxiom/intent/pattern.py:65` | Returns list of dependencies |
| Stable event serialization (`to_dict()`) | IMPLEMENTED | `spaxiom/intent/pattern.py:80` `PatternEvent.to_dict()` | Dataclass-based serialization |

**Acceptance Criteria:**
- [x] `Pattern` base class with abstract methods
- [x] `update()` called by runtime each tick with `dt` and context
- [x] `emit()` returns list of typed event objects
- [x] `depends_on()` returns list of sensors/patterns
- [x] Events have `to_dict()` for JSON serialization

**Proving Test:** `tests/paper_parity/test_intent_pattern_emits_event.py`
**Proving Example:** `examples/paper/intent_occupancyfield.py`

---

### 3.2 Implemented Patterns

| Pattern | Status | Code Pointer | Notes |
|---------|--------|--------------|-------|
| `OccupancyField` | IMPLEMENTED | `spaxiom/intent/occupancy_field.py:20` | Inherits Pattern, emits OccupancyChanged |
| `QueueFlow` | IMPLEMENTED | `spaxiom/intent/queue_flow.py:18` | Inherits Pattern, emits QueueLengthChanged |
| `ADLTracker` | IMPLEMENTED | `spaxiom/intent/adl_tracker.py:15` | Inherits Pattern, emits ADLEvent |
| `FmSteward` | IMPLEMENTED | `spaxiom/intent/fm_steward.py:15` | Inherits Pattern, emits ServiceNeeded |

**Acceptance Criteria:**
- [x] All patterns inherit from `Pattern` base class
- [x] All patterns implement `update(dt, context)`, `emit()`, `depends_on()`
- [x] Patterns integrated into runtime tick loop

**Proving Test:** `tests/paper_parity/test_intent_patterns_interface.py`
**Proving Example:** `examples/paper/intent_all_patterns.py`

---

### 3.3 Runtime Integration

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Pattern registration | IMPLEMENTED | `spaxiom/tick.py:218` `register_pattern()` | Patterns registered with runner |
| Dependency-ordered updates | IMPLEMENTED | `spaxiom/tick.py:280` `_phase2_pattern_updates()` | Topological sort by depends_on |
| Event collection | IMPLEMENTED | `spaxiom/tick.py:295` | Per-tick event stream |
| Event subscription | IMPLEMENTED | `spaxiom/intent/pattern.py:90` `on_pattern_event()` | Subscribe to pattern events |

**Proving Test:** `tests/paper_parity/test_runtime_tick_ordering.py::test_phase2_patterns_dependency_ordered`

---

## 4. Safety Verification

### 4.1 Verifiable Subset

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| Define verifiable subset of DSL | IMPLEMENTED | `spaxiom/safety/ir.py:40` `VerifiableCondition` | Opt-in via explicit construction |
| Internal IR for verifiable conditions | IMPLEMENTED | `spaxiom/safety/ir.py:15` `IRNode` hierarchy | AST-like representation |
| Restricted operators (no Python lambdas) | IMPLEMENTED | `spaxiom/safety/ir.py` | Only Boolean ops, comparisons, temporal |
| Bounded iteration only | N/A | - | No iteration in condition IR |

**Acceptance Criteria:**
- [x] `VerifiableCondition` class for verifiable subset
- [x] IR representation for conditions (`IRNode`, `IRCompare`, `IRAnd`, etc.)
- [x] Validation that condition is in verifiable subset (only IR-based ops allowed)

**Proving Test:** `tests/paper_parity/test_verifiable_subset.py`
**Proving Example:** `examples/paper/safety_export_uppaal.py`

---

### 4.2 UPPAAL Export

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `verify.compile_to_uppaal()` | IMPLEMENTED | `spaxiom/safety/verify.py:25` `compile_to_uppaal()` | Export function |
| Timed automaton generation | IMPLEMENTED | `spaxiom/safety/verify.py:50` `UppaalAutomaton` | Automaton wrapper class |
| `.xml` file output | IMPLEMENTED | `spaxiom/safety/verify.py:85` `UppaalAutomaton.save()` | Produces valid UPPAAL XML |
| Clock/timing modeling | IMPLEMENTED | `spaxiom/safety/verify.py:70` | Clocks for temporal conditions |

**Acceptance Criteria:**
- [x] `from spaxiom.safety import verify` works
- [x] `compile_to_uppaal(conditions, zones)` returns automaton object
- [x] `automaton.save("file.xml")` produces valid UPPAAL XML
- [ ] XML parseable by UPPAAL tool (export-only, not validated against UPPAAL)

**Proving Test:** `tests/paper_parity/test_safety_export_uppaal.py`
**Proving Example:** `examples/paper/safety_export_uppaal.py`

---

### 4.3 SafetyMonitor

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `SafetyMonitor` class | IMPLEMENTED | `spaxiom/safety/monitor.py:25` `SafetyMonitor` | Runtime safety checker |
| `property` parameter (safety condition) | IMPLEMENTED | `spaxiom/safety/monitor.py:35` | Via constructor |
| `on_violation` callback | IMPLEMENTED | `spaxiom/safety/monitor.py:40` | Failsafe callback |
| `compile_to_uppaal()` method | IMPLEMENTED | `spaxiom/safety/monitor.py:95` | Exports monitor to UPPAAL |
| Structured audit records | IMPLEMENTED | `spaxiom/safety/monitor.py:15` `SafetyViolation` | Dataclass with schema |
| Runtime monitoring loop | IMPLEMENTED | `spaxiom/tick.py:350` | Integrated into Phase 4 |

**Acceptance Criteria:**
- [x] `SafetyMonitor(name, property, on_violation)` constructor
- [x] Monitor integrated into runtime
- [x] Violation triggers callback and emits structured `SafetyViolation` event
- [x] Audit events have structured schema

**Proving Test:** `tests/paper_parity/test_safety_monitor.py`
**Proving Example:** `examples/paper/safety_export_uppaal.py`

---

## 5. Governance

### 5.1 Retention Policy

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `RetentionPolicy` class | IMPLEMENTED | `spaxiom/governance/retention.py:15` `RetentionPolicy` | Dataclass with TTL config |
| `default_days` parameter | IMPLEMENTED | `spaxiom/governance/retention.py:18` | Default 30 days |
| `raw_events_days` parameter | IMPLEMENTED | `spaxiom/governance/retention.py:19` | Default 7 days |
| `exceptions` list for compliance events | IMPLEMENTED | `spaxiom/governance/retention.py:20` | Events retained indefinitely |
| `max_entries` limit | IMPLEMENTED | `spaxiom/governance/retention.py:21` | Bounded buffer size |
| `runtime.set_retention_policy()` | IMPLEMENTED | `spaxiom/tick.py:195` | Hook method |
| `apply_to_buffer()` for purging | IMPLEMENTED | `spaxiom/governance/retention.py:45` | TTL + max entries enforcement |
| `should_retain()` check | IMPLEMENTED | `spaxiom/governance/retention.py:35` | Per-event age check |

**Acceptance Criteria:**
- [x] `from spaxiom.governance import RetentionPolicy`
- [x] Policy enforced by history buffers via `apply_to_buffer()`
- [x] Events older than policy are automatically purged
- [x] Exception events retained longer (indefinitely)
- [x] `max_entries` limits buffer size

**Proving Test:** `tests/paper_parity/test_governance_retention.py` (8 passing)
**Proving Example:** `examples/paper/governance_demo.py`

---

### 5.2 Consent Manager

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `ConsentManager` class | IMPLEMENTED | `spaxiom/governance/consent.py:12` `ConsentManager` | Zone/entity consent tracking |
| `opt_out(user_id, zones)` | IMPLEMENTED | `spaxiom/governance/consent.py:22` | Per-user zone opt-out |
| `opt_in(user_id, zones)` | IMPLEMENTED | `spaxiom/governance/consent.py:30` | Reverses opt-out |
| `is_opted_out(zone)` | IMPLEMENTED | `spaxiom/governance/consent.py:38` | Check zone/user opt-out |
| `suppress_zone(zone)` | IMPLEMENTED | `spaxiom/governance/consent.py:50` | Global zone suppression |
| `should_suppress_event()` | IMPLEMENTED | `spaxiom/governance/consent.py:55` | Event-level check |
| `filter_event()` | IMPLEMENTED | `spaxiom/governance/consent.py:65` | Returns None if suppressed |
| `get_consent_summary()` | IMPLEMENTED | `spaxiom/governance/consent.py:80` | Statistics dict |
| `runtime.set_consent_manager()` | IMPLEMENTED | `spaxiom/tick.py:200` | Hook method |

**Acceptance Criteria:**
- [x] `from spaxiom.governance import ConsentManager`
- [x] Zone opt-out prevents event emission for that zone
- [x] User-level opt-out for specific zones
- [x] Global zone suppression
- [x] `opt_in()` reverses `opt_out()`

**Proving Test:** `tests/paper_parity/test_governance_consent.py` (9 passing)
**Proving Example:** `examples/paper/governance_demo.py`

---

### 5.3 Authorization (RBAC/ABAC)

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `RBAC` class | IMPLEMENTED | `spaxiom/governance/authz.py:25` `RBAC` | Role-based access control |
| `Role` class | IMPLEMENTED | `spaxiom/governance/authz.py:12` `Role` | Dataclass with permissions set |
| `rbac.add_role()` | IMPLEMENTED | `spaxiom/governance/authz.py:32` | Add role definition |
| `rbac.assign_user()` | IMPLEMENTED | `spaxiom/governance/authz.py:38` | Assign user to role |
| `rbac.can(user, action)` | IMPLEMENTED | `spaxiom/governance/authz.py:48` | Check permission |
| Wildcard permissions (`*`, `read:*`) | IMPLEMENTED | `spaxiom/governance/authz.py:55` | Glob-style matching |
| `ABAC` class | IMPLEMENTED | `spaxiom/governance/authz.py:75` `ABAC` | Attribute-based access control |
| `Policy` class | IMPLEMENTED | `spaxiom/governance/authz.py:18` `Policy` | Condition-based policy |
| `abac.add_policy()` | IMPLEMENTED | `spaxiom/governance/authz.py:82` | Add policy |
| `abac.is_allowed()` | IMPLEMENTED | `spaxiom/governance/authz.py:88` | Evaluate with context |
| Deny takes precedence | IMPLEMENTED | `spaxiom/governance/authz.py:95` | Deny overrides allow |
| `Authorizer` class | IMPLEMENTED | `spaxiom/governance/authz.py:110` `Authorizer` | Combined RBAC + ABAC |
| `runtime.set_authorizer()` | IMPLEMENTED | `spaxiom/tick.py:205` | Hook method |

**Acceptance Criteria:**
- [x] `from spaxiom.governance import RBAC, Role`
- [x] `from spaxiom.governance import ABAC, Policy`
- [x] `from spaxiom.governance import Authorizer`
- [x] RBAC permission checks with wildcards
- [x] ABAC policy evaluation with context
- [x] Deny policies take precedence

**Proving Test:** `tests/paper_parity/test_governance_authorization.py` (14 passing)
**Proving Example:** `examples/paper/governance_demo.py`

---

### 5.4 Audit Logging

| Requirement | Status | Code Pointer | Notes |
|-------------|--------|--------------|-------|
| `AuditLogger` class | IMPLEMENTED | `spaxiom/governance/audit.py:35` `AuditLogger` | Append-only audit log |
| `AuditEntry` class | IMPLEMENTED | `spaxiom/governance/audit.py:12` `AuditEntry` | Structured event dataclass |
| `backend` parameter | IMPLEMENTED | `spaxiom/governance/audit.py:40` | "memory" or "append_only_db" |
| `audit.log(entry)` | IMPLEMENTED | `spaxiom/governance/audit.py:52` | Append entry |
| `audit.log_event()` | IMPLEMENTED | `spaxiom/governance/audit.py:65` | Convenience method |
| `audit.seal()` | IMPLEMENTED | `spaxiom/governance/audit.py:80` | Prevent further writes |
| Cryptographic signing | IMPLEMENTED | `spaxiom/governance/audit.py:88` `sign()` | HMAC-SHA256 |
| `verify()` | IMPLEMENTED | `spaxiom/governance/audit.py:100` | Verify entry signature |
| `verify_integrity()` | IMPLEMENTED | `spaxiom/governance/audit.py:110` | Check all entries |
| Auto-signing with `signing_key` | IMPLEMENTED | `spaxiom/governance/audit.py:45` | Auto-sign on log |
| `get_entries()` filtering | IMPLEMENTED | `spaxiom/governance/audit.py:120` | Query by actor/event_type |
| `export()` | IMPLEMENTED | `spaxiom/governance/audit.py:135` | Export to dict list |
| `runtime.set_audit_logger()` | IMPLEMENTED | `spaxiom/tick.py:210` | Hook method |

**Acceptance Criteria:**
- [x] `from spaxiom.governance import AuditLogger, AuditEntry`
- [x] Audit entries are append-only (seal prevents writes)
- [x] Entries can be cryptographically signed (HMAC-SHA256)
- [x] Tamper detection via signature verification
- [x] Structured audit events with `to_dict()`

**Proving Test:** `tests/paper_parity/test_governance_audit.py` (14 passing)
**Proving Example:** `examples/paper/governance_demo.py`

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
| Conditions | 13 | 1 | 0 | 14 |
| INTENT Patterns | 0 | 4 | 6 | 10 |
| Safety Verification | 0 | 0 | 11 | 11 |
| Governance | 34 | 0 | 0 | 34 |
| Tooling | 8 | 2 | 0 | 10 |
| **Total** | **58** | **11** | **21** | **90** |

---

## Priority Order for Implementation

Based on dependencies and paper structure:

1. ~~**Runtime phased tick**~~ - DONE (Step 2)
2. **Pattern base class** - Required for INTENT integration
3. ~~**Condition dependency tracking**~~ - DONE (Step 3)
4. ~~**Event-driven evaluation mode**~~ - DONE (Step 3)
5. **SafetyMonitor** - Safety-critical capability
6. **UPPAAL export** - Formal verification
7. **Governance primitives** - Compliance requirements
8. **Instrumentation** - Production monitoring

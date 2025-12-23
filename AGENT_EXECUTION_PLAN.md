# Spaxiom/INTENT Paper Parity Execution Plan

This file defines the exact sequence of work Claude Code must execute.

## Step 0: Baseline inventory (no code changes)
Goal: produce an accurate map of what exists today.

Actions:
1. Create `docs/agent_audit.md` with:
   - repo structure summary
   - exact file paths and symbols for:
     - Runtime and runtime entrypoints (`start_blocking`, async runner, tick loop)
     - Sensor, Zone, Condition, decorators (`@on`)
     - temporal ops (`within`, `exists`)
     - plugin system
     - CLI entrypoints and commands
     - examples and tests
   - how to set up and run (commands only, do not run yet)
2. Create `docs/paper_parity_checklist.md` with sections:
   - Runtime
   - Conditions
   - INTENT patterns
   - Safety verification
   - Governance
   - Tooling
   For each item:
   - requirement statement
   - current status: IMPLEMENTED, PARTIAL, or MISSING
   - code pointer (file path + symbol) if implemented
   - acceptance criteria
   - proving test name (path)
   - proving example (path)

Completion criteria:
- Both docs exist and include real file references.
- No source code changes beyond docs.

## Step 1: Add paper parity harness (minimal scaffolding)
Goal: create the structure that will prove parity over time.

Actions:
1. Add folders:
   - `examples/paper/`
   - `tests/paper_parity/`
2. Add three initial tests (can be skipped initially, but must be specific):
   - `test_runtime_tick_ordering.py`
   - `test_event_driven_condition_selection.py`
   - `test_intent_pattern_emits_event.py`
3. Add one minimal example script that runs without hardware:
   - `examples/paper/runtime_minimal.py`

Completion criteria:
- Test harness is runnable.
- Skips are allowed only if each skip states a precise missing capability.

## Step 2: Runtime parity (phased tick)
Goal: match the paper’s runtime execution model.

Actions:
1. Implement or refactor runtime to a deterministic phased tick:
   1) sensor reads (concurrent where safe)
   2) pattern updates (dependency ordered)
   3) condition evaluation (polling or event-driven)
   4) callback dispatch (isolated)
2. Preserve a blocking wrapper for existing usage.
3. Add instrumentation per tick:
   - timings per phase
   - counts for sensors, patterns, conditions, handlers

Proving artifacts:
- `examples/paper/runtime_tick_phases.py`
- `tests/paper_parity/test_runtime_tick_ordering.py` must pass and assert deterministic ordering.

## Step 3: Condition engine parity (dependency tracking + evaluation modes)
Goal: support polling, event-driven, and auto evaluation.

Actions:
1. Implement dependency tracking:
   - conditions track dependencies on sensors, patterns, and temporal buffers
   - runtime invalidates affected conditions on updates
2. Implement evaluation modes:
   - polling: evaluate all each tick
   - event-driven: evaluate only impacted conditions
   - auto: chooses event-driven when dependencies are trackable

Proving artifacts:
- `examples/paper/conditions_event_driven.py`
- `tests/paper_parity/test_event_driven_condition_selection.py` must pass and prove that unrelated conditions are not evaluated.

## Step 4: INTENT patterns integrated into runtime
Goal: patterns are real runtime components that emit typed events.

Actions:
1. Add a `Pattern` base class:
   - `update(dt, context)`
   - `emit()`
   - `depends_on()`
2. Define typed event schemas with stable serialization.
3. Implement minimal viable versions of core patterns:
   - OccupancyField
   - QueueFlow
   - ADLTracker
   - FM Steward pattern

Proving artifacts:
- `examples/paper/intent_occupancyfield.py`
- `tests/paper_parity/test_intent_pattern_emits_event.py` must pass and assert event shape and determinism.

## Step 5: Safety verification and monitoring
Goal: export verifiable subset to UPPAAL XML and add runtime monitor.

Actions:
1. Define a verifiable subset and an internal IR.
2. Implement UPPAAL XML export.
3. Implement `SafetyMonitor`:
   - runtime checks
   - failsafe callback
   - structured audit events

Proving artifacts:
- `examples/paper/safety_export_uppaal.py`
- `tests/paper_parity/test_safety_export_uppaal.py` must pass (validate XML structure).
- `tests/paper_parity/test_safety_monitor.py` must pass (validate failsafe behavior).

## Step 6: Governance enforcement
Goal: runtime-enforced retention, consent, authorization, and audits.

Actions:
1. Implement enforceable primitives:
   - retention policy for history buffers
   - consent manager (zone or entity opt-out)
   - authorizer for subscriptions and queries
   - structured audit log
2. Ensure these are actually enforced in runtime and in query paths.

Proving artifacts:
- `examples/paper/governance_consent_and_retention.py`
- tests:
  - `test_governance_consent.py`
  - `test_governance_retention.py`
  - `test_governance_authorization.py`

## Step 7: Ship readiness
Goal: make it easy to run, verify, and maintain.

Actions:
1. Update README:
   - what is implemented today
   - how to run paper examples
   - how to run parity tests
2. Ensure CI runs tests if CI exists.
3. Add developer commands (Makefile or documented commands) if consistent with repo norms.

## Definition of done
- Every parity checklist item is IMPLEMENTED or explicitly deferred with rationale.
- All `tests/paper_parity/` pass.
- At least one example exists for each epic area: runtime, conditions, patterns, safety, governance.
- No regressions in existing documented examples.
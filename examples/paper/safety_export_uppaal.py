#!/usr/bin/env python3
"""
safety_export_uppaal.py - Paper Parity Example

Demonstrates:
1. Verifiable subset of the DSL (IR representation)
2. UPPAAL timed automaton export
3. SafetyMonitor runtime integration

Reference: Paper Section 7.3

Outputs: artifacts/robot_safety.xml
"""

import asyncio
import os

from spaxiom.tick import PhasedTickRunner
from spaxiom.safety import (
    # IR nodes and builders
    IRAnd,
    IROr,
    signal,
    compare,
    within,
    verifiable,
    # Monitor
    SafetyMonitor,
    SafetyViolation,
    # UPPAAL export
    verify,
)


def main():
    print("=" * 60)
    print("safety_export_uppaal.py - Safety Verification Demo")
    print("=" * 60)
    print()

    # =========================================================================
    # 1. Verifiable Subset: IR Representation
    # =========================================================================
    print("1. Verifiable Subset: IR Representation")
    print("-" * 40)

    # Define safety signals (sensor values)
    robot_speed = signal("robot_speed")
    human_distance = signal("human_distance")
    emergency_stop = signal("emergency_stop")

    print("   Defined signals:")
    print(f"     - robot_speed: {robot_speed}")
    print(f"     - human_distance: {human_distance}")
    print(f"     - emergency_stop: {emergency_stop}")
    print()

    # Define safety conditions using IR
    # Safety property 1: Robot speed < 100 units
    speed_limit = compare("robot_speed", "<", 100)
    print(f"   Speed limit condition: {speed_limit.to_uppaal_guard()}")

    # Safety property 2: Human distance > 2.0 meters OR emergency stop active
    safe_distance = compare("human_distance", ">", 2.0)
    e_stop_active = compare("emergency_stop", "==", True)
    human_safety = IROr(safe_distance, e_stop_active)
    print(f"   Human safety condition: {human_safety.to_uppaal_guard()}")

    # Combined safety property
    combined = IRAnd(speed_limit, human_safety)
    print(f"   Combined: {combined.to_uppaal_guard()}")
    print()

    # =========================================================================
    # 2. VerifiableCondition Wrapper
    # =========================================================================
    print("2. VerifiableCondition Wrapper")
    print("-" * 40)

    robot_safe = verifiable(combined, name="robot_safety_property")
    print(f"   Created: {robot_safe}")
    print(f"   Signals: {robot_safe.get_signals()}")
    print(f"   Clocks: {robot_safe.get_clocks()}")
    print()

    # Evaluate the condition
    print("   Evaluating:")
    ctx1 = {"robot_speed": 50, "human_distance": 5.0, "emergency_stop": False}
    print(f"     {ctx1} -> {robot_safe.evaluate(ctx1)}")

    ctx2 = {"robot_speed": 150, "human_distance": 5.0, "emergency_stop": False}
    print(f"     {ctx2} -> {robot_safe.evaluate(ctx2)}")

    ctx3 = {"robot_speed": 50, "human_distance": 1.0, "emergency_stop": True}
    print(f"     {ctx3} -> {robot_safe.evaluate(ctx3)}")
    print()

    # =========================================================================
    # 3. Temporal Conditions (with clocks)
    # =========================================================================
    print("3. Temporal Conditions (with clocks)")
    print("-" * 40)

    # Motion must be detected for 5 seconds to trigger
    motion_detected = compare("motion", "==", True)
    sustained_motion = within(motion_detected, 5.0, "motion_clk")
    temporal_cond = verifiable(sustained_motion, name="sustained_motion")

    print(f"   Temporal condition: {temporal_cond.to_uppaal_guard()}")
    print(f"   Clocks required: {temporal_cond.get_clocks()}")
    print()

    # =========================================================================
    # 4. SafetyMonitor
    # =========================================================================
    print("4. SafetyMonitor")
    print("-" * 40)

    violations_logged = []

    def on_violation(v: SafetyViolation):
        violations_logged.append(v)
        print(f"   [VIOLATION] {v.monitor_name}: {v.message}")

    monitor = SafetyMonitor(
        name="robot_monitor",
        property=robot_safe,
        on_violation=on_violation,
    )
    print(f"   Created monitor: {monitor}")

    # Simulate checking
    print("   Simulating safety checks:")

    # Safe state
    monitor.check({"robot_speed": 50, "human_distance": 5.0, "emergency_stop": False})
    print("     Check 1 (safe): No violation")

    # Still safe
    monitor.check({"robot_speed": 80, "human_distance": 3.0, "emergency_stop": False})
    print("     Check 2 (safe): No violation")

    # Violation: speed too high
    monitor.check({"robot_speed": 120, "human_distance": 3.0, "emergency_stop": False})

    print(f"   Total violations: {len(monitor.violations)}")
    print()

    # =========================================================================
    # 5. UPPAAL Export
    # =========================================================================
    print("5. UPPAAL Export")
    print("-" * 40)

    # Create multiple conditions for a richer automaton
    cond1 = verifiable(compare("robot_speed", "<", 100), "speed_safe")
    cond2 = verifiable(compare("human_distance", ">", 2.0), "distance_safe")
    cond3 = verifiable(compare("temperature", "<", 80), "temp_safe")

    # Compile to UPPAAL
    automaton = verify.compile_to_uppaal(
        conditions=[cond1, cond2, cond3],
        name="RobotSafetyMonitor",
    )

    print(f"   Automaton name: {automaton.name}")
    print(f"   Locations: {len(automaton.locations)}")
    print(f"   Transitions: {len(automaton.transitions)}")
    print(f"   Variables: {[v[0] for v in automaton.variables]}")
    print()

    # Save to file
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "robot_safety.xml")

    automaton.save(output_path)
    print(f"   Saved: {output_path}")

    # Show XML structure
    xml_content = automaton.to_xml()
    print(f"   XML size: {len(xml_content)} bytes")
    print()

    # =========================================================================
    # 6. SafetyMonitor compile_to_uppaal
    # =========================================================================
    print("6. SafetyMonitor compile_to_uppaal")
    print("-" * 40)

    # Export the monitor itself
    monitor_automaton = monitor.compile_to_uppaal(name="MonitorExport")
    print(f"   Exported monitor as automaton: {monitor_automaton.name}")

    monitor_path = os.path.join(output_dir, "monitor_export.xml")
    monitor_automaton.save(monitor_path)
    print(f"   Saved: {monitor_path}")
    print()

    # =========================================================================
    # 7. Runtime Integration
    # =========================================================================
    print("7. Runtime Integration")
    print("-" * 40)

    async def run_with_runtime():
        runner = PhasedTickRunner(tick_rate_hz=10.0)

        # For runtime, we need a callable that returns the current state
        current_speed = [50]

        def check_speed():
            return current_speed[0] < 100

        runtime_monitor = SafetyMonitor(
            name="runtime_speed_monitor",
            property=check_speed,
            on_violation=lambda v: print(f"     [RUNTIME VIOLATION] {v.monitor_name}"),
        )

        runner.register_safety_monitor(runtime_monitor)
        print("   Registered monitor with runtime")

        # Run first tick (safe)
        stats = await runner.run_single_tick()
        print(
            f"   Tick 1: monitors={stats.safety_monitors_checked}, "
            f"violations={stats.safety_violations}"
        )

        # Change speed to trigger violation
        current_speed[0] = 150

        stats = await runner.run_single_tick()
        print(
            f"   Tick 2: monitors={stats.safety_monitors_checked}, "
            f"violations={stats.safety_violations}"
        )

    asyncio.run(run_with_runtime())
    print()

    # =========================================================================
    # 8. Audit Records
    # =========================================================================
    print("8. Audit Records")
    print("-" * 40)

    records = monitor.get_audit_records()
    print(f"   Audit records from monitor: {len(records)}")
    for i, record in enumerate(records):
        print(f"   Record {i + 1}:")
        print(f"     timestamp: {record['timestamp']}")
        print(f"     monitor: {record['monitor_name']}")
        print(f"     property: {record['property_name']}")
        print(f"     state: {record['state']}")
    print()

    print("=" * 60)
    print("Done!")
    print(f"Generated artifacts in: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

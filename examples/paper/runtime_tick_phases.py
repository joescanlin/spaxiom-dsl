#!/usr/bin/env python3
"""
runtime_tick_phases.py - Paper Parity Example

Demonstrates the deterministic 4-phase tick execution model:
1. Sensor reads (concurrent)
2. Pattern updates (dependency-ordered)
3. Condition evaluation
4. Callback dispatch (concurrent, isolated)

Reference: Paper Section 2.5 "Runtime Architecture and Execution Model"
"""

import asyncio

from spaxiom import (
    RandomSensor,
    Condition,
    SensorRegistry,
    PhasedTickRunner,
    enable_profiling,
)
from spaxiom.events import on, EVENT_HANDLERS


def main():
    print("=" * 60)
    print("runtime_tick_phases.py - Phased Tick Execution Demo")
    print("=" * 60)
    print()

    # Clear any existing state
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()

    # Create sensors with different purposes
    temp_sensor = RandomSensor(name="temperature", location=(0, 0, 0))
    motion_sensor = RandomSensor(name="motion", location=(1, 0, 0))
    RandomSensor(
        name="light", location=(2, 0, 0)
    )  # Unused but demonstrates concurrency

    print("Created 3 sensors: temperature, motion, light")

    # Create conditions
    temp_high = Condition(lambda: temp_sensor.read() > 0.7)
    motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

    # Register callbacks
    @on(temp_high)
    def on_temp_high():
        print("  -> Callback: Temperature is high!")

    @on(motion_detected)
    def on_motion():
        print("  -> Callback: Motion detected!")

    print("Registered 2 conditions with callbacks")
    print()

    # Create the phased tick runner
    runner = PhasedTickRunner(tick_rate_hz=10.0)  # 10 Hz = 100ms per tick
    enable_profiling(runner)

    print(f"Created PhasedTickRunner with tick_rate={runner.tick_rate_hz} Hz")
    print(f"Tick period: {runner.tick_period_s * 1000:.0f} ms")
    print()

    # Run a few ticks and show the phase ordering
    print("Running 5 ticks with phase instrumentation:")
    print("-" * 40)

    async def run_demo():
        for i in range(5):
            stats = await runner.run_single_tick()
            print(f"Tick {stats.tick_number}:")
            print(f"  Phase order: {' -> '.join(stats.phase_order)}")
            print(f"  Sensors read: {stats.sensors_read}")
            print(f"  Conditions evaluated: {stats.conditions_evaluated}")
            print(f"  Callbacks dispatched: {stats.callbacks_dispatched}")
            print(f"  Total duration: {stats.tick_duration_ms:.2f} ms")
            print()

    asyncio.run(run_demo())

    # Show profiler stats
    print("-" * 40)
    print("Profiler Statistics:")
    stats = runner.profiler.get_stats()
    print(f"  Total ticks: {stats['tick_count']}")
    print(f"  Average tick duration: {stats['avg_tick_ms']:.2f} ms")
    print(f"  Phase 1 (sensor read) avg: {stats['phase1_sensor_read_avg_ms']:.2f} ms")
    print(
        f"  Phase 2 (pattern update) avg: {stats['phase2_pattern_update_avg_ms']:.2f} ms"
    )
    print(
        f"  Phase 3 (condition eval) avg: {stats['phase3_condition_eval_avg_ms']:.2f} ms"
    )
    print(
        f"  Phase 4 (callback dispatch) avg: {stats['phase4_callback_dispatch_avg_ms']:.2f} ms"
    )
    print(f"  Callback failures: {stats['callback_failures']}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()

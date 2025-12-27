#!/usr/bin/env python3
"""
runtime_profiling.py - Paper Parity Example

Demonstrates per-tick instrumentation and profiling:
- enable_profiling(runtime)
- runtime.profiler.get_stats()
- Phase timing statistics

Reference: Paper Section 2.5 "Performance profiling and debugging"
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
    print("runtime_profiling.py - Profiling API Demo")
    print("=" * 60)
    print()

    # Clear any existing state
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()

    # Create several sensors to generate some load
    sensors = []
    for i in range(10):
        sensors.append(RandomSensor(name=f"sensor_{i}", location=(i, 0, 0)))

    print(f"Created {len(sensors)} sensors")

    # Create conditions
    conditions = []
    for i, sensor in enumerate(sensors[:5]):
        cond = Condition(lambda s=sensor: s.read() > 0.5)
        conditions.append(cond)

        @on(cond)
        def handler(idx=i):
            pass  # Silent callback

    print(f"Registered {len(conditions)} conditions with callbacks")
    print()

    # Create runner and enable profiling
    runner = PhasedTickRunner(tick_rate_hz=100.0)  # 100 Hz for fast ticks
    enable_profiling(runner)

    print("Profiling enabled")
    print(f"Running 100 ticks at {runner.tick_rate_hz} Hz...")
    print()

    # Run many ticks
    async def run_benchmark():
        for _ in range(100):
            await runner.run_single_tick()

    asyncio.run(run_benchmark())

    # Get and display stats
    stats = runner.profiler.get_stats()

    print("=" * 40)
    print("PROFILER STATISTICS")
    print("=" * 40)
    print()
    print("Tick Statistics:")
    print(f"  Total ticks recorded: {stats['tick_count']}")
    print(f"  Average tick duration: {stats['avg_tick_ms']:.3f} ms")
    print()
    print("Phase Timings (average per tick):")
    print(f"  Phase 1 - Sensor Read:      {stats['phase1_sensor_read_avg_ms']:.3f} ms")
    print(
        f"  Phase 2 - Pattern Update:   {stats['phase2_pattern_update_avg_ms']:.3f} ms"
    )
    print(
        f"  Phase 3 - Condition Eval:   {stats['phase3_condition_eval_avg_ms']:.3f} ms"
    )
    print(
        f"  Phase 4 - Callback Dispatch: {stats['phase4_callback_dispatch_avg_ms']:.3f} ms"
    )
    print()
    print("Aggregate Counts:")
    print(f"  Total sensors read: {stats['sensors_read_total']}")
    print(f"  Total conditions evaluated: {stats['conditions_evaluated_total']}")
    print(f"  Total callbacks dispatched: {stats['callbacks_dispatched_total']}")
    print(f"  Total callback failures: {stats['callback_failures']}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()

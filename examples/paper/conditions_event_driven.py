#!/usr/bin/env python3
"""
conditions_event_driven.py - Paper Parity Example

Demonstrates event-driven condition evaluation mode:
- Condition(..., mode="event-driven")
- Dependency tracking for selective evaluation
- Comparison with polling mode

Reference: Paper Section 2.5 "Condition evaluation: polling vs event-driven"
"""

import asyncio

from spaxiom import (
    Condition,
    RandomSensor,
    SensorRegistry,
    PhasedTickRunner,
    enable_profiling,
)
from spaxiom.events import on, EVENT_HANDLERS


def main():
    print("=" * 60)
    print("conditions_event_driven.py - Event-Driven Evaluation Demo")
    print("=" * 60)
    print()

    # Clear any existing state
    SensorRegistry().clear()
    EVENT_HANDLERS.clear()

    # Create sensors
    sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
    sensor_b = RandomSensor(name="sensor_b", location=(1, 0, 0))

    print("Created 2 sensors: sensor_a, sensor_b")
    print()

    # Create polling condition (default)
    polling_cond = Condition(
        lambda: sensor_a.read() > 0.5,
        mode="polling",
    )

    # Create event-driven condition
    event_driven_cond = Condition(
        lambda: sensor_b.read() > 0.5,
        mode="event-driven",
        depends_on=[sensor_b],
    )

    # Create auto-mode condition
    auto_cond = Condition(
        lambda: sensor_a.read() > 0.8,
        mode="auto",
        depends_on=[sensor_a],  # Has dependencies, so will use event-driven
    )

    print("Created 3 conditions with different modes:")
    print(f"  polling_cond: mode={polling_cond.mode}")
    print(
        f"  event_driven_cond: mode={event_driven_cond.mode}, effective={event_driven_cond._effective_mode}"
    )
    print(f"  auto_cond: mode={auto_cond.mode}, effective={auto_cond._effective_mode}")
    print()

    # Register callbacks
    @on(polling_cond)
    def on_polling():
        pass

    @on(event_driven_cond)
    def on_event_driven():
        pass

    @on(auto_cond)
    def on_auto():
        pass

    print("Registered callbacks for all 3 conditions")
    print()

    # Run ticks and track evaluation counts
    runner = PhasedTickRunner(tick_rate_hz=100.0)
    enable_profiling(runner)

    print("Running 20 ticks...")

    async def run_demo():
        for _ in range(20):
            await runner.run_single_tick()

    asyncio.run(run_demo())

    print()
    print("Evaluation counts after 20 ticks:")
    print(f"  polling_cond: {polling_cond._eval_count} evaluations")
    print(f"  event_driven_cond: {event_driven_cond._eval_count} evaluations")
    print(f"  auto_cond: {auto_cond._eval_count} evaluations")
    print()

    # Analysis
    print("Analysis:")
    print("  - Polling mode: evaluates EVERY tick (20 evaluations expected)")
    print("  - Event-driven mode: only evaluates when sensor_b value changes")
    print("  - Auto mode: selected event-driven since dependencies were declared")
    print()

    # Show profiler stats
    stats = runner.profiler.get_stats()
    print("Profiler Statistics:")
    print(f"  Total ticks: {stats['tick_count']}")
    print(f"  Conditions evaluated total: {stats['conditions_evaluated_total']}")
    print()

    print("Done!")


if __name__ == "__main__":
    main()

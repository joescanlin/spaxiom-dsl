#!/usr/bin/env python3
"""
conditions_dependencies.py - Paper Parity Example

Demonstrates condition dependency tracking:
- Condition.dependencies property
- Manual dependency declaration via depends_on parameter
- Combined conditions inherit dependencies from both operands

Reference: Paper Section 2.5
"""

from spaxiom import Condition, RandomSensor, SensorRegistry


def main():
    print("=" * 60)
    print("conditions_dependencies.py - Dependency Tracking Demo")
    print("=" * 60)
    print()

    # Clear any existing state
    SensorRegistry().clear()

    # Create sensors
    temp_sensor = RandomSensor(name="temperature", location=(0, 0, 0))
    motion_sensor = RandomSensor(name="motion", location=(1, 0, 0))
    light_sensor = RandomSensor(name="light", location=(2, 0, 0))

    print("Created 3 sensors: temperature, motion, light")
    print()

    # Create conditions with explicit dependencies
    temp_high = Condition(
        lambda: temp_sensor.read() > 0.7,
        depends_on=[temp_sensor],
    )
    motion_detected = Condition(
        lambda: motion_sensor.read() > 0.5,
        depends_on=[motion_sensor],
    )
    light_low = Condition(
        lambda: light_sensor.read() < 0.3,
        depends_on=[light_sensor],
    )

    print("Created 3 conditions with explicit dependencies:")
    print(f"  temp_high: depends on {[s.name for s in temp_high.dependencies]}")
    print(
        f"  motion_detected: depends on {[s.name for s in motion_detected.dependencies]}"
    )
    print(f"  light_low: depends on {[s.name for s in light_low.dependencies]}")
    print()

    # Demonstrate dependency combination
    print("Combining conditions with & and |:")

    occupied_and_hot = motion_detected & temp_high
    print(f"  motion_detected & temp_high:")
    print(f"    depends on: {[s.name for s in occupied_and_hot.dependencies]}")

    any_trigger = temp_high | motion_detected | light_low
    print(f"  temp_high | motion_detected | light_low:")
    print(f"    depends on: {[s.name for s in any_trigger.dependencies]}")
    print()

    # Demonstrate inversion preserves dependencies
    temp_normal = ~temp_high
    print("Inverting conditions preserves dependencies:")
    print(f"  ~temp_high:")
    print(f"    depends on: {[s.name for s in temp_normal.dependencies]}")
    print()

    # Show that dependencies are used for identity comparison
    print("Dependency membership check (uses object identity):")
    print(
        f"  temp_sensor in temp_high.dependencies: {temp_sensor in temp_high.dependencies}"
    )
    print(
        f"  motion_sensor in temp_high.dependencies: {motion_sensor in temp_high.dependencies}"
    )
    print()

    print("Done!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Timestamp Demo script for Spaxiom DSL.

This demonstrates:
1. Creating a sensor that toggles between high and low states
2. Using the Condition timestamp tracking features
3. Showing how transitioned_to_true works compared to regular condition evaluation
"""

import time
from spaxiom.logic import Condition, transitioned_to_true
from spaxiom.sensor import TogglingSensor


def main():
    print("Spaxiom Timestamp Demo")
    print("----------------------")
    print("This demonstrates the timestamp tracking features of Condition objects.")
    print()

    # Create a toggling sensor
    sensor = TogglingSensor(
        name="toggle1",
        location=(0.0, 0.0, 0.0),
        toggle_interval=1.0,  # Toggle every 1 second
        high_value=1.0,
        low_value=0.0,
    )

    # Create a condition that's true when sensor value is high
    is_high = Condition(lambda: sensor.read() > 0.5)

    print("Starting test loop. Press Ctrl+C to exit.")
    print()

    try:
        for i in range(20):
            now = time.time()
            
            # Read sensor value
            sensor_value = sensor.read()
            print(f"Iteration {i+1}: Sensor value = {sensor_value}")
            
            # Evaluate the condition
            result = is_high.evaluate(now=now)
            print(f"  Condition is {result}")
            print(f"  Last changed: {is_high.last_changed:.2f}")
            print(f"  Seconds since change: {now - is_high.last_changed:.2f}")
            
            # Check for transition
            transitioned = transitioned_to_true(is_high, now)
            print(f"  Transitioned to true: {transitioned}")
            print()
            
            # Wait a bit
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Demo script for Spaxiom DSL.

This demonstrates:
1. Creating a random sensor
2. Defining a condition based on sensor readings
3. Registering a callback when the condition is true
4. Running the Spaxiom runtime
"""

import asyncio
from spaxiom import Condition, on
from spaxiom.sensor import RandomSensor
from spaxiom.runtime import start_runtime


def main():
    # Create a random sensor at location (0, 0, 0)
    rs = RandomSensor("rand1", location=(0.0, 0.0, 0.0), metadata=None)

    # Define a condition that is true when the sensor value is > 0.8
    high = Condition(lambda: rs.read() > 0.8)

    # Register a callback when the condition is true
    @on(high)
    def blink():
        print("HIGH - Sensor value exceeded threshold!")

    # Print some info
    print("Spaxiom DSL Demo")
    print("----------------")
    print("Random sensor created. Will trigger when value > 0.8")
    print("Press Ctrl+C to exit")
    print()

    # Start the runtime asynchronously
    asyncio.run(start_runtime(poll_ms=500))


if __name__ == "__main__":
    main()

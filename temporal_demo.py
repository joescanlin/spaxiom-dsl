#!/usr/bin/env python3
"""
Temporal Demo script for Spaxiom DSL.

This demonstrates:
1. Creating a sensor that toggles between high and low states
2. Defining instant and temporal conditions
3. Showing how temporal conditions only trigger after the specified duration
"""

import asyncio
import time
from spaxiom import Condition, on, within
from spaxiom.sensor import Sensor
from spaxiom.runtime import start_runtime


class TogglingSensor(Sensor):
    """A sensor that toggles between high and low states at regular intervals."""

    def __init__(
        self, name, location, toggle_interval=2.0, high_value=1.0, low_value=0.0
    ):
        """
        Initialize the toggling sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            toggle_interval: Time in seconds between toggles
            high_value: The "high" value
            low_value: The "low" value
        """
        super().__init__(name=name, sensor_type="toggle", location=location)
        self.toggle_interval = toggle_interval
        self.high_value = high_value
        self.low_value = low_value
        self.last_toggle = time.time()
        self.current_state = False
        self.current_value = low_value

    def read(self):
        """
        Read the current value, toggling if enough time has passed.

        Returns:
            The current sensor value (high or low)
        """
        now = time.time()
        if now - self.last_toggle >= self.toggle_interval:
            self.current_state = not self.current_state
            self.current_value = (
                self.high_value if self.current_state else self.low_value
            )
            self.last_toggle = now
            # Print toggle event
            state_name = "HIGH" if self.current_state else "LOW"
            print(f"Sensor toggled to {state_name} ({self.current_value})")

        return self.current_value


def main():
    # Create a toggling sensor at location (0, 0, 0)
    toggle_sensor = TogglingSensor(
        name="toggle1",
        location=(0.0, 0.0, 0.0),
        toggle_interval=2.0,  # Toggle every 2 seconds
        high_value=1.0,
        low_value=0.0,
    )

    # Define an instant condition that is true when the sensor value is high
    is_high = Condition(lambda: toggle_sensor.read() > 0.5)

    # Define temporal conditions that require the sensor to be high for different durations
    high_for_1s = within(1.0, is_high)
    high_for_3s = within(
        3.0, is_high
    )  # This won't trigger because toggle interval is 2s
    high_for_1_5s = within(
        1.5, is_high
    )  # This should trigger after the sensor has been high for 1.5s

    # Register callbacks for each condition
    @on(is_high)
    def instant_high():
        print("  INSTANT: Sensor value is HIGH!")

    @on(high_for_1s)
    def sustained_1s():
        print("  SUSTAINED 1s: Sensor value has been HIGH for 1 second!")

    @on(high_for_1_5s)
    def sustained_1_5s():
        print("  SUSTAINED 1.5s: Sensor value has been HIGH for 1.5 seconds!")

    @on(high_for_3s)
    def sustained_3s():
        print("  SUSTAINED 3s: Sensor value has been HIGH for 3 seconds!")
        print(
            "  (This shouldn't trigger because the toggle interval is only 2 seconds)"
        )

    # Print some info
    print("Spaxiom Temporal Demo")
    print("---------------------")
    print("Toggling sensor created. Toggles every 2 seconds between HIGH and LOW.")
    print("Will demonstrate:")
    print("  - Instant condition triggered immediately when sensor is HIGH")
    print("  - Temporal condition requiring 1 second of HIGH")
    print("  - Temporal condition requiring 1.5 seconds of HIGH")
    print("  - Temporal condition requiring 3 seconds of HIGH (should never trigger)")
    print("Press Ctrl+C to exit")
    print()

    # Start the runtime with a shorter polling interval for more responsive events
    asyncio.run(start_runtime(poll_ms=100))


if __name__ == "__main__":
    main()

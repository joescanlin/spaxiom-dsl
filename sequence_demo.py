#!/usr/bin/env python3
"""
Sequence Pattern Demo script for Spaxiom DSL.

This demonstrates:
1. Creating conditions that detect specific events
2. Using the sequence pattern to detect ordered temporal sequences
3. Triggering callbacks when sequences are detected
"""

import asyncio
from spaxiom import Sensor, Condition, on, sequence
from spaxiom.runtime import start_runtime


class EventSensor(Sensor):
    """A sensor that triggers an event when manually activated."""

    def __init__(self, name, location=(0, 0, 0)):
        """Initialize an event sensor."""
        super().__init__(name=name, sensor_type="event", location=location)
        self.triggered = False
        self.value = 0.0

    def _read_raw(self):
        """Read the current sensor value."""
        return 1.0 if self.triggered else 0.0

    def trigger(self):
        """Trigger the sensor event."""
        print(f"[EVENT] {self.name} triggered!")
        self.triggered = True
        self.value = 1.0

    def reset(self):
        """Reset the sensor event."""
        self.triggered = False
        self.value = 0.0


def main():
    print("Spaxiom Sequence Pattern Demo")
    print("-----------------------------")
    print("Demonstrating detection of ordered temporal sequences of events.")
    print("This demo simulates a smart home entry sequence:")
    print("1. Motion detected outside")
    print("2. Door opened")
    print("3. Motion detected inside")
    print("4. Lights turned on")
    print("If this sequence occurs within 15 seconds, a welcome routine is triggered.")
    print("\nWaiting for events...\n")

    # Create event sensors for each step in the sequence
    motion_outside = EventSensor("motion_outside", location=(0, 0, 0))
    door = EventSensor("door", location=(1, 0, 0))
    motion_inside = EventSensor("motion_inside", location=(2, 0, 0))
    lights = EventSensor("lights", location=(3, 0, 0))

    # Create conditions for each step
    motion_outside_detected = Condition(lambda: motion_outside.read() > 0.5)
    door_opened = Condition(lambda: door.read() > 0.5)
    motion_inside_detected = Condition(lambda: motion_inside.read() > 0.5)
    lights_on = Condition(lambda: lights.read() > 0.5)

    # Create a sequence pattern for the entry routine
    entry_sequence = sequence(
        motion_outside_detected,
        door_opened,
        motion_inside_detected,
        lights_on,
        within_s=15.0,
    )

    # Register callback for the sequence
    @on(entry_sequence)
    def welcome_home():
        print("\n🎉 WELCOME HOME SEQUENCE DETECTED! 🎉")
        print("All events occurred in the correct order within 15 seconds")
        print("Activating welcome home routine...\n")

    # Start the Spaxiom runtime in a separate task
    runtime_task = asyncio.create_task(start_runtime(poll_ms=500))

    # Simulate the sequence of events with some delay between them
    async def simulate_entry_sequence():
        await asyncio.sleep(2)  # Wait a bit before starting

        print("\n[SIMULATION] Someone approaching the house...")
        motion_outside.trigger()

        await asyncio.sleep(3)  # 3 seconds later

        print("[SIMULATION] Opening the front door...")
        door.trigger()

        await asyncio.sleep(2)  # 2 seconds later

        print("[SIMULATION] Moving inside the house...")
        motion_inside.trigger()

        await asyncio.sleep(3)  # 3 seconds later

        print("[SIMULATION] Turning on the lights...")
        lights.trigger()

        # Total sequence time: 8 seconds (within the 15-second window)

        # Give runtime a chance to process the sequence
        await asyncio.sleep(2)

        # Reset for another demo - out of order sequence
        print("\n----------------------------------------------")
        print("Now testing an out-of-order sequence that shouldn't trigger:")

        # Reset all sensors
        motion_outside.reset()
        door.reset()
        motion_inside.reset()
        lights.reset()

        await asyncio.sleep(2)

        # Trigger events in wrong order
        print("\n[SIMULATION] Turning on the lights first...")
        lights.trigger()

        await asyncio.sleep(1)

        print("[SIMULATION] Someone approaching the house...")
        motion_outside.trigger()

        await asyncio.sleep(1)

        print("[SIMULATION] Moving inside the house...")
        motion_inside.trigger()

        await asyncio.sleep(1)

        print("[SIMULATION] Opening the front door last...")
        door.trigger()

        # Wait to confirm no callback is triggered
        await asyncio.sleep(3)

        print("\nOut-of-order sequence was not detected (as expected)")
        print("Terminating demo...")

        # Cancel the runtime task to exit
        runtime_task.cancel()

    # Run simulation
    try:
        asyncio.run(asyncio.wait([runtime_task, simulate_entry_sequence()]))
    except asyncio.CancelledError:
        print("Runtime stopped")


if __name__ == "__main__":
    main()

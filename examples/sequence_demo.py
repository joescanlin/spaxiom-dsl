#!/usr/bin/env python3
"""
Sequence Pattern Example: Entry Detection

This example demonstrates detecting a sequence of events:
doorOpen → personPresent → doorClose within 10 seconds
and prints "Entry detected" when this sequence occurs.
"""

import asyncio
import time
from spaxiom import Sensor, Condition, on, sequence
from spaxiom.runtime import start_runtime


class DoorSensor(Sensor):
    """A sensor that detects door states (open/closed)."""

    def __init__(self, name, location=(0, 0, 0)):
        """Initialize the door sensor."""
        super().__init__(name=name, sensor_type="door", location=location)
        self.is_open = False

    def _read_raw(self):
        """Read the current door state (1.0 = open, 0.0 = closed)."""
        return 1.0 if self.is_open else 0.0

    def open(self):
        """Open the door."""
        print(f"Door {self.name} OPENED at t={time.time():.2f}")
        self.is_open = True

    def close(self):
        """Close the door."""
        print(f"Door {self.name} CLOSED at t={time.time():.2f}")
        self.is_open = False


class PersonSensor(Sensor):
    """A sensor that detects person presence."""

    def __init__(self, name, location=(0, 0, 0)):
        """Initialize the person sensor."""
        super().__init__(name=name, sensor_type="person", location=location)
        self.person_detected = False

    def _read_raw(self):
        """Read the current detection state (1.0 = person detected, 0.0 = no person)."""
        return 1.0 if self.person_detected else 0.0

    def detect(self):
        """Detect a person."""
        print(f"PERSON DETECTED by {self.name} at t={time.time():.2f}")
        self.person_detected = True

    def clear(self):
        """Clear the detection."""
        print(f"Person no longer detected by {self.name}")
        self.person_detected = False


# Create a simple global callback that will be triggered by the runtime
entry_detected = False


async def main():
    print("\nSequence Pattern Example: Door → Person → Door Close")
    print("----------------------------------------------------")
    print("This example detects the sequence: door open → person present → door close")
    print("When the pattern is detected within 10 seconds, it prints 'Entry detected'")

    # Create sensors
    door = DoorSensor("front_door", location=(0, 0, 0))
    person = PersonSensor("entry_area", location=(1, 1, 0))

    # Ensure initial state
    door.close()
    person.clear()

    # Create conditions based on sensor values
    door_open = Condition(lambda: door.read() > 0.5)
    person_present = Condition(lambda: person.read() > 0.5)
    door_closed = Condition(lambda: door.read() < 0.5)

    # Debug prints to check condition states
    print("\nInitial condition states:")
    print(f"door_open: {door_open.evaluate()}")
    print(f"person_present: {person_present.evaluate()}")
    print(f"door_closed: {door_closed.evaluate()}")

    # Create the sequence pattern
    entry_pattern = sequence(
        door_open,  # First: door opens
        person_present,  # Then: person is detected
        door_closed,  # Finally: door closes
        within_s=10.0,  # All within 10 seconds
    )

    # Define callback for when the sequence is detected
    global entry_detected

    @on(entry_pattern)
    def on_entry_detected():
        global entry_detected
        entry_detected = True
        print("\n🚨 ENTRY DETECTED! 🚨")
        print("Door opened → person detected → door closed within 10 seconds")

    # Start the runtime with very fast polling for demo purposes
    print("\nStarting runtime and waiting for events...\n")
    runtime_task = asyncio.create_task(start_runtime(poll_ms=50))

    try:
        await asyncio.sleep(1)  # Wait for runtime to initialize

        # Simulate our sequence
        print("\nSimulating sequence: door open → person detected → door closed")

        # Step 1: Open the door
        door.open()
        await asyncio.sleep(0.1)  # Add a small delay to ensure condition is evaluated
        print(
            f"After door open - door_open: {door_open.evaluate()}, door_closed: {door_closed.evaluate()}"
        )
        await asyncio.sleep(2)

        # Step 2: Detect a person
        person.detect()
        await asyncio.sleep(0.1)  # Add a small delay to ensure condition is evaluated
        print(f"After person detect - person_present: {person_present.evaluate()}")
        await asyncio.sleep(2)

        # Step 3: Close the door
        door.close()
        await asyncio.sleep(0.1)  # Add a small delay to ensure condition is evaluated
        print(
            f"After door close - door_open: {door_open.evaluate()}, door_closed: {door_closed.evaluate()}"
        )

        # Wait to see if the callback triggers
        print("\nWaiting for sequence detection...")
        for i in range(10):
            await asyncio.sleep(0.5)
            if entry_detected:
                break

        if entry_detected:
            print("Sequence successfully detected!")
        else:
            print("Sequence was not detected within the timeout period.")
            print(
                "Debug info: If all conditions evaluated correctly but the sequence wasn't detected,"
            )
            print("the issue might be with the sequence pattern implementation.")

        print("\nDemo complete.")

    finally:
        # Cleanup
        runtime_task.cancel()
        try:
            await runtime_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())

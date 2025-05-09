#!/usr/bin/env python3
"""
Sequence Pattern Example with Manual History: Entry Detection

This example demonstrates detecting a sequence of events:
doorOpen → personPresent → doorClose within 10 seconds
and prints "Entry detected" when this sequence occurs.

This version manually manages history to work around runtime limitations.
"""

import asyncio
import time
from collections import deque
from spaxiom import Sensor, Condition
from spaxiom.temporal import SequencePattern


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


async def main():
    print("\nSequence Pattern Example with Manual History: Door → Person → Door Close")
    print("------------------------------------------------------------------------")
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
    
    # Initialize sequence pattern
    pattern = SequencePattern(
        [door_open, person_present, door_closed],
        within_s=10.0
    )
    
    # Manually create history deques
    # Format: (timestamp, value)
    door_open_history = deque(maxlen=50)
    person_present_history = deque(maxlen=50)
    door_closed_history = deque(maxlen=50)
    
    # Add initial state to histories
    now = time.time()
    door_open_history.append((now, door_open.evaluate()))
    person_present_history.append((now, person_present.evaluate()))
    door_closed_history.append((now, door_closed.evaluate()))
    
    print("\nStarting the demo sequence...")
    
    # Simulate our sequence
    print("\nSimulating sequence: door open → person detected → door closed")
    
    # Step 1: Open the door
    door.open()
    now = time.time()
    # First add previous state
    door_open_history.append((now - 0.1, False))
    # Then add current state (transition to True)
    door_open_history.append((now, True))
    door_closed_history.append((now, False))
    print(f"  Added to door_open_history: {now:.2f}, {door_open.evaluate()}")
    
    await asyncio.sleep(2)
    
    # Step 2: Detect a person
    person.detect()
    now = time.time()
    # First add previous state
    person_present_history.append((now - 0.1, False))
    # Then add current state (transition to True)
    person_present_history.append((now, True))
    print(f"  Added to person_present_history: {now:.2f}, {person_present.evaluate()}")
    
    await asyncio.sleep(2)
    
    # Step 3: Close the door
    door.close()
    now = time.time()
    # First add previous state
    door_closed_history.append((now - 0.1, False))
    # Then add current state (transition to True)
    door_closed_history.append((now, True))
    door_open_history.append((now, False))
    print(f"  Added to door_closed_history: {now:.2f}, {door_closed.evaluate()}")
    
    await asyncio.sleep(0.5)
    
    # Manually evaluate the sequence pattern
    now = time.time()
    result = pattern.evaluate(now, [door_open_history, person_present_history, door_closed_history])
    
    if result:
        print("\n🚨 ENTRY DETECTED! 🚨")
        print("Door opened → person detected → door closed within 10 seconds")
    else:
        print("\nSequence pattern not detected.")
        print("Debug information:")
        print(f"  Current time: {now:.2f}")
        print("  Door open history:")
        for ts, val in door_open_history:
            print(f"    {ts:.2f}: {val}")
        print("  Person present history:")
        for ts, val in person_present_history:
            print(f"    {ts:.2f}: {val}")
        print("  Door closed history:")
        for ts, val in door_closed_history:
            print(f"    {ts:.2f}: {val}")
    
    print("\nDemo complete.")


if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
Occupancy Detection Demo for Spaxiom DSL.

This demonstrates:
1. Creating multiple sensor types (pressure and thermal)
2. Defining zones for occupancy detection
3. Creating complex logical conditions using &, |, and ~ operators
4. Using the within() function for sustained detection
5. Triggering events when occupancy conditions are met
"""

import os
import sys
import time
import random

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Condition, on, within, Zone
from spaxiom.sensor import RandomSensor


class OccupancySensor(RandomSensor):
    """
    A sensor that simulates occupancy detection with higher probability ranges.
    This allows more control over the randomness than the standard RandomSensor.
    """

    def __init__(self, name, sensor_type, location, active_probability=0.8):
        """
        Initialize the occupancy sensor.

        Args:
            name: Unique name for the sensor
            sensor_type: Type of sensor ("pressure" or "thermal")
            location: (x, y, z) coordinates
            active_probability: Probability of detecting presence (0.0-1.0)
        """
        super().__init__(name=name, location=location)
        self.sensor_type = sensor_type
        self.active_probability = active_probability

    def _read_raw(self):
        """
        Generate a simulated occupancy reading.

        Returns:
            1.0 if the sensor detects presence (based on probability), 0.0 otherwise
        """
        # Use a biased random generator to simulate occupancy
        if random.random() < self.active_probability:
            return 1.0
        return 0.0


def main():
    """Run the occupancy detection demo."""
    # Create zones
    zone_a = Zone(0, 0, 10, 10)  # Zone A (e.g., office area)
    zone_b = Zone(15, 0, 25, 10)  # Zone B (e.g., hallway)

    print("\nSpaxiom Occupancy Detection Demo")
    print("--------------------------------")
    print(f"Zone A: {zone_a}")
    print(f"Zone B: {zone_b}")
    print()
    print("Setting up sensors in zones A and B...")

    # Create sensors in zone A
    pressure_a = OccupancySensor(
        name="pressure_A",
        sensor_type="pressure",
        location=(5, 5, 0),  # Center of Zone A
        active_probability=0.7,  # 70% chance of detecting pressure when occupied
    )

    thermal_a = OccupancySensor(
        name="thermal_A",
        sensor_type="thermal",
        location=(5, 5, 0),  # Center of Zone A
        active_probability=0.8,  # 80% chance of detecting heat when occupied
    )

    # Create a sensor in zone B
    pressure_b = OccupancySensor(
        name="pressure_B",
        sensor_type="pressure",
        location=(20, 5, 0),  # Center of Zone B
        active_probability=0.6,  # 60% chance of detecting pressure when occupied
    )

    print("Sensors initialized:")
    print(f"  {pressure_a}")
    print(f"  {thermal_a}")
    print(f"  {pressure_b}")
    print()

    # Define conditions for each sensor
    pressure_a_active = Condition(lambda: pressure_a.read() > 0.5)
    thermal_a_active = Condition(lambda: thermal_a.read() > 0.5)
    pressure_b_active = Condition(lambda: pressure_b.read() > 0.5)

    # Define complex condition: person_in_A = pressureA & thermalA & ~pressureB
    # This indicates someone is in zone A (both pressure and thermal detect)
    # but not in zone B (no pressure detected in B)
    person_in_a = pressure_a_active & thermal_a_active & ~pressure_b_active

    # Create a temporal condition - must be true for at least 1 second
    person_in_a_sustained = within(1.0, person_in_a)

    # Register callback function for sustained occupancy
    @on(person_in_a_sustained)
    def notify_occupancy():
        print("\033[1;32m** ZONE A OCCUPIED **\033[0m")

    # Print instructions
    print("Starting occupancy monitoring...")
    print("The message '** ZONE A OCCUPIED **' will appear when:")
    print("  1. Pressure is detected in Zone A")
    print("  2. Thermal signature is detected in Zone A")
    print("  3. No pressure is detected in Zone B")
    print("  4. These conditions remain true for at least 1 second")
    print()
    print("Press Ctrl+C to exit")
    print()

    # Start the event loop
    try:
        while True:
            # Manually evaluate the conditions and print sensor states
            p_a = pressure_a.read() > 0.5
            t_a = thermal_a.read() > 0.5
            p_b = pressure_b.read() > 0.5

            # Print current sensor states
            print(
                f"Pressure A: {'ON' if p_a else 'off'} | "
                f"Thermal A: {'ON' if t_a else 'off'} | "
                f"Pressure B: {'ON' if p_b else 'off'} | "
                f"Occupancy Condition: {'TRUE' if p_a and t_a and not p_b else 'false'}",
                end="\r",
            )

            # Process events
            from spaxiom.events import process_events

            process_events()

            # Wait before next update
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\nExiting occupancy detection demo.")


if __name__ == "__main__":
    main()

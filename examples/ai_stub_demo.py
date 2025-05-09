#!/usr/bin/env python3
"""
AI Stub Demo for Spaxiom DSL.

This demonstrates:
1. Creating a random sensor that simulates data input
2. Creating a stub AI model with a specific detection probability
3. Using the exists() function to check for positive detections
4. Using the on() decorator to trigger actions on detections
"""

import os
import sys
import time
import asyncio

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import on, exists, EntitySet, Entity, StubModel
from spaxiom.runtime import start_runtime
from spaxiom.sensor import RandomSensor


class PersonDetector:
    """
    A class that simulates person detection using a random sensor and stub model.
    """

    def __init__(self, detection_probability=0.2, sensor_location=(0, 0, 0)):
        """
        Initialize the person detector.

        Args:
            detection_probability: Probability of detecting a person (0.0-1.0)
            sensor_location: 3D location of the sensor
        """
        # Create a sensor that generates random values
        self.sensor = RandomSensor(name="camera", location=sensor_location)

        # Create a stub model that simulates person detection
        self.model = StubModel(
            name="person_detector", probability=detection_probability
        )

        # Create an entity set to store detected persons
        self.persons = EntitySet("Persons")

        # Track the last detection time to avoid too frequent detections
        self.last_detection_time = 0

    def update(self):
        """
        Update the detector by reading sensor data and running inference.
        Creates a new person entity when a detection occurs.
        """
        # Read data from the sensor
        sensor_data = self.sensor.read()

        # Run the model on the sensor data
        # (model accepts args but ignores them, just using probability)
        is_person_detected = self.model.predict(sensor_data)

        # If a person is detected, add it to the entity set
        # Only add a new detection every 2 seconds to avoid spam
        current_time = time.time()
        if is_person_detected and current_time - self.last_detection_time > 2.0:
            # Create a new person entity with a confidence score
            person = Entity(
                attrs={
                    "type": "person",
                    "confidence": 0.8 + 0.2 * sensor_data,  # Randomize confidence a bit
                    "timestamp": current_time,
                }
            )

            # Add to the entity set
            self.persons.add(person)

            # Update the last detection time
            self.last_detection_time = current_time

            # Print detection information
            print(f"Person detected! Confidence: {person.attrs['confidence']:.2f}")

        # Remove old detections (older than 5 seconds)
        for person in list(self.persons):
            if current_time - person.attrs["timestamp"] > 5.0:
                self.persons.remove(person)


def main():
    """Run the person detection demo."""
    # Create a person detector
    detector = PersonDetector(detection_probability=0.1)

    # Create a condition that checks if any persons are detected
    person_detected = exists(detector.persons)

    # Register a callback for when a person is detected
    @on(person_detected)
    def alert_person():
        print("PERSON!")

    # Print some info
    print("Spaxiom AI Stub Demo")
    print("--------------------")
    print("Using a RandomSensor and StubModel to simulate person detection")
    print("The model has a 10% chance of detecting a person on each frame")
    print("When a person is detected, it's added to the Persons entity set")
    print("The condition fires when at least one person is in the entity set")
    print("Press Ctrl+C to exit")
    print()

    # Define a custom update loop that updates our detector
    async def custom_update_loop():
        try:
            while True:
                detector.update()
                await asyncio.sleep(0.1)  # Update at 10 Hz
        except asyncio.CancelledError:
            pass

    # Start the custom update loop
    update_task = None

    try:
        # Start the runtime which processes events
        loop = asyncio.get_event_loop()
        update_task = loop.create_task(custom_update_loop())
        asyncio.run(start_runtime(poll_ms=100))
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    finally:
        # Make sure to clean up
        if update_task and not update_task.done():
            update_task.cancel()


if __name__ == "__main__":
    main()

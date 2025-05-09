#!/usr/bin/env python3
"""
Person Detection Demo using ONNX Model for Spaxiom DSL.

This demonstrates:
1. Creating a RandomSensor that simulates camera input
2. Loading an ONNX model for person detection
3. Using the OnnxModel with sensor data
4. Creating conditions based on model predictions
5. Triggering events when a person is detected
"""

import os
import sys
import time
import numpy as np

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Sensor, Condition, on, OnnxModel


class ImageSensor(Sensor):
    """
    A sensor that simulates camera input by generating random image data.
    """

    def __init__(self, name, location=(0, 0, 0), image_shape=(1, 3, 224, 224)):
        """
        Initialize the image sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            image_shape: Shape of the image tensor (batch, channels, height, width)
        """
        super().__init__(name=name, sensor_type="camera", location=location)
        self.image_shape = image_shape
        self.frame_count = 0

        # Simulate a person appearing every 5 frames
        self.person_frequency = 5

        # Print initialization message
        print(f"Image sensor {name} initialized at {location} with shape {image_shape}")

    def _read_raw(self):
        """
        Generate a simulated camera image.

        Returns:
            A numpy array representing an image with the configured shape
        """
        # Increment frame counter
        self.frame_count += 1

        # Generate random image data (normalized between 0-1)
        image = np.random.random(self.image_shape).astype(np.float32)

        # For demonstration purposes, print frame information
        person_present = self.frame_count % self.person_frequency == 0
        print(
            f"Frame {self.frame_count}: {'Person simulated' if person_present else 'No person'}"
        )

        return image


class MockPersonDetectionModel(OnnxModel):
    """
    A mock ONNX model for person detection that pretends to load from a file
    but actually generates simulated results.
    """

    def __init__(self, name="person_detection", path="persondet.onnx"):
        """
        Initialize the mock person detection model.

        Args:
            name: Name of the model
            path: Pretend path to the ONNX model file (not actually used)
        """
        # Initialize with standard input names for an image model
        super().__init__(name=name, path=path, input_names=["image"])
        print(f"Person detection model initialized (pretending to load {path})")

        # Override the _ensure_session method to avoid actually loading a file
        self._session_loaded = False

    def _ensure_session(self):
        """Override to simulate session loading without actually loading a file."""
        if not self._session_loaded:
            print("Loading person detection model...")
            time.sleep(0.5)  # Simulate loading time
            self._session_loaded = True
            print("Person detection model loaded")

    def predict(self, **named_arrays):
        """
        Simulate running inference on the person detection model.

        Args:
            **named_arrays: Input tensors as numpy arrays

        Returns:
            A simulated detection result where:
            - [0] = no person detected
            - [1] = person detected
        """
        # Ensure 'image' input is provided
        if "image" not in named_arrays:
            raise ValueError("Missing required input: 'image'")

        # Simulate session loading if needed
        self._ensure_session()

        # For this demo, we'll simulate a person detection based on the
        # frame count of our image sensor (known via closure)
        frame_number = image_sensor.frame_count

        # Simulate detecting a person every X frames
        person_detected = frame_number % image_sensor.person_frequency == 0

        # Create and return a simulated confidence score
        # [class_id, confidence, x1, y1, x2, y2]
        if person_detected:
            # Person detected with high confidence
            return np.array([[1, 0.92, 0.2, 0.3, 0.5, 0.7]])
        else:
            # No person or low confidence
            return np.array([[0, 0.15, 0, 0, 0, 0]])


def main():
    """Run the person detection demo."""
    global image_sensor

    print("\nSpaxiom ONNX Person Detection Demo")
    print("===================================")
    print("This demo simulates:")
    print("1. A camera sensor generating image frames")
    print("2. An ONNX model for person detection")
    print("3. Events triggered when a person is detected\n")

    # Create the image sensor
    image_sensor = ImageSensor("main_camera", location=(0, 0, 1))

    # Create the person detection model
    person_model = MockPersonDetectionModel()

    # Define a condition based on model prediction
    # A person is detected if the confidence score is > 0.5
    def detect_person():
        # Read the image from the sensor
        image = image_sensor.read()

        # Run the model
        detections = person_model.predict(image=image)

        # Check if any detection has confidence > 0.5
        return len(detections) > 0 and detections[0][1] > 0.5

    # Create a condition from the detection function
    person_detected = Condition(detect_person)

    # Register a callback when a person is detected
    @on(person_detected)
    def alert_person():
        print("\033[1;32m🚨 PERSON DETECTED! 🚨\033[0m")

    # Print instructions
    print("Starting person detection...\n")
    print("Press Ctrl+C to exit\n")

    # Start the event loop
    try:
        while True:
            # Process events
            from spaxiom.events import process_events

            process_events()

            # Wait before next frame
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nExiting person detection demo.")


if __name__ == "__main__":
    main()

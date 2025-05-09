#!/usr/bin/env python3
"""
Fusion Demo script for Spaxiom DSL.

This demonstrates:
1. Creating multiple sensor sources with varying noise levels
2. Using the WeightedFusion class to combine them with appropriate weights
3. Showing how weighted fusion provides more reliable readings
"""

import time
import numpy as np
from spaxiom import Sensor, WeightedFusion


class NoisySensor(Sensor):
    """A sensor that returns a value with added noise."""

    def __init__(
        self, name, location, true_value=10.0, noise_stddev=1.0, metadata=None
    ):
        """
        Initialize a noisy sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            true_value: The underlying true value that the sensor is measuring
            noise_stddev: Standard deviation of the Gaussian noise to add
            metadata: Optional metadata dictionary
        """
        super().__init__(
            name=name,
            sensor_type="noisy",
            location=location,
            metadata=metadata or {"noise_level": noise_stddev},
        )
        self.true_value = true_value
        self.noise_stddev = noise_stddev

    def _read_raw(self):
        """
        Read the sensor value with added noise.

        Returns:
            The true value plus Gaussian noise
        """
        # Add Gaussian noise to the true value
        noise = np.random.normal(0, self.noise_stddev)
        return self.true_value + noise

    def __repr__(self):
        return f"NoisySensor(name='{self.name}', noise_level={self.noise_stddev})"


def main():
    # Fixed "ground truth" value that all sensors are trying to measure
    GROUND_TRUTH = 25.0

    print("Spaxiom Fusion Demo")
    print("------------------")
    print(f"Ground truth value: {GROUND_TRUTH}")
    print()

    # Create three sensors with different noise levels at different locations
    s1 = NoisySensor(
        name="low_noise",
        location=(0, 0, 0),
        true_value=GROUND_TRUTH,
        noise_stddev=0.5,  # Low noise sensor (most reliable)
    )

    s2 = NoisySensor(
        name="medium_noise",
        location=(10, 0, 0),
        true_value=GROUND_TRUTH,
        noise_stddev=2.0,  # Medium noise sensor
    )

    s3 = NoisySensor(
        name="high_noise",
        location=(0, 10, 0),
        true_value=GROUND_TRUTH,
        noise_stddev=5.0,  # High noise sensor (least reliable)
    )

    # Create a fusion sensor with weights inversely proportional to noise levels
    # The most reliable sensors get the highest weights
    fusion = WeightedFusion(
        name="fused_sensor",
        sensors=[s1, s2, s3],
        # Weights inversely proportional to variance (squared standard deviation)
        weights=[
            1 / (s1.noise_stddev**2),
            1 / (s2.noise_stddev**2),
            1 / (s3.noise_stddev**2),
        ],
    )

    # Create a simple average fusion (equal weights) for comparison
    simple_average = WeightedFusion(
        name="simple_average", sensors=[s1, s2, s3], weights=[1.0, 1.0, 1.0]
    )

    # Manual simulation loop to compare readings
    print("Starting simulation...")
    print("(Press Ctrl+C to exit)")
    print()

    try:
        # Print header
        print(
            f"{'Time':^8} | {'Low Noise':^10} | {'Medium Noise':^12} | {'High Noise':^10} | {'Simple Avg':^10} | {'Weighted':^10} | {'Error':^10}"
        )
        print("-" * 85)

        start_time = time.time()
        while True:
            # Read all sensors
            v1 = s1.read()
            v2 = s2.read()
            v3 = s3.read()

            # Read fusion sensors
            weighted_value = fusion.read()
            simple_avg = simple_average.read()

            # Calculate error from ground truth for weighted fusion
            error = abs(weighted_value - GROUND_TRUTH)

            # Print current readings
            elapsed = time.time() - start_time
            print(
                f"{elapsed:6.1f}s | {v1:10.2f} | {v2:12.2f} | {v3:10.2f} | {simple_avg:10.2f} | {weighted_value:10.2f} | {error:10.2f}"
            )

            # Slow down the loop
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user")


if __name__ == "__main__":
    main()

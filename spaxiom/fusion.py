"""
Fusion module for sensor data fusion in Spaxiom DSL.
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Literal
import numpy as np

from spaxiom.core import Sensor


def weighted_average(readings: List[float], weights: List[float]) -> float:
    """
    Compute a weighted average of the given readings.

    Args:
        readings: List of numeric readings
        weights: List of weights corresponding to each reading

    Returns:
        Weighted average of the readings

    Raises:
        ValueError: If readings and weights have different lengths,
                   if weights sum to zero, or if either list is empty
    """
    # Sanity checks
    if not readings:
        raise ValueError("Readings list cannot be empty")

    if not weights:
        raise ValueError("Weights list cannot be empty")

    if len(readings) != len(weights):
        raise ValueError(
            f"Readings list (len={len(readings)}) and weights list (len={len(weights)}) must have the same length"
        )

    # Convert to numpy arrays for vectorized operations
    readings_array = np.array(readings, dtype=float)
    weights_array = np.array(weights, dtype=float)

    # Ensure weights sum to a non-zero value
    weights_sum = np.sum(weights_array)
    if np.isclose(weights_sum, 0.0):
        raise ValueError("Sum of weights cannot be zero")

    # Compute weighted average (weights * readings, then sum, then divide by sum of weights)
    weighted_sum = np.sum(readings_array * weights_array)
    return float(weighted_sum / weights_sum)


class WeightedFusion(Sensor):
    """
    A sensor that fuses multiple sensor readings using weighted averaging.

    Attributes:
        name: Name of the fusion sensor
        sensors: List of sensors to fuse
        weights: List of weights for each sensor
        location: Location of the fusion sensor (defaults to centroid of component sensors)
        privacy: Privacy level of the fusion sensor ('public' or 'private')
    """

    def __init__(
        self,
        name: str,
        sensors: List[Sensor],
        weights: List[float],
        location: Optional[Tuple[float, float, float]] = None,
        privacy: Literal["public", "private"] = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a weighted fusion sensor.

        Args:
            name: Unique name for the fusion sensor
            sensors: List of sensors to fuse
            weights: List of weights for each sensor
            location: Optional location override (if None, uses centroid of component sensors)
            privacy: Privacy level of the fusion sensor ('public' or 'private')
            metadata: Optional metadata dictionary

        Raises:
            ValueError: If sensors and weights lists have different lengths or if either is empty
        """
        # Sanity checks
        if not sensors:
            raise ValueError("Sensors list cannot be empty")

        if not weights:
            raise ValueError("Weights list cannot be empty")

        if len(sensors) != len(weights):
            raise ValueError(
                f"Sensors list (len={len(sensors)}) and weights list (len={len(weights)}) must have the same length"
            )

        # Store sensors and weights before super().__init__ to avoid AttributeError in __repr__
        self.sensors = sensors
        self.weights = weights

        # Calculate centroid location if not provided
        if location is None:
            # Extract locations from all sensors
            sensor_locations = np.array([sensor.location for sensor in sensors])
            # Compute centroid
            location = tuple(np.mean(sensor_locations, axis=0).tolist())

        # Check if any component sensors are private
        # If any component sensor is private, the fusion should be private too
        derived_privacy = privacy
        if any(sensor.privacy == "private" for sensor in sensors):
            derived_privacy = "private"

        # Initialize parent class
        super().__init__(
            name=name,
            sensor_type="weighted_fusion",
            location=location,
            privacy=derived_privacy,
            metadata=metadata or {},
        )

    def _read_raw(self) -> Union[float, None]:
        """
        Read values from all component sensors and compute weighted average.

        Returns:
            Weighted average of sensor readings

        Raises:
            ValueError: If any sensor returns None or a non-numeric value
        """
        # Collect readings from all sensors
        readings = []
        for sensor in self.sensors:
            value = sensor.read()

            # Validate sensor reading
            if value is None:
                raise ValueError(f"Sensor {sensor.name} returned None")

            try:
                readings.append(float(value))
            except (ValueError, TypeError):
                raise ValueError(
                    f"Sensor {sensor.name} returned non-numeric value: {value}"
                )

        # Compute weighted average
        return weighted_average(readings, self.weights)

    def __repr__(self) -> str:
        """Return string representation of the fusion sensor."""
        sensor_names = [s.name for s in self.sensors]
        return f"WeightedFusion(name='{self.name}', sensors={sensor_names}, weights={self.weights}, privacy='{self.privacy}')"

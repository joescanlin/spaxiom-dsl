"""
Tests for the sensor fusion mixin in Spaxiom DSL.
"""

import pytest
import uuid
from spaxiom.sensor import Sensor
from spaxiom.fusion import WeightedFusion


class MockSensor(Sensor):
    """Mock sensor for testing."""

    def __init__(self, name, value, location=(0, 0, 0)):
        # Generate a unique name to avoid registry conflicts
        unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
        # Skip the registry by not calling post_init
        self.name = unique_name
        self.sensor_type = "mock"
        self.location = location
        self.metadata = None
        self.value = value

    def _read_raw(self):
        """Return the predefined value."""
        return self.value


class TestSensorFusionMixin:
    """Test cases for the Sensor.fuse_with method."""

    def test_fuse_with_average_strategy(self):
        """Test fusing two sensors using the 'average' strategy."""
        # Create mock sensors
        s1 = MockSensor("sensor1", 10.0, location=(0, 0, 0))
        s2 = MockSensor("sensor2", 20.0, location=(10, 10, 10))

        # Fuse sensors with average strategy
        fusion = s1.fuse_with(s2, strategy="average")

        # Verify fusion sensor properties
        assert isinstance(fusion, WeightedFusion)
        assert len(fusion.sensors) == 2
        assert fusion.sensors[0] == s1
        assert fusion.sensors[1] == s2
        assert fusion.weights == [1.0, 1.0]

        # Test fusion result (should be simple average)
        assert fusion.read() == pytest.approx(15.0)

        # Verify that location is calculated automatically (centroid)
        assert fusion.location == pytest.approx((5.0, 5.0, 5.0))

    def test_fuse_with_weighted_strategy(self):
        """Test fusing two sensors using the 'weighted' strategy."""
        # Create mock sensors
        s1 = MockSensor("sensor1", 10.0)
        s2 = MockSensor("sensor2", 20.0)

        # Custom weights
        weights = [0.75, 0.25]

        # Fuse sensors with weighted strategy
        fusion = s1.fuse_with(s2, strategy="weighted", weights=weights)

        # Verify fusion sensor properties
        assert isinstance(fusion, WeightedFusion)
        assert fusion.weights == weights

        # Verify weights are applied correctly: (10*0.75 + 20*0.25)/(0.75+0.25) = 12.5
        assert fusion.read() == pytest.approx(12.5)

    def test_fuse_with_custom_name_and_location(self):
        """Test fusing with custom name and location."""
        s1 = MockSensor("sensor1", 10.0)
        s2 = MockSensor("sensor2", 20.0)

        custom_name = "my_custom_fusion"
        custom_location = (100, 200, 300)

        fusion = s1.fuse_with(
            s2, strategy="average", name=custom_name, location=custom_location
        )

        assert fusion.name == custom_name
        assert fusion.location == custom_location

    def test_fuse_with_invalid_strategy(self):
        """Test that invalid strategy raises ValueError."""
        s1 = MockSensor("sensor1", 10.0)
        s2 = MockSensor("sensor2", 20.0)

        with pytest.raises(ValueError):
            s1.fuse_with(s2, strategy="invalid_strategy")

    def test_fuse_with_invalid_weights_count(self):
        """Test that providing wrong number of weights raises ValueError."""
        s1 = MockSensor("sensor1", 10.0)
        s2 = MockSensor("sensor2", 20.0)

        with pytest.raises(ValueError):
            s1.fuse_with(
                s2, strategy="weighted", weights=[0.5, 0.3, 0.2]
            )  # 3 weights instead of 2

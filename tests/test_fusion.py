"""
Tests for the fusion module in Spaxiom DSL.
"""

import pytest
import uuid
from spaxiom.fusion import weighted_average, WeightedFusion
from spaxiom.sensor import Sensor


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


# Helper to generate unique fusion names
def unique_fusion_name():
    """Generate a unique fusion sensor name for testing."""
    return f"fusion_{uuid.uuid4().hex[:8]}"


class TestWeightedAverage:
    """Test cases for the weighted_average function."""

    def test_basic_weighted_average(self):
        """Test basic weighted averaging."""
        readings = [10.0, 20.0, 30.0]
        weights = [1.0, 1.0, 1.0]

        # With equal weights, should be the same as simple average
        result = weighted_average(readings, weights)
        assert result == pytest.approx(20.0)

    def test_weighted_average_with_unequal_weights(self):
        """Test weighted averaging with unequal weights."""
        readings = [10.0, 20.0, 30.0]
        weights = [1.0, 2.0, 3.0]

        # Manual calculation: (10*1 + 20*2 + 30*3) / (1+2+3) = 130 / 6 = 21.667
        expected = (10 * 1 + 20 * 2 + 30 * 3) / (1 + 2 + 3)  # = 130 / 6 = 21.667
        result = weighted_average(readings, weights)
        assert result == pytest.approx(expected, abs=1e-4)

    def test_weighted_average_with_normalized_weights(self):
        """Test weighted averaging with already normalized weights."""
        readings = [10.0, 20.0, 30.0, 40.0]
        weights = [0.1, 0.2, 0.3, 0.4]  # Sum = 1.0

        # Manual calculation: 10*0.1 + 20*0.2 + 30*0.3 + 40*0.4 = 30
        result = weighted_average(readings, weights)
        assert result == pytest.approx(30.0)

    def test_weighted_average_with_single_value(self):
        """Test weighted averaging with a single value."""
        readings = [42.0]
        weights = [1.0]

        result = weighted_average(readings, weights)
        assert result == pytest.approx(42.0)

    def test_error_on_empty_lists(self):
        """Test that empty lists raise ValueError."""
        with pytest.raises(ValueError):
            weighted_average([], [1.0, 2.0])

        with pytest.raises(ValueError):
            weighted_average([1.0, 2.0], [])

    def test_error_on_mismatched_lengths(self):
        """Test that mismatched list lengths raise ValueError."""
        with pytest.raises(ValueError):
            weighted_average([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_error_on_zero_weight_sum(self):
        """Test that zero sum of weights raises ValueError."""
        with pytest.raises(ValueError):
            weighted_average([1.0, 2.0, 3.0], [1.0, -1.0, 0.0])


class TestWeightedFusion:
    """Test cases for the WeightedFusion class."""

    def test_basic_fusion(self):
        """Test basic sensor fusion with equal weights."""
        # Create mock sensors with fixed values
        sensors = [
            MockSensor("s1", 10.0, location=(0, 0, 0)),
            MockSensor("s2", 20.0, location=(1, 1, 1)),
            MockSensor("s3", 30.0, location=(2, 2, 2)),
        ]

        weights = [1.0, 1.0, 1.0]

        # Create fusion sensor with unique name
        fusion = WeightedFusion(unique_fusion_name(), sensors, weights)

        # Test read value (should be average of all sensors)
        assert fusion.read() == pytest.approx(20.0)

        # Test default location (should be centroid of sensor locations)
        assert fusion.location == pytest.approx((1.0, 1.0, 1.0))

    def test_fusion_two_stub_sensors_equal_weights(self):
        """Test fusing exactly two sensors with fixed values 10 and 20 using equal weights."""
        # Create two sensors with fixed values 10 and 20
        sensor1 = MockSensor("stub1", 10.0)
        sensor2 = MockSensor("stub2", 20.0)

        # Create fusion with equal weights (1.0 for each)
        fusion = WeightedFusion(
            unique_fusion_name(), sensors=[sensor1, sensor2], weights=[1.0, 1.0]
        )

        # With equal weights, result should be exactly 15.0
        assert fusion.read() == pytest.approx(15.0)

        # Also verify that weights are properly set
        assert fusion.weights == [1.0, 1.0]
        assert len(fusion.sensors) == 2
        assert fusion.sensors[0] == sensor1
        assert fusion.sensors[1] == sensor2

    def test_fusion_with_custom_weights(self):
        """Test sensor fusion with custom weights."""
        # Create mock sensors with fixed values
        sensors = [
            MockSensor("s1", 10.0),
            MockSensor("s2", 20.0),
            MockSensor("s3", 30.0),
        ]

        weights = [1.0, 2.0, 3.0]

        # Create fusion sensor with unique name
        fusion = WeightedFusion(unique_fusion_name(), sensors, weights)

        # Manual calculation: (10*1 + 20*2 + 30*3) / (1+2+3) = 130 / 6 = 21.667
        expected = (10 * 1 + 20 * 2 + 30 * 3) / (1 + 2 + 3)  # = 130 / 6 = 21.667
        assert fusion.read() == pytest.approx(expected, abs=1e-4)

    def test_fusion_with_custom_location(self):
        """Test sensor fusion with custom location override."""
        sensors = [
            MockSensor("s1", 10.0, location=(0, 0, 0)),
            MockSensor("s2", 20.0, location=(10, 10, 10)),
        ]

        custom_location = (5, 5, 5)

        # Create fusion sensor with unique name and custom location
        fusion = WeightedFusion(
            unique_fusion_name(), sensors, [1.0, 1.0], location=custom_location
        )

        # Location should be the custom one, not the centroid
        assert fusion.location == custom_location

    def test_error_on_empty_sensors(self):
        """Test that empty sensors list raises ValueError."""
        with pytest.raises(ValueError):
            WeightedFusion(unique_fusion_name(), [], [1.0])

    def test_error_on_empty_weights(self):
        """Test that empty weights list raises ValueError."""
        sensors = [MockSensor("s1", 10.0)]

        with pytest.raises(ValueError):
            WeightedFusion(unique_fusion_name(), sensors, [])

    def test_error_on_mismatched_lengths(self):
        """Test that mismatched list lengths raise ValueError."""
        sensors = [
            MockSensor("s1", 10.0),
            MockSensor("s2", 20.0),
        ]

        weights = [1.0, 2.0, 3.0]

        with pytest.raises(ValueError):
            WeightedFusion(unique_fusion_name(), sensors, weights)

    def test_repr(self):
        """Test string representation of fusion sensor."""
        sensors = [
            MockSensor("s1", 10.0),
            MockSensor("s2", 20.0),
        ]

        weights = [1.0, 2.0]

        fusion_name = unique_fusion_name()
        fusion = WeightedFusion(fusion_name, sensors, weights)

        # Check that repr contains important information
        repr_str = repr(fusion)
        assert "WeightedFusion" in repr_str
        assert fusion_name in repr_str
        assert "weights" in repr_str

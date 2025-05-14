"""
Tests for the SimVector module.
"""

import unittest
from unittest.mock import patch

from spaxiom.sim.vec_sim import SimVector, SimSensor
from spaxiom.core import SensorRegistry


class TestSimVector(unittest.TestCase):
    """Test the SimVector class for simulating multiple sensors."""

    def setUp(self):
        """Set up for each test."""
        # Clear the sensor registry before each test
        SensorRegistry().clear()

        # Patch numpy.random.uniform to return predictable values
        self.random_patch = patch("numpy.random.uniform")
        self.mock_random = self.random_patch.start()

        # We'll need at least 3 sets of random values for our tests
        # Each sensor needs 4 values: frequency, amplitude, phase, offset
        # For n=5 sensors, we need 20 values
        random_values = []
        for i in range(30):  # More than enough for all tests
            random_values.extend(
                [0.2, 1.0, 0.5, 0.0]
            )  # frequency, amplitude, phase, offset

        self.mock_random.side_effect = random_values

    def tearDown(self):
        """Clean up after each test."""
        self.random_patch.stop()
        SensorRegistry().clear()

    def test_init_and_properties(self):
        """Test initialization and basic properties."""
        # Create a SimVector
        sim_vec = SimVector(
            n=3, hz=10.0, name_prefix="test", base_location=(1.0, 2.0, 3.0), spacing=2.0
        )

        # Check basic properties
        self.assertEqual(3, len(sim_vec))
        self.assertEqual(3, len(sim_vec.sensors))
        self.assertEqual(10.0, sim_vec.hz)
        self.assertEqual(0.1, sim_vec.update_period)
        self.assertFalse(sim_vec.running)

        # Check sensor properties
        for i, sensor in enumerate(sim_vec.sensors):
            self.assertEqual(f"test_{i}", sensor.name)
            self.assertEqual((1.0 + i * 2.0, 2.0, 3.0), sensor.location)
            self.assertEqual("sim", sensor.sensor_type)
            self.assertEqual("public", sensor.privacy)

    def test_getitem(self):
        """Test the __getitem__ method."""
        sim_vec = SimVector(n=5, hz=10.0)

        # Access sensors by index
        sensor0 = sim_vec[0]
        sensor3 = sim_vec[3]

        self.assertEqual("sim_0", sensor0.name)
        self.assertEqual("sim_3", sensor3.name)

        # Test index out of range
        with self.assertRaises(IndexError):
            _ = sim_vec[10]

    def test_len(self):
        """Test the __len__ method."""
        sim_vec = SimVector(n=7, hz=10.0)
        self.assertEqual(7, len(sim_vec))

    def test_repr(self):
        """Test the __repr__ method."""
        sim_vec = SimVector(n=3, hz=5.0)
        repr_str = repr(sim_vec)

        self.assertIn("SimVector", repr_str)
        self.assertIn("n=3", repr_str)
        self.assertIn("hz=5.0", repr_str)
        self.assertIn("running=False", repr_str)

    @patch("threading.Thread")
    @patch("time.time")
    def test_start_and_stop(self, mock_time, mock_thread):
        """Test starting and stopping the simulation."""
        # Mock time.time to return a fixed value
        mock_time.return_value = 100.0

        # Create SimVector
        sim_vec = SimVector(n=2, hz=20.0)

        # Start the simulation
        sim_vec.start()

        # Verify thread was started
        self.assertTrue(sim_vec.running)
        self.assertEqual(100.0, sim_vec._start_time)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

        # Call start again - should do nothing since already running
        sim_vec.start()
        # Thread should still only be created once
        mock_thread.assert_called_once()

        # Now stop
        sim_vec.stop()
        self.assertFalse(sim_vec.running)


class TestSimSensor(unittest.TestCase):
    """Test the SimSensor class."""

    def setUp(self):
        """Setup the test."""
        # Clear the sensor registry
        SensorRegistry().clear()

    def tearDown(self):
        """Clean up after each test."""
        SensorRegistry().clear()

    def test_init(self):
        """Test initialization."""
        sensor = SimSensor(
            name="test_sensor",
            location=(1.0, 2.0, 3.0),
            frequency=0.5,
            amplitude=2.0,
            phase=1.0,
            offset=0.5,
            privacy="private",
        )

        # Check attributes
        self.assertEqual("test_sensor", sensor.name)
        self.assertEqual((1.0, 2.0, 3.0), sensor.location)
        self.assertEqual("sim", sensor.sensor_type)
        self.assertEqual("private", sensor.privacy)
        self.assertEqual(0.5, sensor.frequency)
        self.assertEqual(2.0, sensor.amplitude)
        self.assertEqual(1.0, sensor.phase)
        self.assertEqual(0.5, sensor.offset)
        self.assertEqual(0.5, sensor.current_value)  # Should default to offset

    def test_read_raw(self):
        """Test the _read_raw method."""
        sensor = SimSensor(
            name="read_test", location=(0, 0, 0), frequency=1.0, amplitude=1.0
        )

        # Set a value and read it
        sensor.current_value = 0.75
        self.assertEqual(0.75, sensor._read_raw())

    def test_calculate_value(self):
        """Test the calculate_value method."""
        sensor = SimSensor(
            name="calc_test",
            location=(0, 0, 0),
            frequency=1.0,  # 1 Hz
            amplitude=2.0,
            phase=0.0,  # No phase shift
            offset=1.0,
        )

        # At t=0, sin(0) = 0, so value should be offset
        self.assertEqual(1.0, sensor.calculate_value(0.0))

        # At t=0.25s with 1Hz, sin(π/2) = 1, so value should be offset + amplitude
        self.assertAlmostEqual(3.0, sensor.calculate_value(0.25), places=6)

        # At t=0.5s with 1Hz, sin(π) = 0, so value should be offset
        self.assertAlmostEqual(1.0, sensor.calculate_value(0.5), places=6)

        # At t=0.75s with 1Hz, sin(3π/2) = -1, so value should be offset - amplitude
        self.assertAlmostEqual(-1.0, sensor.calculate_value(0.75), places=6)

    def test_repr(self):
        """Test the __repr__ method."""
        sensor = SimSensor(
            name="repr_test", location=(5, 6, 7), frequency=2.5, amplitude=1.5
        )

        repr_str = repr(sensor)
        self.assertIn("SimSensor", repr_str)
        self.assertIn("name='repr_test'", repr_str)
        self.assertIn("frequency=2.5", repr_str)
        self.assertIn("amplitude=1.5", repr_str)
        self.assertIn("location=(5, 6, 7)", repr_str)


if __name__ == "__main__":
    unittest.main()

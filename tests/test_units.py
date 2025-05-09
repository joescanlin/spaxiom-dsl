"""
Unit tests for the units module.
"""

import unittest
from spaxiom import Quantity
from spaxiom.sensor import Sensor


class TestUnits(unittest.TestCase):
    """Test suite for the units module."""

    def test_basic_quantity_creation(self):
        """Test creating basic quantities with different units."""
        length = Quantity(10, "m")
        self.assertEqual(length.magnitude, 10)
        self.assertEqual(str(length.units), "meter")

        mass = Quantity(5, "kg")
        self.assertEqual(mass.magnitude, 5)
        self.assertEqual(str(mass.units), "kilogram")

        time = Quantity(2, "s")
        self.assertEqual(time.magnitude, 2)
        self.assertEqual(str(time.units), "second")

    def test_unit_conversion(self):
        """Test converting between different units."""
        length = Quantity(1, "m")
        length_in_cm = length.to("cm")
        self.assertEqual(length_in_cm.magnitude, 100)
        self.assertEqual(str(length_in_cm.units), "centimeter")

        mass = Quantity(1, "kg")
        mass_in_g = mass.to("g")
        self.assertEqual(mass_in_g.magnitude, 1000)
        self.assertEqual(str(mass_in_g.units), "gram")

        time = Quantity(1, "h")
        time_in_s = time.to("s")
        self.assertEqual(time_in_s.magnitude, 3600)
        self.assertEqual(str(time_in_s.units), "second")

    def test_arithmetic_operations(self):
        """Test arithmetic operations on quantities."""
        # Addition of compatible units
        length1 = Quantity(5, "m")
        length2 = Quantity(10, "cm")
        total_length = length1 + length2
        self.assertAlmostEqual(total_length.magnitude, 5.1)
        self.assertEqual(str(total_length.units), "meter")

        # Multiplication (creating derived units)
        length = Quantity(10, "m")
        width = Quantity(5, "m")
        area = length * width
        self.assertEqual(area.magnitude, 50)
        self.assertEqual(str(area.units), "meter ** 2")

        # Division (creating derived units)
        distance = Quantity(100, "m")
        time = Quantity(5, "s")
        speed = distance / time
        self.assertEqual(speed.magnitude, 20)
        self.assertEqual(str(speed.units), "meter / second")

    def test_temperature_units(self):
        """Test handling of temperature units (offset units)."""
        temp_c = Quantity(20, "degC")
        temp_f = temp_c.to("degF")
        self.assertAlmostEqual(temp_f.magnitude, 68, places=1)

        # Temperature differences (delta)
        temp_delta = Quantity(10, "delta_degC")
        new_temp = temp_c + temp_delta
        self.assertEqual(new_temp.magnitude, 30)
        self.assertEqual(str(new_temp.units), "degree_Celsius")

    def test_sensor_with_units(self):
        """Test sensors with units."""

        class DummySensor(Sensor):
            def __init__(self):
                super().__init__(name="dummy", sensor_type="test", location=(0, 0, 0))

            def _read_raw(self):
                return 42.0

        sensor = DummySensor()

        # Read without units
        value = sensor.read()
        self.assertEqual(value, 42.0)

        # Read with units
        value_m = sensor.read(unit="m")
        self.assertEqual(value_m.magnitude, 42.0)
        self.assertEqual(str(value_m.units), "meter")

        # Convert to a different unit
        value_cm = value_m.to("cm")
        self.assertEqual(value_cm.magnitude, 4200.0)
        self.assertEqual(str(value_cm.units), "centimeter")


if __name__ == "__main__":
    unittest.main()

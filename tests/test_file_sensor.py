"""
Unit tests for the FileSensor class.
"""

import os
import csv
import unittest
import tempfile
from spaxiom import FileSensor


class TestFileSensor(unittest.TestCase):
    """Test suite for the FileSensor class."""

    def setUp(self):
        """Create a temporary CSV file for testing."""
        # Create a temporary directory
        self.test_dir = tempfile.TemporaryDirectory()

        # Create a test CSV file with a header and data
        self.csv_path = os.path.join(self.test_dir.name, "test_data.csv")

        with open(self.csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "temperature", "humidity"])
            writer.writerow(["2023-01-01 00:00:00", "22.5", "45.0"])
            writer.writerow(["2023-01-01 00:01:00", "23.0", "45.5"])
            writer.writerow(["2023-01-01 00:02:00", "23.5", "46.0"])
            writer.writerow(["2023-01-01 00:03:00", "24.0", "46.5"])
            writer.writerow(
                ["2023-01-01 00:04:00", "invalid", "47.0"]
            )  # Test invalid data
            writer.writerow(["2023-01-01 00:05:00", "25.0", "47.5"])

    def tearDown(self):
        """Clean up temporary files."""
        self.test_dir.cleanup()

    def test_basic_reading(self):
        """Test basic reading from a CSV file."""
        sensor = FileSensor(
            name="basic_reading_sensor",
            file_path=self.csv_path,
            column_name="temperature",
            location=(0, 0, 0),
        )

        # Check if we can read all valid values
        self.assertEqual(sensor.read(), 22.5)
        self.assertEqual(sensor.read(), 23.0)
        self.assertEqual(sensor.read(), 23.5)
        self.assertEqual(sensor.read(), 24.0)
        # The invalid row should be skipped
        self.assertEqual(sensor.read(), 25.0)

        # Should return None once we reach the end
        self.assertIsNone(sensor.read())

    def test_with_units(self):
        """Test reading with units."""
        sensor = FileSensor(
            name="units_sensor",
            file_path=self.csv_path,
            column_name="temperature",
            unit="degC",
        )

        # Read with units
        value = sensor.read(unit="degC")
        self.assertEqual(value.magnitude, 22.5)
        self.assertEqual(str(value.units), "degree_Celsius")

        # Convert to a different unit
        value_f = value.to("degF")
        self.assertAlmostEqual(value_f.magnitude, 72.5, places=1)

    def test_looping(self):
        """Test looping behavior."""
        sensor = FileSensor(
            name="looping_sensor",
            file_path=self.csv_path,
            column_name="temperature",
            loop=True,
        )

        # Read all values
        for _ in range(5):
            sensor.read()

        # Should loop back to the beginning
        self.assertEqual(sensor.read(), 22.5)

    def test_reset(self):
        """Test reset functionality."""
        sensor = FileSensor(
            name="reset_sensor",
            file_path=self.csv_path,
            column_name="temperature",
        )

        # Read a few values
        sensor.read()
        sensor.read()
        self.assertEqual(sensor.current_row, 2)

        # Reset the sensor
        sensor.reset()
        self.assertEqual(sensor.current_row, 0)

        # Should start from the beginning again
        self.assertEqual(sensor.read(), 22.5)

    def test_column_by_index(self):
        """Test reading a column by index."""
        # Create a CSV file without a header
        noheader_path = os.path.join(self.test_dir.name, "noheader.csv")
        with open(noheader_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["2023-01-01 00:00:00", "22.5", "45.0"])
            writer.writerow(["2023-01-01 00:01:00", "23.0", "45.5"])

        sensor = FileSensor(
            name="column_index_sensor",
            file_path=noheader_path,
            column_name="1",  # Use the second column (index 1)
            skip_header=False,
        )

        self.assertEqual(sensor.read(), 22.5)
        self.assertEqual(sensor.read(), 23.0)

    def test_column_not_found(self):
        """Test error when column is not found."""
        with self.assertRaises(ValueError):
            FileSensor(
                name="not_found_column_sensor",
                file_path=self.csv_path,
                column_name="non_existent_column",
            )

    def test_file_not_found(self):
        """Test error when file is not found."""
        with self.assertRaises(FileNotFoundError):
            FileSensor(
                name="not_found_file_sensor",
                file_path="non_existent_file.csv",
                column_name="temperature",
            )

    def test_invalid_column_index(self):
        """Test behavior with an invalid column index."""
        # Create a CSV file without a header
        noheader_path = os.path.join(self.test_dir.name, "noheader.csv")
        with open(noheader_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["2023-01-01 00:00:00", "22.5", "45.0"])

        # Instead of raising an exception immediately, the implementation
        # prints a warning and skips the row when reading
        sensor = FileSensor(
            name="invalid_index_sensor",
            file_path=noheader_path,
            column_name="5",  # This index is out of range
            skip_header=False,
        )
        
        # When we try to read, we should get None (no valid data)
        self.assertIsNone(sensor.read())

    def test_string_column_in_noheader_mode(self):
        """Test using a string column name in no-header mode."""
        # Create a CSV file without a header but with string values in first row
        noheader_path = os.path.join(self.test_dir.name, "string_columns.csv")
        with open(noheader_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "temperature", "humidity"])
            writer.writerow(["2023-01-01 00:00:00", "22.5", "45.0"])

        # Create the sensor using the column index instead
        sensor = FileSensor(
            name="string_column_sensor",
            file_path=noheader_path,
            column_name="1",  # Use index 1 instead of name
            skip_header=False,  # We're treating the header as data
        )
        
        # First row containing "temperature" is skipped due to conversion error
        # Second row should work
        self.assertEqual(sensor.read(), 22.5)

    def test_no_data_in_file(self):
        """Test behavior with an empty CSV file."""
        # Create an empty CSV file
        empty_path = os.path.join(self.test_dir.name, "empty.csv")
        with open(empty_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Just write the header
            writer.writerow(["timestamp", "temperature", "humidity"])

        sensor = FileSensor(
            name="empty_file_sensor",
            file_path=empty_path,
            column_name="temperature",
        )
        
        # Should return None as there's no data
        self.assertIsNone(sensor.read())

    def test_repr_method(self):
        """Test the string representation of FileSensor."""
        sensor = FileSensor(
            name="repr_test_sensor",
            file_path=self.csv_path,
            column_name="temperature",
        )
        
        # Test the repr method
        repr_str = repr(sensor)
        self.assertIn("FileSensor", repr_str)
        self.assertIn("name='repr_test_sensor'", repr_str)
        self.assertIn("file='test_data.csv'", repr_str)
        self.assertIn("column='temperature'", repr_str)


if __name__ == "__main__":
    unittest.main()

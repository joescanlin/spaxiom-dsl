"""
Tests for the Spaxiom CLI scaffold generation functionality.
"""

import os
import tempfile
import unittest
from click.testing import CliRunner

from spaxiom.cli import cli


class TestCLIScaffold(unittest.TestCase):
    """Test suite for the 'spax new' command that generates scaffolds."""

    def setUp(self):
        """Set up for each test."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()

    def test_scaffold_help(self):
        """Test that the 'new' command help works."""
        result = self.runner.invoke(cli, ["new", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Create a new Spaxiom script scaffold", result.output)
        self.assertIn("--sensors", result.output)
        self.assertIn("--zones", result.output)
        self.assertIn("--privacy", result.output)

    def test_basic_scaffold_creation(self):
        """Test basic scaffold creation with default options."""
        script_name = "test_basic_scaffold"
        result = self.runner.invoke(
            cli, ["new", script_name, "--output-dir", self.temp_path]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created scaffold", result.output)

        # Check if the file was created
        script_path = os.path.join(self.temp_path, f"{script_name}.py")
        self.assertTrue(os.path.exists(script_path))

        # Check file content for basic elements
        with open(script_path, "r") as f:
            content = f.read()

        # Verify key imports
        self.assertIn(
            "from spaxiom import Sensor, Zone, Condition, on, within", content
        )
        self.assertIn("from spaxiom import RandomSensor", content)

        # Verify sensor and zone creation
        self.assertIn("sensor1 = RandomSensor", content)
        self.assertIn("sensor2 = RandomSensor", content)
        self.assertIn("zone1 = Zone", content)

        # Verify privacy settings
        self.assertIn('privacy="private"', content)  # Default is to include privacy

        # Verify condition and event handler
        self.assertIn("@on(sustained_high)", content)
        self.assertIn("def handle_high_value():", content)
        self.assertIn("from spaxiom.runtime import format_sensor_value", content)

        # Verify runtime starter
        self.assertIn("from spaxiom.runtime import start_blocking", content)
        self.assertIn("start_blocking(poll_ms=50)", content)

    def test_custom_scaffold_options(self):
        """Test scaffold creation with custom options."""
        script_name = "test_custom_scaffold"
        result = self.runner.invoke(
            cli,
            [
                "new",
                script_name,
                "--output-dir",
                self.temp_path,
                "--sensors",
                "3",
                "--zones",
                "2",
                "--no-privacy",
            ],
        )

        self.assertEqual(result.exit_code, 0)

        # Check file content
        script_path = os.path.join(self.temp_path, f"{script_name}.py")
        with open(script_path, "r") as f:
            content = f.read()

        # Verify options were applied
        self.assertIn("sensor1 = RandomSensor", content)
        self.assertIn("sensor2 = RandomSensor", content)
        self.assertIn("sensor3 = RandomSensor", content)
        self.assertIn("zone1 = Zone", content)
        self.assertIn("zone2 = Zone", content)
        self.assertNotIn('privacy="private"', content)  # No privacy was specified

    def test_overwrite_confirmation(self):
        """Test the overwrite confirmation prompt."""
        script_name = "test_overwrite"
        script_path = os.path.join(self.temp_path, f"{script_name}.py")

        # Create a file first
        with open(script_path, "w") as f:
            f.write("# Existing script")

        # Test with response 'n' (don't overwrite)
        result = self.runner.invoke(
            cli,
            ["new", script_name, "--output-dir", self.temp_path],
            input="n\n",  # Respond 'no' to the overwrite prompt
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("File", result.output)
        self.assertIn("already exists", result.output)
        self.assertIn("Operation cancelled", result.output)

        # Check file wasn't overwritten
        with open(script_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "# Existing script")

        # Test with response 'y' (do overwrite)
        result = self.runner.invoke(
            cli,
            ["new", script_name, "--output-dir", self.temp_path],
            input="y\n",  # Respond 'yes' to the overwrite prompt
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Overwrite", result.output)
        self.assertIn("Created scaffold", result.output)

        # Check file was overwritten
        with open(script_path, "r") as f:
            content = f.read()
        self.assertIn("from spaxiom import", content)  # New content was written


if __name__ == "__main__":
    unittest.main()

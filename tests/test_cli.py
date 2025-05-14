"""
Tests for the Spaxiom CLI module.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from spaxiom.cli import cli


class TestCLI(unittest.TestCase):
    """Test the Spaxiom CLI commands."""

    def setUp(self):
        """Set up for each test."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()

    def test_cli_help(self):
        """Test that the CLI help command works."""
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Spaxiom DSL command-line interface", result.output)
        self.assertIn("new", result.output)
        self.assertIn("run", result.output)

    def test_new_command_help(self):
        """Test that the 'new' command help works."""
        result = self.runner.invoke(cli, ["new", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Create a new Spaxiom script scaffold", result.output)
        self.assertIn("--sensors", result.output)
        self.assertIn("--zones", result.output)
        self.assertIn("--privacy", result.output)

    def test_run_command_help(self):
        """Test that the 'run' command help works."""
        result = self.runner.invoke(cli, ["run", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Run a Spaxiom script", result.output)
        self.assertIn("--poll-ms", result.output)
        self.assertIn("--history-length", result.output)

    def test_new_command_creates_script(self):
        """Test that the 'new' command creates a script."""
        script_name = "test_script"
        result = self.runner.invoke(
            cli, ["new", script_name, "--output-dir", self.temp_path]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            f"Created scaffold script: {os.path.join(self.temp_path, script_name)}.py",
            result.output,
        )

        # Check if the file was created
        script_path = os.path.join(self.temp_path, f"{script_name}.py")
        self.assertTrue(os.path.exists(script_path))

        # Check file content
        with open(script_path, "r") as f:
            content = f.read()

        # Verify key components
        self.assertIn(
            "from spaxiom import Sensor, Zone, Condition, on, within", content
        )
        self.assertIn("RandomSensor", content)
        self.assertIn("Zone", content)
        self.assertIn("def main():", content)
        self.assertIn("start_blocking", content)

    def test_new_command_with_options(self):
        """Test that the 'new' command honors options."""
        script_name = "test_script_options"
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
                "--privacy",
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
        self.assertIn('privacy="private"', content)

    def test_new_command_no_privacy(self):
        """Test that the 'new' command respects --no-privacy option."""
        script_name = "test_script_no_privacy"
        result = self.runner.invoke(
            cli, ["new", script_name, "--output-dir", self.temp_path, "--no-privacy"]
        )

        self.assertEqual(result.exit_code, 0)

        # Check file content
        script_path = os.path.join(self.temp_path, f"{script_name}.py")
        with open(script_path, "r") as f:
            content = f.read()

        # Verify no privacy parameters are present
        self.assertNotIn('privacy="private"', content)

    def test_new_command_file_exists(self):
        """Test that the 'new' command checks for existing files."""
        script_name = "existing_script"
        script_path = os.path.join(self.temp_path, f"{script_name}.py")

        # Create the file first
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

    @patch("spaxiom.cli.importlib.util.spec_from_file_location")
    @patch("spaxiom.cli.importlib.util.module_from_spec")
    @patch("spaxiom.cli.start_blocking")
    def test_run_command(
        self, mock_start_blocking, mock_module_from_spec, mock_spec_from_file_location
    ):
        """Test the 'run' command with mocked imports."""
        # Create a mock script that we'll "run"
        script_path = os.path.join(self.temp_path, "test_run.py")
        with open(script_path, "w") as f:
            f.write("# Test script for running\n")
            f.write("def main():\n")
            f.write("    pass\n")

        # Mock the module loading process
        mock_spec = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        # Inject a mock main function
        mock_main = MagicMock()
        mock_module.main = mock_main

        # Run the command
        result = self.runner.invoke(cli, ["run", script_path])

        # Verify the output and mocks
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Importing", result.output)
        self.assertIn("Script has a main() function", result.output)

        # Verify the main function was called
        mock_main.assert_called_once()

        # Verify that start_blocking was not called (since we had a main function)
        mock_start_blocking.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Tests for Spaxiom Edge CLI commands."""

import json
import unittest
from unittest.mock import patch
from click.testing import CliRunner

from spaxiom.cli import cli


class TestEdgeCLI(unittest.TestCase):
    """Test the Edge CLI commands."""

    def setUp(self):
        self.runner = CliRunner()

    def test_edge_help(self):
        """Test edge command help."""
        result = self.runner.invoke(cli, ["edge", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Edge device management", result.output)
        self.assertIn("start", result.output)
        self.assertIn("status", result.output)
        self.assertIn("agents", result.output)

    def test_edge_start_help(self):
        """Test edge start command help."""
        result = self.runner.invoke(cli, ["edge", "start", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Start the Spaxiom Edge server", result.output)
        self.assertIn("--host", result.output)
        self.assertIn("--port", result.output)

    def test_edge_status_help(self):
        """Test edge status command help."""
        result = self.runner.invoke(cli, ["edge", "status", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Show Spaxiom Edge system status", result.output)

    def test_edge_agents_help(self):
        """Test edge agents command help."""
        result = self.runner.invoke(cli, ["edge", "agents", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Manage deployed agents", result.output)
        self.assertIn("list", result.output)
        self.assertIn("deploy", result.output)
        self.assertIn("start", result.output)
        self.assertIn("stop", result.output)

    def test_edge_agents_list_help(self):
        """Test edge agents list help."""
        result = self.runner.invoke(cli, ["edge", "agents", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("List all agents", result.output)

    def test_edge_agents_deploy_help(self):
        """Test edge agents deploy help."""
        result = self.runner.invoke(cli, ["edge", "agents", "deploy", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Deploy a pattern", result.output)

    def test_edge_agents_start_help(self):
        """Test edge agents start help."""
        result = self.runner.invoke(cli, ["edge", "agents", "start", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Start a stopped agent", result.output)

    def test_edge_agents_stop_help(self):
        """Test edge agents stop help."""
        result = self.runner.invoke(cli, ["edge", "agents", "stop", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Stop a running agent", result.output)

    def test_edge_agents_restart_help(self):
        """Test edge agents restart help."""
        result = self.runner.invoke(cli, ["edge", "agents", "restart", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Restart an agent", result.output)

    def test_edge_agents_remove_help(self):
        """Test edge agents remove help."""
        result = self.runner.invoke(cli, ["edge", "agents", "remove", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Remove an agent", result.output)

    def test_edge_agents_info_help(self):
        """Test edge agents info help."""
        result = self.runner.invoke(cli, ["edge", "agents", "info", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Show detailed agent information", result.output)

    @patch("spaxiom.cli.commands.edge.status.fetch_status")
    def test_edge_status_json(self, mock_fetch):
        """Test edge status with JSON output."""
        mock_fetch.return_value = {
            "running": True,
            "database": {"healthy": True},
            "sensors": {"active": 3, "total": 5},
            "agents": {"running": 2, "total": 3},
        }

        result = self.runner.invoke(cli, ["--json", "edge", "status"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertTrue(data["running"])

    @patch("spaxiom.cli.commands.edge.status.fetch_status")
    def test_edge_status_error(self, mock_fetch):
        """Test edge status when server is not running."""
        mock_fetch.return_value = {"error": "Cannot connect to edge server"}

        result = self.runner.invoke(cli, ["edge", "status"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cannot connect", result.output)


class TestVersionCommand(unittest.TestCase):
    """Test the version command."""

    def setUp(self):
        self.runner = CliRunner()

    def test_version_basic(self):
        """Test basic version output."""
        result = self.runner.invoke(cli, ["version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("spaxiom", result.output)
        self.assertIn("0.1.0", result.output)

    def test_version_verbose(self):
        """Test verbose version output."""
        result = self.runner.invoke(cli, ["version", "--verbose"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("spaxiom", result.output)
        self.assertIn("Python", result.output)
        # Optional dependencies section may or may not show depending on rich
        # Just check basic output works

    def test_version_json(self):
        """Test JSON version output."""
        result = self.runner.invoke(cli, ["--json", "version"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("spaxiom", data)
        self.assertIn("python", data)


class TestGlobalOptions(unittest.TestCase):
    """Test global CLI options."""

    def setUp(self):
        self.runner = CliRunner()

    def test_quiet_flag(self):
        """Test that --quiet flag is passed to context."""
        result = self.runner.invoke(cli, ["--quiet", "version"])
        self.assertEqual(result.exit_code, 0)

    def test_json_flag(self):
        """Test that --json flag produces JSON output."""
        result = self.runner.invoke(cli, ["--json", "version"])
        self.assertEqual(result.exit_code, 0)
        # Should be valid JSON
        json.loads(result.output)


if __name__ == "__main__":
    unittest.main()

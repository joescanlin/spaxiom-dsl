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

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_list_json(self, mock_api):
        """Test agents list with JSON output."""
        mock_api.return_value = [
            {"id": "abc123", "name": "Test Agent", "status": "running", "stats": {}},
        ]

        result = self.runner.invoke(cli, ["--json", "edge", "agents", "list"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Agent")

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_list_empty(self, mock_api):
        """Test agents list when no agents exist."""
        mock_api.return_value = []

        result = self.runner.invoke(cli, ["edge", "agents", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No agents found", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_start(self, mock_api):
        """Test starting an agent."""
        mock_api.return_value = {"status": "running"}

        result = self.runner.invoke(cli, ["edge", "agents", "start", "abc123"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("started", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_stop(self, mock_api):
        """Test stopping an agent."""
        mock_api.return_value = {"status": "stopped"}

        result = self.runner.invoke(
            cli, ["edge", "agents", "stop", "abc123", "--force"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("stopped", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_restart(self, mock_api):
        """Test restarting an agent."""
        mock_api.return_value = {"status": "running"}

        result = self.runner.invoke(cli, ["edge", "agents", "restart", "abc123"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("restarted", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_deploy(self, mock_api):
        """Test deploying an agent."""
        mock_api.return_value = {"id": "newagent123"}

        result = self.runner.invoke(cli, ["edge", "agents", "deploy", "pattern123"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("deployed", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_remove(self, mock_api):
        """Test removing an agent."""
        mock_api.return_value = {"success": True}

        result = self.runner.invoke(
            cli, ["edge", "agents", "remove", "abc123", "--force"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("removed", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_info(self, mock_api):
        """Test getting agent info."""
        mock_api.return_value = {
            "id": "abc123",
            "name": "Test Agent",
            "status": "running",
            "pattern_id": "pattern123",
            "stats": {"tick_count": 100, "events_emitted": 10, "avg_tick_ms": 5.0},
        }

        result = self.runner.invoke(cli, ["edge", "agents", "info", "abc123"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Test Agent", result.output)
        self.assertIn("running", result.output)

    @patch("spaxiom.cli.commands.edge.agents.api_request")
    def test_agents_error_handling(self, mock_api):
        """Test error handling in agents commands."""
        mock_api.return_value = {"error": "Agent not found"}

        result = self.runner.invoke(cli, ["edge", "agents", "start", "notfound"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Agent not found", result.output)


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
        self.assertIn("Optional dependencies", result.output)

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

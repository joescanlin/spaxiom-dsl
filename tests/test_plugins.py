"""
Tests for the plugins module.
"""

import unittest
from unittest.mock import patch

from spaxiom.plugins import (
    register_plugin,
    reset_plugins,
    PLUGINS,
)


class TestPlugins(unittest.TestCase):
    """Test the plugins module functionality."""

    def setUp(self):
        """Set up for tests."""
        # Clear plugins before each test
        reset_plugins()

    def tearDown(self):
        """Clean up after tests."""
        reset_plugins()

    def test_register_plugin(self):
        """Test registering a plugin using the decorator."""

        # Define a test plugin function
        @register_plugin
        def test_plugin():
            pass

        # Check it was registered correctly
        self.assertIn(test_plugin, PLUGINS)
        self.assertEqual(1, len(PLUGINS))

    def test_register_plugin_duplicate(self):
        """Test registering the same plugin multiple times."""

        # Define a test plugin function
        def test_plugin():
            pass

        # Register it twice
        register_plugin(test_plugin)
        register_plugin(test_plugin)

        # It should only be registered once
        self.assertIn(test_plugin, PLUGINS)
        self.assertEqual(1, len(PLUGINS))

    @patch("spaxiom.plugins.logger")
    def test_reset_plugins(self, mock_logger):
        """Test resetting registered plugins."""

        # Define and register a plugin function
        def test_plugin():
            pass

        register_plugin(test_plugin)

        # Verify it was registered
        self.assertEqual(1, len(PLUGINS))

        # Reset plugins
        reset_plugins()

        # Verify plugins were cleared
        self.assertEqual(0, len(PLUGINS))


if __name__ == "__main__":
    unittest.main()

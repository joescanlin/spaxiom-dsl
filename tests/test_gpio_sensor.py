"""
Tests for the GPIO sensor module.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch


# Define a mock gpiozero module that we'll use for testing
class MockGPIOZero:
    """Mock class for the gpiozero module."""

    class DigitalInputDevice:
        """Mock DigitalInputDevice class."""

        def __init__(self, pin, pull_up=False, active_state=True):
            self.pin = pin
            self.pull_up = pull_up
            self.active_state = active_state
            self.value = 0  # Default value is 0 (inactive)
            self.closed = False

        def close(self):
            self.closed = True


# Test that the module at least imports
def test_gpio_sensor_imports():
    """Test that the GPIO sensor module can be imported."""
    from spaxiom.adaptors import __init__  # noqa: F401


# Comprehensive test suite using mocks to avoid hardware dependencies
class TestGPIODigitalSensor:
    """Test the GPIODigitalSensor class."""

    def setup_method(self):
        """Set up mocks before each test."""
        # Mock platform check to make the tests think we're on Linux
        self.platform_patch = patch("sys.platform", "linux")
        self.platform_patch.start()

        # Create a mock for gpiozero
        self.mock_gpiozero = MockGPIOZero()

        # Mock gpiozero import - this needs to be set up BEFORE importing the module
        sys.modules["gpiozero"] = self.mock_gpiozero

        # Now we need to reload the gpio_sensor module to pick up our mocks
        # First, if it's already imported, store any existing import
        self.old_gpio_sensor = sys.modules.get("spaxiom.adaptors.gpio_sensor")

        # Import and patch the module
        import importlib
        from spaxiom.adaptors import gpio_sensor

        importlib.reload(gpio_sensor)

        # Now we need to patch the gpiozero reference inside the module
        gpio_sensor.gpiozero = self.mock_gpiozero
        gpio_sensor.GPIOZERO_AVAILABLE = True

    def teardown_method(self):
        """Clean up after each test."""
        self.platform_patch.stop()

        # Remove our mock from sys.modules
        if "gpiozero" in sys.modules:
            del sys.modules["gpiozero"]

        # Restore original module if it existed
        if hasattr(self, "old_gpio_sensor") and self.old_gpio_sensor:
            sys.modules["spaxiom.adaptors.gpio_sensor"] = self.old_gpio_sensor

    def test_initialization(self):
        """Test GPIODigitalSensor initialization."""
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        # Test basic initialization
        sensor = GPIODigitalSensor(name="test_sensor", pin=17)
        assert sensor.name == "test_sensor"
        assert sensor.pin == 17
        assert sensor.pull_up is False  # Default value
        assert sensor.active_state is True  # Default value

        # Test initialization with custom parameters
        sensor = GPIODigitalSensor(
            name="custom_sensor",
            pin=18,
            location=(1.0, 2.0, 3.0),
            pull_up=True,
            active_state=False,
            metadata={"location": "door"},
        )
        assert sensor.name == "custom_sensor"
        assert sensor.pin == 18
        assert sensor.location == (1.0, 2.0, 3.0)
        assert sensor.pull_up is True
        assert sensor.active_state is False
        assert sensor.metadata["location"] == "door"

        # The DigitalInputDevice should have been initialized with our parameters
        assert sensor._input_device.pin == 18
        assert sensor._input_device.pull_up is True
        assert sensor._input_device.active_state is False

    def test_unavailable_on_non_linux(self):
        """Test that GPIODigitalSensor raises ImportError when gpiozero is not available."""
        # First, restore real platform
        self.platform_patch.stop()

        # Now patch to use a non-Linux platform
        with patch("sys.platform", "darwin"):
            # Re-import to update GPIOZERO_AVAILABLE under the patched environment
            import importlib
            from spaxiom.adaptors import gpio_sensor

            importlib.reload(gpio_sensor)
            gpio_sensor.GPIOZERO_AVAILABLE = False

            with pytest.raises(ImportError):
                gpio_sensor.GPIODigitalSensor(name="unavailable", pin=17)

        # Restore Linux platform for other tests
        self.platform_patch = patch("sys.platform", "linux")
        self.platform_patch.start()

        # Re-import with Linux platform
        importlib.reload(gpio_sensor)
        gpio_sensor.gpiozero = self.mock_gpiozero
        gpio_sensor.GPIOZERO_AVAILABLE = True

    def test_initialization_error(self):
        """Test error handling during initialization."""
        # Create a new module-level gpiozero mock with DigitalInputDevice that raises exception
        error_mock_gpiozero = MagicMock()
        error_mock_gpiozero.DigitalInputDevice = MagicMock(
            side_effect=RuntimeError("GPIO error")
        )

        # Import the module
        from spaxiom.adaptors import gpio_sensor

        # Save the original mock
        original_gpiozero = gpio_sensor.gpiozero

        try:
            # Replace with our error mock
            gpio_sensor.gpiozero = error_mock_gpiozero

            # Try to create a sensor
            with pytest.raises(RuntimeError) as exc_info:
                gpio_sensor.GPIODigitalSensor(name="error_sensor", pin=17)

            assert "Failed to initialize GPIO pin" in str(exc_info.value)
        finally:
            # Restore the original mock
            gpio_sensor.gpiozero = original_gpiozero

    def test_read_methods(self):
        """Test reading from the GPIO sensor."""
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        # Create a sensor
        sensor = GPIODigitalSensor(name="read_test", pin=17)

        # Initial state should be inactive (0)
        assert sensor._read_raw() is False
        assert sensor.is_active() is False

        # Change the state to active (1)
        sensor._input_device.value = 1
        assert sensor._read_raw() is True
        assert sensor.is_active() is True

        # Change back to inactive
        sensor._input_device.value = 0
        assert sensor._read_raw() is False
        assert sensor.is_active() is False

    def test_cleanup(self):
        """Test resource cleanup when the object is deleted."""
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        sensor = GPIODigitalSensor(name="cleanup_sensor", pin=17)
        device = sensor._input_device

        # Simulate the __del__ method
        sensor.__del__()

        # Check that the device was closed
        assert device.closed is True

    def test_repr(self):
        """Test the string representation of GPIODigitalSensor."""
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        sensor = GPIODigitalSensor(
            name="repr_sensor", pin=17, pull_up=True, active_state=False
        )

        # Get the string representation
        repr_str = repr(sensor)

        # Check that it contains important information
        assert "GPIODigitalSensor" in repr_str
        assert "name='repr_sensor'" in repr_str
        assert "pin=17" in repr_str
        assert "pull_up=True" in repr_str
        assert "active_state=False" in repr_str

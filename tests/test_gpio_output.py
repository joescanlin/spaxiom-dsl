"""
Tests for the GPIO output module.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch


# Define a mock gpiozero module that we'll use for testing
class MockGPIOZero:
    """Mock class for the gpiozero module."""

    class LED:
        """Mock LED class."""

        def __init__(self, pin, active_high=True, initial_value=False):
            self.pin = pin
            self.active_high = active_high
            self.value = initial_value
            self.is_lit = initial_value
            self.closed = False

        def on(self):
            self.value = True
            self.is_lit = True

        def off(self):
            self.value = False
            self.is_lit = False

        def toggle(self):
            self.value = not self.value
            self.is_lit = self.value

        def blink(
            self,
            on_time=1,
            off_time=1,
            fade_in_time=0,
            fade_out_time=0,
            n=1,
            background=True,
        ):
            self.blink_called = True
            self.blink_args = {
                "on_time": on_time,
                "off_time": off_time,
                "fade_in_time": fade_in_time,
                "fade_out_time": fade_out_time,
                "n": n,
                "background": background,
            }

        def close(self):
            self.closed = True


# Test that the module at least imports
def test_gpio_output_imports():
    """Test that the GPIO output module can be imported."""
    from spaxiom.actuators import __init__  # noqa: F401


# Comprehensive test suite using mocks to avoid hardware dependencies
class TestGPIOOutput:
    """Test the GPIOOutput class with mocks."""

    def setup_method(self):
        """Set up mocks before each test."""
        # Mock platform check to make the tests think we're on Linux
        self.platform_patch = patch("sys.platform", "linux")
        self.platform_patch.start()

        # Create a mock for gpiozero
        self.mock_gpiozero = MockGPIOZero()

        # Mock gpiozero import - this needs to be set up BEFORE importing the module
        sys.modules["gpiozero"] = self.mock_gpiozero

        # Now that our mocks are in place, import the module
        from spaxiom.actuators import gpio_output

        # Reset the module state to force initialization with our mocks
        gpio_output.GPIOZERO_AVAILABLE = True

    def teardown_method(self):
        """Clean up after each test."""
        self.platform_patch.stop()

        # Remove our mock from sys.modules
        if "gpiozero" in sys.modules:
            del sys.modules["gpiozero"]

    def test_initialization(self):
        """Test GPIOOutput initialization."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        # Test basic initialization
        output = GPIOOutput(name="test_output", pin=17)
        assert output.name == "test_output"
        assert output.pin == 17
        assert output.active_high is True  # Default value

        # Test initialization with custom parameters
        output = GPIOOutput(
            name="custom_output",
            pin=18,
            active_high=False,
            initial_value=True,
            metadata={"location": "kitchen"},
        )
        assert output.name == "custom_output"
        assert output.pin == 18
        assert output.active_high is False
        assert output.metadata["location"] == "kitchen"

        # The LED should have been initialized with our parameters
        assert output._output_device.pin == 18
        assert output._output_device.active_high is False
        assert output._output_device.value is True  # initial_value

    def test_unavailable_on_non_linux(self):
        """Test that GPIOOutput raises ImportError when gpiozero is not available."""
        # First, restore real platform
        self.platform_patch.stop()

        # Now patch to use a non-Linux platform
        with patch("sys.platform", "darwin"):
            # Re-import to update GPIOZERO_AVAILABLE under the patched environment
            import importlib
            from spaxiom.actuators import gpio_output

            importlib.reload(gpio_output)

            with pytest.raises(ImportError):
                gpio_output.GPIOOutput(name="unavailable", pin=17)

        # Restore Linux platform for other tests
        self.platform_patch = patch("sys.platform", "linux")
        self.platform_patch.start()

        # Re-import with Linux platform
        importlib.reload(gpio_output)
        gpio_output.GPIOZERO_AVAILABLE = True

    def test_initialization_error(self):
        """Test error handling during initialization."""
        # Create a new module-level gpiozero mock with LED that raises exception
        error_mock_gpiozero = MagicMock()
        error_mock_gpiozero.LED = MagicMock(side_effect=RuntimeError("GPIO error"))

        # Replace the mock in sys.modules
        old_mock = sys.modules["gpiozero"]
        sys.modules["gpiozero"] = error_mock_gpiozero

        try:
            # Import the module with the new mock
            import importlib
            from spaxiom.actuators import gpio_output

            importlib.reload(gpio_output)

            from spaxiom.actuators.gpio_output import GPIOOutput

            with pytest.raises(RuntimeError) as exc_info:
                GPIOOutput(name="error_output", pin=17)

            assert "Failed to initialize GPIO pin" in str(exc_info.value)
        finally:
            # Restore the original mock
            sys.modules["gpiozero"] = old_mock

            # Re-import with the original mock
            importlib.reload(gpio_output)

    def test_set_high_and_low(self):
        """Test setting output high and low."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        output = GPIOOutput(name="high_low_output", pin=17)

        # Test set_high
        output.set_high()
        assert output._output_device.is_lit is True
        assert output.is_active() is True

        # Test set_low
        output.set_low()
        assert output._output_device.is_lit is False
        assert output.is_active() is False

    def test_toggle(self):
        """Test toggling the output."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        output = GPIOOutput(name="toggle_output", pin=17, initial_value=False)
        assert output.is_active() is False

        # Toggle once (False -> True)
        output.toggle()
        assert output.is_active() is True

        # Toggle again (True -> False)
        output.toggle()
        assert output.is_active() is False

    def test_pulse(self):
        """Test pulsing the output."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        output = GPIOOutput(name="pulse_output", pin=17)

        # Call pulse with custom parameters
        output.pulse(fade_in_time=0.5, fade_out_time=0.5, n=3, background=False)

        # Verify that blink was called with our parameters
        assert hasattr(output._output_device, "blink_called")
        assert output._output_device.blink_called is True
        assert output._output_device.blink_args["fade_in_time"] == 0.5
        assert output._output_device.blink_args["fade_out_time"] == 0.5
        assert output._output_device.blink_args["n"] == 3
        assert output._output_device.blink_args["background"] is False

    def test_cleanup(self):
        """Test resource cleanup when the object is deleted."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        output = GPIOOutput(name="cleanup_output", pin=17)
        device = output._output_device

        # Simulate the __del__ method
        output.__del__()

        # Check that the device was closed
        assert device.closed is True

    def test_repr(self):
        """Test the string representation of GPIOOutput."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        output = GPIOOutput(name="repr_output", pin=17)

        # Get the string representation
        repr_str = repr(output)

        # Check that it contains important information
        assert "GPIOOutput" in repr_str
        assert "name='repr_output'" in repr_str
        assert "pin=17" in repr_str
        assert "state=inactive" in repr_str  # Initial state is inactive

        # Change the state and check the updated repr
        output.set_high()
        repr_str = repr(output)
        assert "state=active" in repr_str

"""
Tests for the GPIO sensor module.
"""

import sys
import pytest
import importlib.util

# Skip all tests if not on Linux
is_linux = sys.platform.startswith("linux")
has_gpiozero = importlib.util.find_spec("gpiozero") is not None


# Test that the module at least imports
def test_gpio_sensor_imports():
    """Test that the GPIO sensor module can be imported."""
    from spaxiom.adaptors import __init__  # noqa: F401


# Skip hardware-dependent tests on non-Linux platforms
@pytest.mark.skipif(
    not (is_linux and has_gpiozero),
    reason="GPIO sensor tests require Linux and gpiozero",
)
class TestGPIODigitalSensor:
    """Test the GPIODigitalSensor class."""

    def test_gpio_sensor_class_exists(self):
        """Test that the GPIODigitalSensor class exists."""
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        assert GPIODigitalSensor is not None

    def test_gpio_sensor_methods(self, monkeypatch):
        """Test that GPIODigitalSensor methods are defined (mocked)."""
        # Mock the gpiozero DigitalInputDevice class to avoid hardware access
        from spaxiom.adaptors.gpio_sensor import GPIOZERO_AVAILABLE, gpiozero

        # Only proceed if gpiozero is available
        if not GPIOZERO_AVAILABLE:
            pytest.skip("gpiozero not available")

        # Create a mock DigitalInputDevice class
        class MockDigitalInputDevice:
            def __init__(self, pin, pull_up=False, active_state=True):
                self.pin = pin
                self.pull_up = pull_up
                self.active_state = active_state
                self.value = 0

            def close(self):
                pass

        # Patch gpiozero.DigitalInputDevice with our mock
        monkeypatch.setattr(gpiozero, "DigitalInputDevice", MockDigitalInputDevice)

        # Now test the GPIODigitalSensor class
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

        # Create a GPIODigitalSensor instance
        sensor = GPIODigitalSensor(name="test_button", pin=17)

        # Test the methods
        assert hasattr(sensor, "_read_raw")
        assert hasattr(sensor, "is_active")

        # Access internals to simulate readings
        sensor._input_device.value = 1
        assert sensor._read_raw() is True
        assert sensor.is_active() is True

        sensor._input_device.value = 0
        assert sensor._read_raw() is False
        assert sensor.is_active() is False

"""
Tests for the GPIO output module.
"""

import sys
import pytest
import importlib.util

# Skip all tests if not on Linux
is_linux = sys.platform.startswith("linux")
has_gpiozero = importlib.util.find_spec("gpiozero") is not None


# Test that the module at least imports
def test_gpio_output_imports():
    """Test that the GPIO output module can be imported."""
    from spaxiom.actuators import __init__  # noqa: F401


# Skip hardware-dependent tests on non-Linux platforms
@pytest.mark.skipif(
    not (is_linux and has_gpiozero),
    reason="GPIO output tests require Linux and gpiozero",
)
class TestGPIOOutput:
    """Test the GPIOOutput class."""

    def test_gpio_output_class_exists(self):
        """Test that the GPIOOutput class exists."""
        from spaxiom.actuators.gpio_output import GPIOOutput

        assert GPIOOutput is not None

    def test_gpio_output_methods(self, monkeypatch):
        """Test that GPIOOutput methods are defined (mocked)."""
        # Mock the gpiozero LED class to avoid hardware access
        from spaxiom.actuators.gpio_output import GPIOZERO_AVAILABLE, gpiozero

        # Only proceed if gpiozero is available
        if not GPIOZERO_AVAILABLE:
            pytest.skip("gpiozero not available")

        # Create a mock LED class
        class MockLED:
            def __init__(self, pin, active_high=True, initial_value=False):
                self.pin = pin
                self.active_high = active_high
                self.value = initial_value
                self.is_lit = initial_value

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
                self, on_time, off_time, fade_in_time, fade_out_time, n, background
            ):
                pass

            def close(self):
                pass

        # Patch gpiozero.LED with our mock
        monkeypatch.setattr(gpiozero, "LED", MockLED)

        # Now test the GPIOOutput class
        from spaxiom.actuators.gpio_output import GPIOOutput

        # Create a GPIOOutput instance
        output = GPIOOutput(name="test_led", pin=17)

        # Test the methods
        assert hasattr(output, "set_high")
        assert hasattr(output, "set_low")
        assert hasattr(output, "toggle")
        assert hasattr(output, "is_active")
        assert hasattr(output, "pulse")

        # Test basic functionality with mocked LED
        assert output.is_active() is False
        output.set_high()
        assert output.is_active() is True
        output.set_low()
        assert output.is_active() is False
        output.toggle()
        assert output.is_active() is True

"""
GPIO Output module for controlling digital outputs on Linux systems using gpiozero.
"""

import sys
from typing import Optional, Dict, Any

# Check if we're on a Linux system and if gpiozero is available
GPIOZERO_AVAILABLE = False
if sys.platform.startswith("linux"):
    try:
        import gpiozero

        GPIOZERO_AVAILABLE = True
    except ImportError:
        pass


class GPIOOutput:
    """
    A class for controlling digital outputs on Linux systems using gpiozero.

    This class wraps gpiozero.LED to provide a simple interface for controlling
    digital outputs like LEDs, relays, or other GPIO-controlled devices.

    Attributes:
        name: Unique identifier for the output
        pin: BCM pin number to control
        active_high: Whether the output is active high (True) or active low (False)
    """

    def __init__(
        self,
        name: str,
        pin: int,
        active_high: bool = True,
        initial_value: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a GPIO output.

        Args:
            name: Unique name for the output
            pin: BCM pin number to control
            active_high: Whether the output is active high (True) or active low (False)
            initial_value: Initial state of the output (True = high, False = low)
            metadata: Optional metadata dictionary

        Raises:
            ImportError: If not on a Linux system or gpiozero is not installed
            RuntimeError: If unable to initialize the GPIO pin
        """
        if not GPIOZERO_AVAILABLE:
            raise ImportError(
                "GPIOOutput requires gpiozero, which is only available on Linux systems. "
                "Please install gpiozero: pip install gpiozero"
            )

        self.name = name
        self.pin = pin
        self.active_high = active_high
        self.metadata = metadata or {}

        # Initialize the GPIO output device
        try:
            self._output_device = gpiozero.LED(
                pin=pin, active_high=active_high, initial_value=initial_value
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GPIO pin {pin}: {str(e)}")

    def set_high(self) -> None:
        """Set the output to high (on) state."""
        self._output_device.on()

    def set_low(self) -> None:
        """Set the output to low (off) state."""
        self._output_device.off()

    def toggle(self) -> None:
        """Toggle the output state."""
        self._output_device.toggle()

    def is_active(self) -> bool:
        """
        Check if the output is in the active state.

        Returns:
            True if the output is active (on), False otherwise
        """
        return self._output_device.is_lit

    def pulse(
        self,
        fade_in_time: float = 0,
        fade_out_time: float = 0,
        n: int = 1,
        background: bool = True,
    ) -> None:
        """
        Pulse the output on and off.

        Args:
            fade_in_time: Time in seconds to fade in (if supported)
            fade_out_time: Time in seconds to fade out (if supported)
            n: Number of times to pulse
            background: Whether to pulse in the background
        """
        self._output_device.blink(
            on_time=1,
            off_time=1,
            fade_in_time=fade_in_time,
            fade_out_time=fade_out_time,
            n=n,
            background=background,
        )

    def __del__(self):
        """Clean up resources when the object is deleted."""
        if hasattr(self, "_output_device"):
            try:
                self._output_device.close()
            except Exception:
                pass  # Ignore cleanup errors

    def __repr__(self) -> str:
        """Return a string representation of the GPIO output."""
        state = "active" if self.is_active() else "inactive"
        return f"GPIOOutput(name='{self.name}', pin={self.pin}, state={state})"

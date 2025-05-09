"""
Actuators module for Spaxiom DSL.

This module contains classes for controlling various output devices and actuators.
"""

import sys
import importlib.util

__all__ = []

# Import GPIO output if we're on Linux
if sys.platform.startswith("linux"):
    # Check if gpiozero is available
    gpiozero_spec = importlib.util.find_spec("gpiozero")
    if gpiozero_spec is not None:
        # Import and expose the GPIO output class
        from spaxiom.actuators.gpio_output import GPIOOutput as _GPIOOutput

        locals()["GPIOOutput"] = _GPIOOutput
        __all__.append("GPIOOutput")

"""
Adaptors module for Spaxiom DSL.

This module contains adaptor classes that interface with various data sources
and convert them into Spaxiom sensor data.
"""

from spaxiom.adaptors.file_sensor import FileSensor
import sys
import importlib.util

__all__ = ["FileSensor"]

# Import GPIO sensor if we're on Linux
if sys.platform.startswith("linux"):
    # Check if gpiozero is available
    gpiozero_spec = importlib.util.find_spec("gpiozero")
    if gpiozero_spec is not None:
        # Import and expose the GPIO sensor class
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor as _GPIOSensor

        locals()["GPIODigitalSensor"] = _GPIOSensor
        __all__.append("GPIODigitalSensor")

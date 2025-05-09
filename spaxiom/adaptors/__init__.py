"""
Adaptors module for Spaxiom DSL.

This module contains adaptor classes that interface with various data sources
and convert them into Spaxiom sensor data.
"""

from spaxiom.adaptors.file_sensor import FileSensor
import sys

__all__ = ["FileSensor"]

# Import GPIO sensor if we're on Linux
if sys.platform.startswith("linux"):
    try:
        from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor, GPIOZERO_AVAILABLE
        if GPIOZERO_AVAILABLE:
            __all__.append("GPIODigitalSensor")
    except ImportError:
        pass

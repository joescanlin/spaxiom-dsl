"""
Adaptors module for Spaxiom DSL.

This module contains adaptor classes that interface with various data sources
and convert them into Spaxiom sensor data.
"""

from spaxiom.adaptors.file_sensor import FileSensor

__all__ = ["FileSensor"]

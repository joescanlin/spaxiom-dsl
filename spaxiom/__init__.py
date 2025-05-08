"""
Spaxiom - An embedded domain-specific language for spatial sensor fusion and AI.
"""

from spaxiom.sensor import Sensor
from spaxiom.zone import Zone
from spaxiom.condition import Condition
from spaxiom.events import on
from spaxiom.temporal import within

__all__ = [
    "Sensor",
    "Zone",
    "Condition",
    "on",
    "within",
]

__version__ = "0.0.1"

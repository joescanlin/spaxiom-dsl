"""
Spaxiom - An embedded domain-specific language for spatial sensor fusion and AI.
"""

from spaxiom.sensor import Sensor
from spaxiom.zone import Zone
from spaxiom.logic import Condition, transitioned_to_true
from spaxiom.events import on
from spaxiom.temporal import within
from spaxiom.entities import Entity, EntitySet

__all__ = [
    "Sensor",
    "Zone",
    "Condition",
    "on",
    "within",
    "transitioned_to_true",
    "Entity",
    "EntitySet",
]

__version__ = "0.0.1"

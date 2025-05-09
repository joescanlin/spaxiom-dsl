"""
Spaxiom - An embedded domain-specific language for spatial sensor fusion and AI.
"""

import sys
from spaxiom.sensor import Sensor
from spaxiom.zone import Zone
from spaxiom.logic import Condition, transitioned_to_true, exists
from spaxiom.events import on
from spaxiom.temporal import within, sequence
from spaxiom.entities import Entity, EntitySet
from .model import StubModel, OnnxModel
from .units import Quantity, ureg, QuantityType
from .geo import intersection, union
from .fusion import weighted_average, WeightedFusion
from .adaptors.file_sensor import FileSensor
from .adaptors.mqtt_sensor import MQTTSensor

__all__ = [
    "Sensor",
    "Zone",
    "Condition",
    "on",
    "within",
    "sequence",
    "transitioned_to_true",
    "Entity",
    "EntitySet",
    "exists",
    "StubModel",
    "OnnxModel",
    "Quantity",
    "ureg",
    "QuantityType",
    "intersection",
    "union",
    "weighted_average",
    "WeightedFusion",
    "FileSensor",
    "MQTTSensor",
]

# Import GPIO sensor if on Linux with gpiozero available
if sys.platform.startswith("linux"):
    try:
        from .adaptors.gpio_sensor import GPIODigitalSensor, GPIOZERO_AVAILABLE
        if GPIOZERO_AVAILABLE:
            __all__.append("GPIODigitalSensor")
    except ImportError:
        pass

__version__ = "0.0.2"

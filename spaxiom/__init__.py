"""
Spaxiom - An embedded domain-specific language for spatial sensor fusion and AI.
"""

import sys
import importlib.util
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
from .summarize import RollingSummary

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
    "RollingSummary",
]

# Import GPIO sensor if on Linux with gpiozero available
if sys.platform.startswith("linux"):
    # Check if gpiozero is available
    gpiozero_spec = importlib.util.find_spec("gpiozero")
    if gpiozero_spec is not None:
        # Import the GPIO sensor class
        from .adaptors.gpio_sensor import GPIODigitalSensor as _GPIODigitalSensor

        # Add it to the module namespace
        GPIODigitalSensor = _GPIODigitalSensor
        # Add it to __all__
        __all__.append("GPIODigitalSensor")

        # Also import the GPIO output class
        from .actuators.gpio_output import GPIOOutput as _GPIOOutput

        # Add it to the module namespace
        GPIOOutput = _GPIOOutput
        # Add it to __all__
        __all__.append("GPIOOutput")

__version__ = "0.0.2"

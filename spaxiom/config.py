"""
Configuration module for Spaxiom DSL to load configuration from YAML files.
"""

import os
from typing import Dict, Any, Optional, List

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is required for configuration loading. "
        "Please install it with: pip install pyyaml"
    )

from spaxiom.sensor import RandomSensor, TogglingSensor
from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor
from spaxiom.core import Sensor


def load_yaml(path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file and return Python objects.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r") as file:
        try:
            config = yaml.safe_load(file)
            return config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file: {e}")


def create_sensor_from_cfg(entry: Dict[str, Any]) -> Optional[Sensor]:
    """
    Create a sensor from a configuration entry.

    Supported configuration keys:
    - name: Unique identifier for the sensor (required)
    - type: Type of sensor (required, one of 'random', 'toggle', 'gpio_digital')
    - hz: Frequency in Hz for polling (optional, defaults to 1.0)
    - pin: BCM pin number for GPIO sensors (required for GPIO sensors)
    - privacy: Privacy level ('public' or 'private', optional, defaults to 'public')
    - location: Spatial coordinates [x, y, z] (optional, defaults to [0, 0, 0])

    Additional type-specific options may be supported.

    Args:
        entry: Dictionary containing sensor configuration

    Returns:
        Created sensor object, or None if the configuration is invalid

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Check required fields
    if "name" not in entry:
        raise ValueError("Sensor configuration missing required 'name' field")

    if "type" not in entry:
        raise ValueError("Sensor configuration missing required 'type' field")

    # Extract common parameters
    name = entry["name"]
    sensor_type = entry["type"]
    hz = float(entry.get("hz", 1.0))
    privacy = entry.get("privacy", "public")

    # Get location, defaulting to origin
    location_raw = entry.get("location", [0, 0, 0])
    if isinstance(location_raw, list) and len(location_raw) == 3:
        location = tuple(float(v) for v in location_raw)
    else:
        location = (0.0, 0.0, 0.0)

    # Get metadata if provided
    metadata = entry.get("metadata", None)

    # Create sensor based on type
    if sensor_type == "random":
        return RandomSensor(
            name=name, location=location, hz=hz, privacy=privacy, metadata=metadata
        )

    elif sensor_type == "toggle":
        # Get toggle-specific options
        toggle_interval = float(entry.get("toggle_interval", 2.0))
        high_value = float(entry.get("high_value", 1.0))
        low_value = float(entry.get("low_value", 0.0))

        return TogglingSensor(
            name=name,
            location=location,
            toggle_interval=toggle_interval,
            high_value=high_value,
            low_value=low_value,
            hz=hz,
            privacy=privacy,
            metadata=metadata,
        )

    elif sensor_type == "gpio_digital":
        # Check if pin is provided for GPIO sensors
        if "pin" not in entry:
            raise ValueError("GPIO sensor configuration missing required 'pin' field")

        pin = int(entry["pin"])
        pull_up = bool(entry.get("pull_up", False))
        active_state = bool(entry.get("active_state", True))

        return GPIODigitalSensor(
            name=name,
            pin=pin,
            location=location,
            pull_up=pull_up,
            active_state=active_state,
            metadata=metadata,
        )

    else:
        raise ValueError(f"Unsupported sensor type: {sensor_type}")


def create_sensors_from_config(config: Dict[str, Any]) -> List[Sensor]:
    """
    Create multiple sensors from a configuration dictionary.

    Args:
        config: Configuration dictionary containing a 'sensors' list

    Returns:
        List of created sensor objects

    Raises:
        ValueError: If the configuration is invalid
    """
    if "sensors" not in config or not isinstance(config["sensors"], list):
        raise ValueError("Configuration must contain a 'sensors' list")

    sensors = []
    for entry in config["sensors"]:
        try:
            sensor = create_sensor_from_cfg(entry)
            if sensor:
                sensors.append(sensor)
        except Exception as e:
            print(f"Error creating sensor from config: {e}")

    return sensors


def load_sensors_from_yaml(path: str) -> List[Sensor]:
    """
    Load and create sensors from a YAML configuration file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        List of created sensor objects

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
        ValueError: If the configuration is invalid
    """
    config = load_yaml(path)
    return create_sensors_from_config(config)

"""
Tests for the Spaxiom configuration module.
"""

import os
import pytest
import yaml
from tempfile import NamedTemporaryFile

from spaxiom import (
    load_yaml,
    create_sensor_from_cfg,
    load_sensors_from_yaml,
    SensorRegistry,
)


class TestConfig:
    """Test the configuration module functions."""

    def setup_method(self):
        """Setup for each test - clear the sensor registry."""
        SensorRegistry().clear()

    def test_load_yaml(self):
        """Test loading YAML configuration."""
        # Create a temporary YAML file
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(
                """
                name: test
                value: 42
                nested:
                  key: value
                list:
                  - item1
                  - item2
                """
            )
            tmp_path = tmp.name

        try:
            # Test loading the file
            config = load_yaml(tmp_path)

            # Check the loaded content
            assert config["name"] == "test"
            assert config["value"] == 42
            assert config["nested"]["key"] == "value"
            assert config["list"] == ["item1", "item2"]
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_yaml_file_not_found(self):
        """Test load_yaml with non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_yaml("non_existent_file.yaml")

    def test_load_yaml_invalid_yaml(self):
        """Test load_yaml with invalid YAML content."""
        # Create a temporary file with invalid YAML
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(
                """
                invalid:
                  - yaml: content
                  missing: colon
                """
            )
            tmp_path = tmp.name

        try:
            # Test loading the file
            with pytest.raises(yaml.YAMLError):
                load_yaml(tmp_path)
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_create_sensor_from_cfg_random(self):
        """Test creating a random sensor from configuration."""
        config = {
            "name": "test_random",
            "type": "random",
            "location": [1.0, 2.0, 3.0],
            "hz": 10.0,
            "privacy": "public",
        }

        sensor = create_sensor_from_cfg(config)

        assert sensor.name == "test_random"
        assert sensor.sensor_type == "random"
        assert sensor.location == (1.0, 2.0, 3.0)
        assert sensor.sample_period_s == 0.1  # 1 / 10 Hz
        assert sensor.privacy == "public"

    def test_create_sensor_from_cfg_toggle(self):
        """Test creating a toggle sensor from configuration."""
        config = {
            "name": "test_toggle",
            "type": "toggle",
            "location": [1.0, 2.0, 3.0],
            "hz": 5.0,
            "toggle_interval": 3.0,
            "high_value": 10.0,
            "low_value": 2.0,
        }

        sensor = create_sensor_from_cfg(config)

        assert sensor.name == "test_toggle"
        assert sensor.sensor_type == "toggle"
        assert sensor.location == (1.0, 2.0, 3.0)
        assert sensor.sample_period_s == 0.2  # 1 / 5 Hz
        assert sensor.toggle_interval == 3.0
        assert sensor.high_value == 10.0
        assert sensor.low_value == 2.0

    def test_create_sensor_from_cfg_gpio(self):
        """Test creating a GPIO sensor from configuration."""
        # Skip this test if not on Linux or gpiozero not available
        if not pytest.importorskip("sys").platform.startswith("linux"):
            try:
                pytest.importorskip("gpiozero")
                pytest.skip("gpiozero is available but not on Linux")
            except ImportError:
                pytest.skip("gpiozero not available")

        config = {
            "name": "test_gpio",
            "type": "gpio_digital",
            "pin": 17,
            "location": [0.0, 0.0, 0.0],
            "pull_up": True,
            "active_state": True,
        }

        # Mock gpiozero to avoid actual hardware access
        try:
            from unittest.mock import patch, MagicMock

            with patch("gpiozero.DigitalInputDevice") as mock_device:
                mock_device.return_value = MagicMock()
                sensor = create_sensor_from_cfg(config)

                assert sensor.name == "test_gpio"
                assert sensor.sensor_type == "gpio_digital"
                assert sensor.location == (0.0, 0.0, 0.0)
                assert sensor.pin == 17
                assert sensor.pull_up is True
                assert sensor.active_state is True
        except ImportError:
            pytest.skip("gpiozero not available")

    def test_create_sensor_from_cfg_missing_name(self):
        """Test creating a sensor with missing name."""
        config = {"type": "random"}

        with pytest.raises(ValueError, match="missing required 'name' field"):
            create_sensor_from_cfg(config)

    def test_create_sensor_from_cfg_missing_type(self):
        """Test creating a sensor with missing type."""
        config = {"name": "test_sensor"}

        with pytest.raises(ValueError, match="missing required 'type' field"):
            create_sensor_from_cfg(config)

    def test_create_sensor_from_cfg_invalid_type(self):
        """Test creating a sensor with invalid type."""
        config = {"name": "test_sensor", "type": "nonexistent_type"}

        with pytest.raises(ValueError, match="Unsupported sensor type"):
            create_sensor_from_cfg(config)

    def test_create_sensor_from_cfg_gpio_missing_pin(self):
        """Test creating a GPIO sensor with missing pin."""
        config = {"name": "test_gpio", "type": "gpio_digital"}

        with pytest.raises(ValueError, match="missing required 'pin' field"):
            create_sensor_from_cfg(config)

    def test_create_sensors_from_config(self):
        """Test creating multiple sensors from configuration."""
        # Create a temporary YAML file
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(
                """
                sensors:
                  - name: sensor1
                    type: random
                    location: [1.0, 2.0, 3.0]
                    hz: 5.0
                    
                  - name: sensor2
                    type: toggle
                    location: [4.0, 5.0, 6.0]
                    toggle_interval: 2.0
                """
            )
            tmp_path = tmp.name

        try:
            # Test loading and creating sensors
            sensors = load_sensors_from_yaml(tmp_path)

            # Check the created sensors
            assert len(sensors) == 2

            # Check the registry
            registry = SensorRegistry()
            assert "sensor1" in registry.list_all()
            assert "sensor2" in registry.list_all()

            # Check the first sensor
            sensor1 = registry.get("sensor1")
            assert sensor1.name == "sensor1"
            assert sensor1.sensor_type == "random"
            assert sensor1.location == (1.0, 2.0, 3.0)

            # Check the second sensor
            sensor2 = registry.get("sensor2")
            assert sensor2.name == "sensor2"
            assert sensor2.sensor_type == "toggle"
            assert sensor2.location == (4.0, 5.0, 6.0)
            assert sensor2.toggle_interval == 2.0
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_sensors_from_yaml_invalid_config(self):
        """Test loading sensors with invalid configuration."""
        # Create a temporary YAML file with invalid configuration
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(
                """
                not_sensors:
                  - name: sensor1
                    type: random
                """
            )
            tmp_path = tmp.name

        try:
            # Test loading with invalid configuration
            with pytest.raises(ValueError, match="must contain a 'sensors' list"):
                load_sensors_from_yaml(tmp_path)
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

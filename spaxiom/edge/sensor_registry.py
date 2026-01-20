"""
Persistent sensor registry for edge deployment.

Extends the in-memory SensorRegistry to persist sensors to SQLite
and instantiate sensor objects from stored configuration.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Type

from spaxiom.core import Sensor, SensorRegistry
from spaxiom.sensor import RandomSensor, TogglingSensor
from spaxiom.sim.sensors import SimulatedAnalogSensor, SimulatedBinarySensor
from spaxiom.edge.database import EdgeDatabase, SensorRepository, SensorRecord

logger = logging.getLogger(__name__)

# Sensor type registry for instantiation
SENSOR_TYPES: Dict[str, Type[Sensor]] = {
    "random": RandomSensor,
    "toggling": TogglingSensor,
    "base": Sensor,
    "sim_analog": SimulatedAnalogSensor,
    "sim_binary": SimulatedBinarySensor,
}

# Try to import optional sensor types
try:
    from spaxiom.adaptors.gpio_sensor import GPIODigitalSensor

    SENSOR_TYPES["gpio_digital"] = GPIODigitalSensor
except ImportError:
    pass

try:
    from spaxiom.adaptors.mqtt_sensor import MQTTSensor

    SENSOR_TYPES["mqtt"] = MQTTSensor
except ImportError:
    pass

try:
    from spaxiom.adaptors.file_sensor import FileSensor

    SENSOR_TYPES["file"] = FileSensor
except ImportError:
    pass


class SensorHealth:
    """Health status for a sensor."""

    def __init__(
        self,
        sensor_id: str,
        status: str = "unknown",
        last_read: Optional[float] = None,
        last_value: Any = None,
        error: Optional[str] = None,
    ):
        self.sensor_id = sensor_id
        self.status = status
        self.last_read = last_read
        self.last_value = last_value
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "status": self.status,
            "last_read": self.last_read,
            "last_value": self.last_value,
            "error": self.error,
        }


class PersistentSensorRegistry:
    """Sensor registry with SQLite persistence.

    Manages sensor lifecycle:
    - Load sensors from database on startup
    - Persist new sensors to database
    - Instantiate appropriate sensor objects from config
    - Track sensor health and connectivity
    """

    def __init__(self, db: EdgeDatabase):
        """Initialize the persistent registry.

        Args:
            db: EdgeDatabase instance for persistence
        """
        self.db = db
        self.repo = SensorRepository(db)
        self._sensors: Dict[str, Sensor] = {}
        self._records: Dict[str, SensorRecord] = {}
        self._health: Dict[str, SensorHealth] = {}
        self._core_registry = SensorRegistry()

    def load(self) -> int:
        """Load all sensors from database and instantiate them.

        Returns:
            Number of sensors loaded
        """
        records = self.repo.get_all(enabled_only=True)
        loaded = 0

        for record in records:
            try:
                sensor = self._instantiate_sensor(record)
                if sensor:
                    self._sensors[record.id] = sensor
                    self._records[record.id] = record
                    self._health[record.id] = SensorHealth(
                        sensor_id=record.id, status="loaded"
                    )
                    loaded += 1
                    logger.debug(f"Loaded sensor: {record.name} ({record.sensor_type})")
            except Exception as e:
                logger.error(f"Failed to load sensor {record.name}: {e}")
                self._health[record.id] = SensorHealth(
                    sensor_id=record.id, status="error", error=str(e)
                )

        logger.info(f"Loaded {loaded} sensors from database")
        return loaded

    def _instantiate_sensor(self, record: SensorRecord) -> Optional[Sensor]:
        """Create a sensor instance from a database record.

        Args:
            record: SensorRecord from database

        Returns:
            Instantiated Sensor object, or None if type not supported
        """
        sensor_type = record.sensor_type.lower()
        sensor_class = SENSOR_TYPES.get(sensor_type)

        if not sensor_class:
            logger.warning(f"Unknown sensor type: {sensor_type}")
            return None

        config = record.config.copy()
        location = record.location or (0, 0, 0)

        # Build sensor based on type
        if sensor_type == "random":
            return RandomSensor(
                name=record.name,
                location=location,
                hz=config.get("hz", 1.0),
                privacy=config.get("privacy", "public"),
            )
        elif sensor_type == "toggling":
            return TogglingSensor(
                name=record.name,
                location=location,
                toggle_interval=config.get("toggle_interval", 2.0),
                high_value=config.get("high_value", 1.0),
                low_value=config.get("low_value", 0.0),
                hz=config.get("hz", 10.0),
                privacy=config.get("privacy", "public"),
            )
        elif sensor_type == "gpio_digital":
            return sensor_class(
                name=record.name,
                pin=config.get("pin", 17),
                sensor_type=config.get("value_type", "digital"),
                location=location,
                pull_up=config.get("pull_up", True),
                active_low=config.get("active_low", False),
            )
        elif sensor_type == "mqtt":
            return sensor_class(
                name=record.name,
                topic=config.get("topic", "sensors/#"),
                broker=config.get("broker", "localhost"),
                port=config.get("port", 1883),
                location=location,
            )
        elif sensor_type == "file":
            return sensor_class(
                name=record.name,
                path=config.get("path", "/tmp/sensor"),
                sensor_type=config.get("value_type", "file"),
                location=location,
            )
        elif sensor_type == "sim_analog":
            return SimulatedAnalogSensor(
                name=record.name,
                location=location,
                base=config.get("base", 0.0),
                min_value=config.get("min_value", 0.0),
                max_value=config.get("max_value", 1.0),
                noise_std=config.get("noise_std", 0.05),
                drift_per_s=config.get("drift_per_s", 0.0),
                spike_probability=config.get("spike_probability", 0.0),
                spike_delta=config.get("spike_delta", 0.0),
                spike_duration_s=config.get("spike_duration_s", 1.0),
                seed=config.get("seed"),
                privacy=config.get("privacy", "public"),
            )
        elif sensor_type == "sim_binary":
            return SimulatedBinarySensor(
                name=record.name,
                location=location,
                probability_on=config.get("probability_on", 0.05),
                min_on_s=config.get("min_on_s", 1.0),
                min_off_s=config.get("min_off_s", 1.0),
                seed=config.get("seed"),
                privacy=config.get("privacy", "public"),
            )
        else:
            # Generic sensor
            return Sensor(
                name=record.name,
                sensor_type=sensor_type,
                location=location,
            )

    def register(
        self,
        name: str,
        sensor_type: str,
        location: Optional[tuple] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> Optional[str]:
        """Register a new sensor and persist to database.

        Args:
            name: Unique sensor name
            sensor_type: Type of sensor (random, gpio_digital, mqtt, etc.)
            location: (x, y, z) location tuple
            config: Type-specific configuration
            enabled: Whether sensor is enabled

        Returns:
            Sensor ID if successful, None if failed
        """
        # Check for duplicate name
        existing = self.repo.get_by_name(name)
        if existing:
            logger.error(f"Sensor with name '{name}' already exists")
            return None

        # Create database record
        try:
            record = self.repo.create(
                name=name,
                sensor_type=sensor_type,
                location=location,
                config=config,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Failed to create sensor record: {e}")
            return None

        # Instantiate sensor if enabled
        if enabled:
            try:
                sensor = self._instantiate_sensor(record)
                if sensor:
                    self._sensors[record.id] = sensor
                    self._records[record.id] = record
                    self._health[record.id] = SensorHealth(
                        sensor_id=record.id, status="ok"
                    )
                    logger.info(f"Registered sensor: {name} ({sensor_type})")
            except Exception as e:
                logger.error(f"Failed to instantiate sensor {name}: {e}")
                self._health[record.id] = SensorHealth(
                    sensor_id=record.id, status="error", error=str(e)
                )

        return record.id

    def unregister(self, sensor_id: str) -> bool:
        """Remove a sensor from the registry and database.

        Args:
            sensor_id: ID of sensor to remove

        Returns:
            True if removed, False if not found
        """
        # Remove from memory
        self._sensors.pop(sensor_id, None)
        self._records.pop(sensor_id, None)
        self._health.pop(sensor_id, None)

        # Remove from database
        deleted = self.repo.delete(sensor_id)
        if deleted:
            logger.info(f"Unregistered sensor: {sensor_id}")
        return deleted

    def get(self, sensor_id: str) -> Optional[Sensor]:
        """Get a sensor instance by ID.

        Args:
            sensor_id: Sensor ID

        Returns:
            Sensor instance or None
        """
        return self._sensors.get(sensor_id)

    def get_by_name(self, name: str) -> Optional[Sensor]:
        """Get a sensor instance by name.

        Args:
            name: Sensor name

        Returns:
            Sensor instance or None
        """
        for sid, record in self._records.items():
            if record.name == name:
                return self._sensors.get(sid)
        return None

    def remove(self, name: str) -> bool:
        """Remove a sensor by name.

        Args:
            name: Sensor name

        Returns:
            True if removed, False if not found
        """
        for sid, record in list(self._records.items()):
            if record.name == name:
                return self.unregister(sid)
        return False

    def add_from_config(
        self,
        name: str,
        sensor_type: str,
        location: tuple,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a sensor from configuration (convenience method).

        Args:
            name: Sensor name
            sensor_type: Type of sensor
            location: (x, y, z) location
            config: Type-specific config

        Returns:
            Sensor ID if successful, None if failed
        """
        return self.register(
            name=name,
            sensor_type=sensor_type,
            location=location,
            config=config or {},
            enabled=True,
        )

    def instantiate_from_record(self, record: SensorRecord) -> bool:
        """Instantiate a sensor from an existing database record.

        Use this when a sensor record already exists in the DB
        and you just want to create the runtime instance.

        Args:
            record: SensorRecord from database

        Returns:
            True if instantiated successfully, False otherwise
        """
        if record.id in self._sensors:
            # Already instantiated
            return True

        try:
            sensor = self._instantiate_sensor(record)
            if sensor:
                self._sensors[record.id] = sensor
                self._records[record.id] = record
                self._health[record.id] = SensorHealth(sensor_id=record.id, status="ok")
                logger.debug(f"Instantiated sensor: {record.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to instantiate sensor {record.name}: {e}")
            self._health[record.id] = SensorHealth(
                sensor_id=record.id, status="error", error=str(e)
            )
            return False

    def check_health_for(self, name: str) -> Dict[str, Any]:
        """Check health for a sensor by name.

        Args:
            name: Sensor name

        Returns:
            Health status dict
        """
        for sid, record in self._records.items():
            if record.name == name:
                health = self.test_sensor(sid)
                return health.to_dict()
        return {"status": "unknown", "error": "Sensor not found"}

    def get_record(self, sensor_id: str) -> Optional[SensorRecord]:
        """Get the database record for a sensor.

        Args:
            sensor_id: Sensor ID

        Returns:
            SensorRecord or None
        """
        return self._records.get(sensor_id)

    def list_all(self) -> Dict[str, Sensor]:
        """Get all registered sensor instances.

        Returns:
            Dict mapping sensor ID to Sensor instance
        """
        return self._sensors.copy()

    def list_records(self) -> List[SensorRecord]:
        """Get all sensor records (including disabled).

        Returns:
            List of SensorRecord objects
        """
        return self.repo.get_all()

    def update(
        self,
        sensor_id: str,
        name: Optional[str] = None,
        sensor_type: Optional[str] = None,
        location: Optional[tuple] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[SensorRecord]:
        """Update a sensor configuration.

        Args:
            sensor_id: Sensor ID to update
            name: New name (optional)
            sensor_type: New type (optional)
            location: New location (optional)
            config: New config (optional)
            enabled: New enabled state (optional)

        Returns:
            Updated SensorRecord or None if not found
        """
        record = self.repo.update(
            sensor_id=sensor_id,
            name=name,
            sensor_type=sensor_type,
            location=location,
            config=config,
            enabled=enabled,
        )

        if not record:
            return None

        # Reload sensor if type or config changed
        if sensor_type is not None or config is not None:
            # Remove old instance
            self._sensors.pop(sensor_id, None)

            # Reinstantiate if enabled
            if record.enabled:
                try:
                    sensor = self._instantiate_sensor(record)
                    if sensor:
                        self._sensors[sensor_id] = sensor
                        self._health[sensor_id] = SensorHealth(
                            sensor_id=sensor_id, status="ok"
                        )
                except Exception as e:
                    self._health[sensor_id] = SensorHealth(
                        sensor_id=sensor_id, status="error", error=str(e)
                    )

        # Update enabled state
        elif enabled is not None:
            if enabled and sensor_id not in self._sensors:
                try:
                    sensor = self._instantiate_sensor(record)
                    if sensor:
                        self._sensors[sensor_id] = sensor
                        self._health[sensor_id] = SensorHealth(
                            sensor_id=sensor_id, status="ok"
                        )
                except Exception as e:
                    self._health[sensor_id] = SensorHealth(
                        sensor_id=sensor_id, status="error", error=str(e)
                    )
            elif not enabled:
                self._sensors.pop(sensor_id, None)

        self._records[sensor_id] = record
        return record

    def test_sensor(self, sensor_id: str, timeout: float = 5.0) -> SensorHealth:
        """Test a sensor by reading its value.

        Args:
            sensor_id: Sensor ID to test
            timeout: Read timeout in seconds

        Returns:
            SensorHealth with test results
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return SensorHealth(
                sensor_id=sensor_id, status="error", error="Sensor not found"
            )

        try:
            start = time.time()
            value = sensor.read()
            elapsed = time.time() - start

            if elapsed > timeout:
                health = SensorHealth(
                    sensor_id=sensor_id,
                    status="timeout",
                    last_read=time.time(),
                    error=f"Read took {elapsed:.2f}s",
                )
            else:
                health = SensorHealth(
                    sensor_id=sensor_id,
                    status="ok",
                    last_read=time.time(),
                    last_value=value,
                )

            self._health[sensor_id] = health
            return health

        except Exception as e:
            health = SensorHealth(
                sensor_id=sensor_id,
                status="error",
                last_read=time.time(),
                error=str(e),
            )
            self._health[sensor_id] = health
            return health

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered sensors.

        Returns:
            Dict mapping sensor ID to health status dict
        """
        results = {}
        for sensor_id in self._sensors:
            health = self.test_sensor(sensor_id)
            results[sensor_id] = health.to_dict()
        return results

    def get_health(self, sensor_id: str) -> Optional[SensorHealth]:
        """Get cached health status for a sensor.

        Args:
            sensor_id: Sensor ID

        Returns:
            SensorHealth or None
        """
        return self._health.get(sensor_id)

    def count(self) -> int:
        """Get count of active sensors."""
        return len(self._sensors)

    def count_all(self) -> int:
        """Get count of all sensors (including disabled)."""
        return self.repo.count()

    @staticmethod
    def get_supported_types() -> List[str]:
        """Get list of supported sensor types.

        Returns:
            List of sensor type names
        """
        return list(SENSOR_TYPES.keys())

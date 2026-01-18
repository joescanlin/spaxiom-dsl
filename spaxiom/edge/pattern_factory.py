"""
Pattern Factory for Edge Deployment.

Creates pattern instances from stored configuration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from spaxiom.zone import Zone

if TYPE_CHECKING:
    from spaxiom.edge.database import EdgeDatabase, PatternRecord
    from spaxiom.edge.sensor_registry import PersistentSensorRegistry
    from spaxiom.intent.pattern import Pattern

logger = logging.getLogger(__name__)


class PatternFactory:
    """Factory for creating pattern instances from stored configuration."""

    def __init__(
        self,
        db: EdgeDatabase,
        sensor_registry: PersistentSensorRegistry,
    ):
        """Initialize the pattern factory.

        Args:
            db: Database connection
            sensor_registry: Sensor registry for resolving sensor references
        """
        self.db = db
        self.sensor_registry = sensor_registry
        self._zone_cache: Dict[str, Zone] = {}

    def _resolve_zones(self, zone_ids: List[str]) -> List[Zone]:
        """Resolve zone IDs to Zone instances.

        Args:
            zone_ids: List of zone IDs to resolve

        Returns:
            List of Zone instances
        """
        from spaxiom.edge.database import ZoneRepository

        zone_repo = ZoneRepository(self.db)
        zones = []

        for zone_id in zone_ids:
            if zone_id in self._zone_cache:
                zones.append(self._zone_cache[zone_id])
                continue

            record = zone_repo.get(zone_id)
            if record:
                zone = self._create_zone_from_record(record)
                self._zone_cache[zone_id] = zone
                zones.append(zone)
            else:
                logger.warning(f"Zone '{zone_id}' not found")

        return zones

    def _create_zone_from_record(self, record) -> Zone:
        """Create a Zone instance from a database record.

        Args:
            record: Zone record from database

        Returns:
            Zone instance
        """
        geometry = record.geometry or {}

        if record.zone_type == "rectangle":
            bounds = (
                geometry.get("x", 0),
                geometry.get("y", 0),
                geometry.get("x", 0) + geometry.get("width", 10),
                geometry.get("y", 0) + geometry.get("height", 10),
            )
        elif record.zone_type == "circle":
            cx = geometry.get("center_x", 0)
            cy = geometry.get("center_y", 0)
            r = geometry.get("radius", 5)
            bounds = (cx - r, cy - r, cx + r, cy + r)
        else:
            bounds = (0, 0, 10, 10)

        return Zone(name=record.name, bounds=bounds)

    def _resolve_sensors(self, sensor_ids: List[str]) -> List[Any]:
        """Resolve sensor IDs to sensor instances.

        Args:
            sensor_ids: List of sensor IDs to resolve

        Returns:
            List of sensor instances
        """
        sensors = []
        for sensor_id in sensor_ids:
            sensor = self.sensor_registry.get_by_id(sensor_id)
            if sensor:
                sensors.append(sensor)
            else:
                logger.warning(f"Sensor '{sensor_id}' not found in registry")
        return sensors

    def create(self, pattern_record: PatternRecord) -> Optional[Pattern]:
        """Create a pattern instance from stored configuration.

        Args:
            pattern_record: Pattern record from database

        Returns:
            Pattern instance or None if creation fails
        """
        pattern_type = pattern_record.pattern_type
        config = pattern_record.config or {}
        zone_ids = pattern_record.zones or []
        sensor_ids = pattern_record.sensors or []

        try:
            if pattern_type == "occupancy_field":
                return self._create_occupancy_field(config, zone_ids, sensor_ids)
            elif pattern_type == "queue_flow":
                return self._create_queue_flow(config, zone_ids, sensor_ids)
            elif pattern_type == "adl_tracker":
                return self._create_adl_tracker(config, zone_ids, sensor_ids)
            elif pattern_type == "fm_steward":
                return self._create_fm_steward(config, zone_ids, sensor_ids)
            else:
                logger.error(f"Unknown pattern type: {pattern_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create pattern '{pattern_record.name}': {e}")
            return None

    def _create_occupancy_field(
        self, config: Dict, zone_ids: List[str], sensor_ids: List[str]
    ) -> Optional[Pattern]:
        """Create an OccupancyField pattern."""
        from spaxiom.intent.occupancy_field import OccupancyField

        zones = self._resolve_zones(zone_ids)
        sensors = self._resolve_sensors(sensor_ids)

        if not zones:
            logger.error("OccupancyField requires at least one zone")
            return None
        if not sensors:
            logger.error("OccupancyField requires at least one sensor")
            return None

        return OccupancyField(
            zone=zones[0],
            sensor=sensors[0],
            decay_rate=config.get("decay_rate", 0.1),
        )

    def _create_queue_flow(
        self, config: Dict, zone_ids: List[str], sensor_ids: List[str]
    ) -> Optional[Pattern]:
        """Create a QueueFlow pattern."""
        from spaxiom.intent.queue_flow import QueueFlow

        zones = self._resolve_zones(zone_ids)
        sensors = self._resolve_sensors(sensor_ids)

        if len(zones) < 2:
            logger.error("QueueFlow requires at least two zones (entry and exit)")
            return None
        if not sensors:
            logger.error("QueueFlow requires at least one sensor")
            return None

        return QueueFlow(
            entry_zone=zones[0],
            exit_zone=zones[1],
            sensor=sensors[0],
            max_queue=config.get("max_queue_length", 10),
        )

    def _create_adl_tracker(
        self, config: Dict, zone_ids: List[str], sensor_ids: List[str]
    ) -> Optional[Pattern]:
        """Create an ADLTracker pattern."""
        from spaxiom.intent.adl_tracker import ADLTracker

        zones = self._resolve_zones(zone_ids)
        sensors = self._resolve_sensors(sensor_ids)

        if not zones:
            logger.error("ADLTracker requires at least one zone")
            return None

        return ADLTracker(
            zones=zones,
            sensors=sensors,
        )

    def _create_fm_steward(
        self, config: Dict, zone_ids: List[str], sensor_ids: List[str]
    ) -> Optional[Pattern]:
        """Create an FmSteward pattern."""
        from spaxiom.intent.fm_steward import FmSteward

        sensors = self._resolve_sensors(sensor_ids)

        if not sensors:
            logger.error("FmSteward requires at least one sensor")
            return None

        return FmSteward(
            sensors=sensors,
            thresholds=config.get("thresholds", {}),
        )

    def validate_config(
        self,
        pattern_type: str,
        config: Dict,
        zone_ids: List[str],
        sensor_ids: List[str],
    ) -> Dict[str, Any]:
        """Validate pattern configuration without creating the pattern.

        Args:
            pattern_type: Type of pattern
            config: Pattern configuration
            zone_ids: Zone IDs
            sensor_ids: Sensor IDs

        Returns:
            Validation result with 'valid', 'errors', 'warnings' keys
        """
        errors = []
        warnings = []

        # Check zones exist
        from spaxiom.edge.database import ZoneRepository

        zone_repo = ZoneRepository(self.db)
        for zone_id in zone_ids:
            if not zone_repo.get(zone_id):
                errors.append(f"Zone '{zone_id}' not found")

        # Check sensors exist
        for sensor_id in sensor_ids:
            if not self.sensor_registry.get_by_id(sensor_id):
                errors.append(f"Sensor '{sensor_id}' not found")

        # Pattern-specific validation
        if pattern_type == "occupancy_field":
            if not zone_ids:
                errors.append("OccupancyField requires at least one zone")
            if not sensor_ids:
                errors.append("OccupancyField requires at least one sensor")
        elif pattern_type == "queue_flow":
            if len(zone_ids) < 2:
                errors.append("QueueFlow requires at least two zones")
            if not sensor_ids:
                errors.append("QueueFlow requires at least one sensor")
        elif pattern_type == "adl_tracker":
            if not zone_ids:
                errors.append("ADLTracker requires at least one zone")
        elif pattern_type == "fm_steward":
            if not sensor_ids:
                errors.append("FmSteward requires at least one sensor")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

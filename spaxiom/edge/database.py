"""
SQLite database for edge deployment persistence.

Provides persistent storage for:
- Sensors: Registered sensors and configuration
- Zones: Defined spatial zones
- Patterns: Configured INTENT patterns
- Agents: Deployed agent instances
- Events: Event log with retention policy
- Settings: Key-value system settings
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)

# Current schema version for migrations
SCHEMA_VERSION = 1


@dataclass
class SensorRecord:
    """Database record for a sensor."""

    id: str
    name: str
    sensor_type: str
    location_x: Optional[float] = None
    location_y: Optional[float] = None
    location_z: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def location(self) -> Optional[tuple]:
        if self.location_x is not None:
            return (self.location_x, self.location_y or 0, self.location_z or 0)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SensorRecord":
        config = json.loads(row["config"]) if row["config"] else {}
        return cls(
            id=row["id"],
            name=row["name"],
            sensor_type=row["sensor_type"],
            location_x=row["location_x"],
            location_y=row["location_y"],
            location_z=row["location_z"],
            config=config,
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class ZoneRecord:
    """Database record for a zone."""

    id: str
    name: str
    zone_type: str = "rectangle"
    geometry: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ZoneRecord":
        geometry = json.loads(row["geometry"]) if row["geometry"] else {}
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        return cls(
            id=row["id"],
            name=row["name"],
            zone_type=row["zone_type"],
            geometry=geometry,
            metadata=metadata,
            created_at=row["created_at"],
        )


@dataclass
class PatternRecord:
    """Database record for a pattern."""

    id: str
    name: str
    pattern_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    zones: List[str] = field(default_factory=list)
    sensors: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PatternRecord":
        config = json.loads(row["config"]) if row["config"] else {}
        zones = json.loads(row["zones"]) if row["zones"] else []
        sensors = json.loads(row["sensors"]) if row["sensors"] else []
        return cls(
            id=row["id"],
            name=row["name"],
            pattern_type=row["pattern_type"],
            config=config,
            zones=zones,
            sensors=sensors,
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class AgentRecord:
    """Database record for an agent."""

    id: str
    name: str
    pattern_id: str
    status: str = "stopped"
    pid: Optional[int] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    last_error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AgentRecord":
        config = json.loads(row["config"]) if row["config"] else {}
        return cls(
            id=row["id"],
            name=row["name"],
            pattern_id=row["pattern_id"],
            status=row["status"],
            pid=row["pid"],
            started_at=row["started_at"],
            stopped_at=row["stopped_at"],
            last_error=row["last_error"],
            config=config,
        )


@dataclass
class EventRecord:
    """Database record for an event."""

    id: Optional[int]
    timestamp: str
    event_type: str
    source: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "EventRecord":
        data = json.loads(row["data"]) if row["data"] else {}
        return cls(
            id=row["id"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            source=row["source"],
            data=data,
            severity=row["severity"],
        )


class EdgeDatabase:
    """SQLite database manager for edge deployment."""

    def __init__(self, db_path: str = "spaxiom.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        """Initialize database schema."""
        with self.connection() as conn:
            self._create_tables(conn)
            self._set_schema_version(conn, SCHEMA_VERSION)
        logger.info(f"Database initialized at {self.db_path}")

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all tables if they don't exist."""
        conn.executescript("""
            -- Sensors table
            CREATE TABLE IF NOT EXISTS sensors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sensor_type TEXT NOT NULL,
                location_x REAL,
                location_y REAL,
                location_z REAL,
                config JSON,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Zones table
            CREATE TABLE IF NOT EXISTS zones (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                zone_type TEXT DEFAULT 'rectangle',
                geometry JSON NOT NULL,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Patterns table
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                pattern_type TEXT NOT NULL,
                config JSON NOT NULL,
                zones JSON,
                sensors JSON,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Agents table
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                status TEXT DEFAULT 'stopped',
                pid INTEGER,
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                last_error TEXT,
                config JSON,
                FOREIGN KEY (pattern_id) REFERENCES patterns(id)
            );

            -- Events table
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                source TEXT,
                data JSON,
                severity TEXT DEFAULT 'info'
            );

            -- Index for event cleanup by timestamp
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

            -- Index for event queries by type
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

            -- Settings table
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Schema version table
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );
            """)

    def _set_schema_version(self, conn: sqlite3.Connection, version: int) -> None:
        """Set the schema version."""
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))

    def get_schema_version(self) -> int:
        """Get current schema version."""
        with self.connection() as conn:
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            return row["version"] if row else 0

    def check_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            with self.connection() as conn:
                conn.execute("SELECT 1")
                size = self.db_path.stat().st_size if self.db_path.exists() else 0
            return {
                "status": "ok",
                "path": str(self.db_path),
                "size_bytes": size,
                "schema_version": self.get_schema_version(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class SensorRepository:
    """Repository for sensor CRUD operations."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def create(
        self,
        name: str,
        sensor_type: str,
        location: Optional[tuple] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> SensorRecord:
        """Create a new sensor record."""
        sensor_id = str(uuid.uuid4())
        loc_x, loc_y, loc_z = location if location else (None, None, None)
        config_json = json.dumps(config or {})
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO sensors (id, name, sensor_type, location_x, location_y, 
                                     location_z, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sensor_id,
                    name,
                    sensor_type,
                    loc_x,
                    loc_y,
                    loc_z,
                    config_json,
                    int(enabled),
                    now,
                    now,
                ),
            )

        return SensorRecord(
            id=sensor_id,
            name=name,
            sensor_type=sensor_type,
            location_x=loc_x,
            location_y=loc_y,
            location_z=loc_z,
            config=config or {},
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def get(self, sensor_id: str) -> Optional[SensorRecord]:
        """Get a sensor by ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM sensors WHERE id = ?", (sensor_id,)
            ).fetchone()
            return SensorRecord.from_row(row) if row else None

    def get_by_name(self, name: str) -> Optional[SensorRecord]:
        """Get a sensor by name."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM sensors WHERE name = ?", (name,)
            ).fetchone()
            return SensorRecord.from_row(row) if row else None

    def get_all(self, enabled_only: bool = False) -> List[SensorRecord]:
        """Get all sensors."""
        with self.db.connection() as conn:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM sensors WHERE enabled = 1"
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM sensors").fetchall()
            return [SensorRecord.from_row(row) for row in rows]

    def update(
        self,
        sensor_id: str,
        name: Optional[str] = None,
        sensor_type: Optional[str] = None,
        location: Optional[tuple] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[SensorRecord]:
        """Update a sensor record."""
        existing = self.get(sensor_id)
        if not existing:
            return None

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if sensor_type is not None:
            updates.append("sensor_type = ?")
            params.append(sensor_type)
        if location is not None:
            updates.extend(["location_x = ?", "location_y = ?", "location_z = ?"])
            params.extend(location)
        if config is not None:
            updates.append("config = ?")
            params.append(json.dumps(config))
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(int(enabled))

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(sensor_id)

        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE sensors SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        return self.get(sensor_id)

    def delete(self, sensor_id: str) -> bool:
        """Delete a sensor record."""
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM sensors WHERE id = ?", (sensor_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        """Get total sensor count."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM sensors").fetchone()
            return row["count"]


class ZoneRepository:
    """Repository for zone CRUD operations."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def create(
        self,
        name: str,
        zone_type: str,
        geometry: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ZoneRecord:
        """Create a new zone record."""
        zone_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO zones (id, name, zone_type, geometry, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    zone_id,
                    name,
                    zone_type,
                    json.dumps(geometry),
                    json.dumps(metadata or {}),
                    now,
                ),
            )

        return ZoneRecord(
            id=zone_id,
            name=name,
            zone_type=zone_type,
            geometry=geometry,
            metadata=metadata or {},
            created_at=now,
        )

    def get(self, zone_id: str) -> Optional[ZoneRecord]:
        """Get a zone by ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM zones WHERE id = ?", (zone_id,)
            ).fetchone()
            return ZoneRecord.from_row(row) if row else None

    def get_by_name(self, name: str) -> Optional[ZoneRecord]:
        """Get a zone by name."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM zones WHERE name = ?", (name,)).fetchone()
            return ZoneRecord.from_row(row) if row else None

    def get_all(self) -> List[ZoneRecord]:
        """Get all zones."""
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM zones").fetchall()
            return [ZoneRecord.from_row(row) for row in rows]

    def update(
        self,
        zone_id: str,
        name: Optional[str] = None,
        zone_type: Optional[str] = None,
        geometry: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ZoneRecord]:
        """Update a zone record."""
        existing = self.get(zone_id)
        if not existing:
            return None

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if zone_type is not None:
            updates.append("zone_type = ?")
            params.append(zone_type)
        if geometry is not None:
            updates.append("geometry = ?")
            params.append(json.dumps(geometry))
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return existing

        params.append(zone_id)

        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE zones SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        return self.get(zone_id)

    def delete(self, zone_id: str) -> bool:
        """Delete a zone record."""
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        """Get total zone count."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM zones").fetchone()
            return row["count"]


class PatternRepository:
    """Repository for pattern CRUD operations."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def create(
        self,
        name: str,
        pattern_type: str,
        config: Dict[str, Any],
        zones: Optional[List[str]] = None,
        sensors: Optional[List[str]] = None,
        enabled: bool = True,
    ) -> PatternRecord:
        """Create a new pattern record."""
        pattern_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO patterns (id, name, pattern_type, config, zones, sensors, 
                                      enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern_id,
                    name,
                    pattern_type,
                    json.dumps(config),
                    json.dumps(zones or []),
                    json.dumps(sensors or []),
                    int(enabled),
                    now,
                    now,
                ),
            )

        return PatternRecord(
            id=pattern_id,
            name=name,
            pattern_type=pattern_type,
            config=config,
            zones=zones or [],
            sensors=sensors or [],
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def get(self, pattern_id: str) -> Optional[PatternRecord]:
        """Get a pattern by ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM patterns WHERE id = ?", (pattern_id,)
            ).fetchone()
            return PatternRecord.from_row(row) if row else None

    def get_by_name(self, name: str) -> Optional[PatternRecord]:
        """Get a pattern by name."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM patterns WHERE name = ?", (name,)
            ).fetchone()
            return PatternRecord.from_row(row) if row else None

    def get_all(self, enabled_only: bool = False) -> List[PatternRecord]:
        """Get all patterns."""
        with self.db.connection() as conn:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM patterns WHERE enabled = 1"
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM patterns").fetchall()
            return [PatternRecord.from_row(row) for row in rows]

    def update(
        self,
        pattern_id: str,
        name: Optional[str] = None,
        pattern_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        zones: Optional[List[str]] = None,
        sensors: Optional[List[str]] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[PatternRecord]:
        """Update a pattern record."""
        existing = self.get(pattern_id)
        if not existing:
            return None

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if pattern_type is not None:
            updates.append("pattern_type = ?")
            params.append(pattern_type)
        if config is not None:
            updates.append("config = ?")
            params.append(json.dumps(config))
        if zones is not None:
            updates.append("zones = ?")
            params.append(json.dumps(zones))
        if sensors is not None:
            updates.append("sensors = ?")
            params.append(json.dumps(sensors))
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(int(enabled))

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(pattern_id)

        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE patterns SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        return self.get(pattern_id)

    def delete(self, pattern_id: str) -> bool:
        """Delete a pattern record."""
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        """Get total pattern count."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM patterns").fetchone()
            return row["count"]


class AgentRepository:
    """Repository for agent CRUD operations."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def create(
        self,
        name: str,
        pattern_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentRecord:
        """Create a new agent record."""
        agent_id = str(uuid.uuid4())

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO agents (id, name, pattern_id, status, config)
                VALUES (?, ?, ?, 'stopped', ?)
                """,
                (agent_id, name, pattern_id, json.dumps(config or {})),
            )

        return AgentRecord(
            id=agent_id,
            name=name,
            pattern_id=pattern_id,
            status="stopped",
            config=config or {},
        )

    def get(self, agent_id: str) -> Optional[AgentRecord]:
        """Get an agent by ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            ).fetchone()
            return AgentRecord.from_row(row) if row else None

    def get_all(self, status: Optional[str] = None) -> List[AgentRecord]:
        """Get all agents, optionally filtered by status."""
        with self.db.connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM agents WHERE status = ?", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM agents").fetchall()
            return [AgentRecord.from_row(row) for row in rows]

    def update_status(
        self,
        agent_id: str,
        status: str,
        pid: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentRecord]:
        """Update agent status."""
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            if status == "running":
                conn.execute(
                    """
                    UPDATE agents SET status = ?, pid = ?, started_at = ?, last_error = NULL
                    WHERE id = ?
                    """,
                    (status, pid, now, agent_id),
                )
            elif status == "stopped":
                conn.execute(
                    """
                    UPDATE agents SET status = ?, pid = NULL, stopped_at = ?
                    WHERE id = ?
                    """,
                    (status, now, agent_id),
                )
            elif status == "error":
                conn.execute(
                    """
                    UPDATE agents SET status = ?, last_error = ?, stopped_at = ?
                    WHERE id = ?
                    """,
                    (status, error, now, agent_id),
                )
            else:
                conn.execute(
                    "UPDATE agents SET status = ? WHERE id = ?",
                    (status, agent_id),
                )

        return self.get(agent_id)

    def delete(self, agent_id: str) -> bool:
        """Delete an agent record."""
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        """Get total agent count."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM agents").fetchone()
            return row["count"]


class EventRepository:
    """Repository for event logging and queries."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def log(
        self,
        event_type: str,
        source: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> EventRecord:
        """Log a new event."""
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (timestamp, event_type, source, data, severity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, event_type, source, json.dumps(data or {}), severity),
            )
            event_id = cursor.lastrowid

        return EventRecord(
            id=event_id,
            timestamp=now,
            event_type=event_type,
            source=source,
            data=data or {},
            severity=severity,
        )

    def query(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        """Query events with filters."""
        conditions = []
        params = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if until:
            conditions.append("timestamp <= ?")
            params.append(until)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with self.db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM events {where_clause}
                ORDER BY timestamp DESC LIMIT ?
                """,
                params,
            ).fetchall()
            return [EventRecord.from_row(row) for row in rows]

    def cleanup(self, max_age_days: int = 30) -> int:
        """Delete events older than max_age_days."""
        cutoff = datetime.utcnow()
        cutoff_ts = cutoff.timestamp() - (max_age_days * 24 * 60 * 60)
        cutoff_iso = datetime.utcfromtimestamp(cutoff_ts).isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE timestamp < ?", (cutoff_iso,)
            )
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} events older than {max_age_days} days")
            return deleted

    def count(self) -> int:
        """Get total event count."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM events").fetchone()
            return row["count"]


class SettingsRepository:
    """Repository for key-value settings."""

    def __init__(self, db: EdgeDatabase):
        self.db = db

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return default

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        now = datetime.utcnow().isoformat()

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
                """,
                (key, json.dumps(value), now, json.dumps(value), now),
            )

    def delete(self, key: str) -> bool:
        """Delete a setting."""
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        with self.db.connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {row["key"]: json.loads(row["value"]) for row in rows}

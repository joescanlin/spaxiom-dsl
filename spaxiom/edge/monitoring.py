"""
Health monitoring and alerts for Spaxiom Edge.

Provides:
- System health checks (disk, memory, CPU)
- Sensor connectivity monitoring
- Database health checks
- Alert management and delivery
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents a system alert."""

    id: str
    alert_type: str
    message: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "message": self.message,
            "severity": self.severity.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "data": self.data,
        }


@dataclass
class HealthCheck:
    """Result of a health check."""

    name: str
    healthy: bool
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "healthy": self.healthy,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
        }


def get_disk_usage(path: str = "/") -> dict:
    """Get disk usage statistics.

    Args:
        path: Path to check (default: root)

    Returns:
        Dictionary with total, used, free bytes and percent used
    """
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        percent = (used / total) * 100 if total > 0 else 0

        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "percent_used": round(percent, 1),
        }
    except Exception as e:
        logger.error(f"Error getting disk usage: {e}")
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "percent_used": 0,
            "error": str(e),
        }


def get_memory_usage() -> dict:
    """Get memory usage statistics.

    Returns:
        Dictionary with total, used, free bytes and percent used
    """
    try:
        # Try to read from /proc/meminfo (Linux)
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1]) * 1024  # Convert KB to bytes
                        meminfo[key] = value

            total = meminfo.get("MemTotal", 0)
            free = meminfo.get("MemFree", 0)
            buffers = meminfo.get("Buffers", 0)
            cached = meminfo.get("Cached", 0)
            available = meminfo.get("MemAvailable", free + buffers + cached)
            used = total - available
            percent = (used / total) * 100 if total > 0 else 0

            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "available_bytes": available,
                "percent_used": round(percent, 1),
            }
        else:
            # Fallback for macOS/other systems
            import subprocess

            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Parse vm_stat output (macOS)
                lines = result.stdout.split("\n")
                page_size = 4096  # Default page size

                stats = {}
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        value = value.strip().rstrip(".")
                        try:
                            stats[key.strip()] = int(value) * page_size
                        except ValueError:
                            pass

                free = stats.get("Pages free", 0)
                active = stats.get("Pages active", 0)
                inactive = stats.get("Pages inactive", 0)
                wired = stats.get("Pages wired down", 0)
                used = active + wired
                total = free + active + inactive + wired
                percent = (used / total) * 100 if total > 0 else 0

                return {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "percent_used": round(percent, 1),
                }

            return {"error": "Unable to get memory info"}

    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return {"error": str(e)}


def get_cpu_usage(interval: float = 0.1) -> dict:
    """Get CPU usage statistics.

    Args:
        interval: Measurement interval in seconds

    Returns:
        Dictionary with CPU usage percent
    """
    try:
        # Try to read from /proc/stat (Linux)
        if os.path.exists("/proc/stat"):

            def read_cpu_times():
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                    parts = line.split()
                    # user, nice, system, idle, iowait, irq, softirq
                    times = [int(x) for x in parts[1:8]]
                    idle = times[3] + times[4]  # idle + iowait
                    total = sum(times)
                    return idle, total

            idle1, total1 = read_cpu_times()
            time.sleep(interval)
            idle2, total2 = read_cpu_times()

            idle_delta = idle2 - idle1
            total_delta = total2 - total1
            usage = (
                ((total_delta - idle_delta) / total_delta) * 100
                if total_delta > 0
                else 0
            )

            return {"percent_used": round(usage, 1)}
        else:
            # Fallback - return unknown
            return {"percent_used": None, "error": "CPU stats not available"}

    except Exception as e:
        logger.error(f"Error getting CPU usage: {e}")
        return {"error": str(e)}


def get_uptime() -> float:
    """Get system uptime in seconds.

    Returns:
        Uptime in seconds, or 0 if unavailable
    """
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                uptime = float(f.readline().split()[0])
                return uptime
        else:
            # macOS fallback
            import subprocess

            result = subprocess.run(
                ["sysctl", "-n", "kern.boottime"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse boot time
                import re

                match = re.search(r"sec = (\d+)", result.stdout)
                if match:
                    boot_time = int(match.group(1))
                    return time.time() - boot_time
        return 0
    except Exception as e:
        logger.error(f"Error getting uptime: {e}")
        return 0


class HealthMonitor:
    """Monitors system health and generates alerts."""

    def __init__(
        self,
        disk_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        cpu_threshold: float = 90.0,
        check_interval: int = 60,
    ):
        """Initialize health monitor.

        Args:
            disk_threshold: Alert when disk usage exceeds this percent
            memory_threshold: Alert when memory usage exceeds this percent
            cpu_threshold: Alert when CPU usage exceeds this percent (sustained)
            check_interval: Seconds between health checks
        """
        self.disk_threshold = disk_threshold
        self.memory_threshold = memory_threshold
        self.cpu_threshold = cpu_threshold
        self.check_interval = check_interval

        self._alerts: Dict[str, Alert] = {}
        self._alert_counter = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[Alert], None]] = []

        # Track sustained high CPU
        self._high_cpu_count = 0
        self._high_cpu_threshold_count = 3  # 3 consecutive checks

    def add_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add alert callback.

        Args:
            callback: Function called when new alert is created
        """
        self._callbacks.append(callback)

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"alert_{int(time.time())}_{self._alert_counter}"

    def _create_alert(
        self,
        alert_type: str,
        message: str,
        severity: AlertSeverity,
        data: Optional[dict] = None,
    ) -> Alert:
        """Create and store a new alert.

        Args:
            alert_type: Type of alert (disk_high, memory_high, etc.)
            message: Alert message
            severity: Alert severity
            data: Additional alert data

        Returns:
            Created alert
        """
        alert = Alert(
            id=self._generate_alert_id(),
            alert_type=alert_type,
            message=message,
            severity=severity,
            data=data or {},
        )

        self._alerts[alert.id] = alert

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(f"Alert created: [{severity.value}] {message}")
        return alert

    def _resolve_alerts_of_type(self, alert_type: str) -> None:
        """Resolve all active alerts of a given type."""
        for alert in self._alerts.values():
            if alert.alert_type == alert_type and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                logger.info(f"Alert resolved: {alert.message}")

    def check_disk(self, path: str = "/") -> HealthCheck:
        """Check disk health.

        Args:
            path: Path to check

        Returns:
            HealthCheck result
        """
        usage = get_disk_usage(path)

        if "error" in usage:
            return HealthCheck(
                name="disk",
                healthy=False,
                message=f"Error checking disk: {usage['error']}",
            )

        percent = usage["percent_used"]
        healthy = percent < self.disk_threshold

        if not healthy:
            # Create alert if not already active
            existing = [
                a
                for a in self._alerts.values()
                if a.alert_type == "disk_high" and a.status == AlertStatus.ACTIVE
            ]
            if not existing:
                self._create_alert(
                    "disk_high",
                    f"Disk usage at {percent}% (threshold: {self.disk_threshold}%)",
                    AlertSeverity.WARNING if percent < 95 else AlertSeverity.CRITICAL,
                    data=usage,
                )
        else:
            self._resolve_alerts_of_type("disk_high")

        return HealthCheck(
            name="disk",
            healthy=healthy,
            message=f"Disk usage: {percent}%",
            value=percent,
            threshold=self.disk_threshold,
        )

    def check_memory(self) -> HealthCheck:
        """Check memory health.

        Returns:
            HealthCheck result
        """
        usage = get_memory_usage()

        if "error" in usage:
            return HealthCheck(
                name="memory",
                healthy=False,
                message=f"Error checking memory: {usage['error']}",
            )

        percent = usage["percent_used"]
        healthy = percent < self.memory_threshold

        if not healthy:
            existing = [
                a
                for a in self._alerts.values()
                if a.alert_type == "memory_high" and a.status == AlertStatus.ACTIVE
            ]
            if not existing:
                self._create_alert(
                    "memory_high",
                    f"Memory usage at {percent}% (threshold: {self.memory_threshold}%)",
                    AlertSeverity.WARNING if percent < 95 else AlertSeverity.CRITICAL,
                    data=usage,
                )
        else:
            self._resolve_alerts_of_type("memory_high")

        return HealthCheck(
            name="memory",
            healthy=healthy,
            message=f"Memory usage: {percent}%",
            value=percent,
            threshold=self.memory_threshold,
        )

    def check_cpu(self) -> HealthCheck:
        """Check CPU health.

        Returns:
            HealthCheck result
        """
        usage = get_cpu_usage()

        if "error" in usage or usage.get("percent_used") is None:
            return HealthCheck(
                name="cpu",
                healthy=True,
                message="CPU stats not available",
            )

        percent = usage["percent_used"]

        # Track sustained high CPU
        if percent >= self.cpu_threshold:
            self._high_cpu_count += 1
        else:
            self._high_cpu_count = 0

        healthy = self._high_cpu_count < self._high_cpu_threshold_count

        if not healthy:
            existing = [
                a
                for a in self._alerts.values()
                if a.alert_type == "cpu_high" and a.status == AlertStatus.ACTIVE
            ]
            if not existing:
                self._create_alert(
                    "cpu_high",
                    f"CPU usage sustained at {percent}% (threshold: {self.cpu_threshold}%)",
                    AlertSeverity.WARNING,
                    data=usage,
                )
        else:
            self._resolve_alerts_of_type("cpu_high")

        return HealthCheck(
            name="cpu",
            healthy=healthy,
            message=f"CPU usage: {percent}%",
            value=percent,
            threshold=self.cpu_threshold,
        )

    def check_all(self) -> Dict[str, HealthCheck]:
        """Run all health checks.

        Returns:
            Dictionary of check name to HealthCheck result
        """
        return {
            "disk": self.check_disk(),
            "memory": self.check_memory(),
            "cpu": self.check_cpu(),
        }

    def get_overall_health(self) -> dict:
        """Get overall system health status.

        Returns:
            Dictionary with health status and checks
        """
        checks = self.check_all()
        all_healthy = all(check.healthy for check in checks.values())

        active_alerts = [
            a.to_dict() for a in self._alerts.values() if a.status == AlertStatus.ACTIVE
        ]

        return {
            "healthy": all_healthy,
            "checks": {name: check.to_dict() for name, check in checks.items()},
            "active_alerts": len(active_alerts),
            "alerts": active_alerts,
            "uptime_seconds": get_uptime(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts with optional filtering.

        Args:
            status: Filter by status
            severity: Filter by severity
            limit: Maximum number of alerts to return

        Returns:
            List of matching alerts
        """
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by created_at descending
        alerts.sort(key=lambda a: a.created_at, reverse=True)

        return alerts[:limit]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if alert was acknowledged
        """
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            if alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if alert was resolved
        """
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            if alert.status != AlertStatus.RESOLVED:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                return True
        return False

    def clear_resolved_alerts(self, max_age_hours: int = 24) -> int:
        """Clear old resolved alerts.

        Args:
            max_age_hours: Maximum age of resolved alerts to keep

        Returns:
            Number of alerts cleared
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        to_remove = []

        for alert_id, alert in self._alerts.items():
            if alert.status == AlertStatus.RESOLVED:
                if alert.resolved_at and alert.resolved_at.timestamp() < cutoff:
                    to_remove.append(alert_id)

        for alert_id in to_remove:
            del self._alerts[alert_id]

        return len(to_remove)

    async def start(self) -> None:
        """Start background health monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Health monitor started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                self.check_all()
                self.clear_resolved_alerts()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.check_interval)

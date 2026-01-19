"""Tests for health monitoring and alerts."""

import pytest

from spaxiom.edge.monitoring import (
    Alert,
    AlertSeverity,
    AlertStatus,
    HealthCheck,
    HealthMonitor,
    get_disk_usage,
    get_memory_usage,
    get_uptime,
)


class TestSystemMetrics:
    """Tests for system metric functions."""

    def test_get_disk_usage_returns_dict(self):
        """Test that get_disk_usage returns expected structure."""
        usage = get_disk_usage("/")

        assert isinstance(usage, dict)
        if "error" not in usage:
            assert "total_bytes" in usage
            assert "used_bytes" in usage
            assert "free_bytes" in usage
            assert "percent_used" in usage
            assert usage["total_bytes"] > 0

    def test_get_memory_usage_returns_dict(self):
        """Test that get_memory_usage returns expected structure."""
        usage = get_memory_usage()

        assert isinstance(usage, dict)
        if "error" not in usage:
            assert "percent_used" in usage

    def test_get_uptime_returns_number(self):
        """Test that get_uptime returns a number."""
        uptime = get_uptime()
        assert isinstance(uptime, (int, float))
        assert uptime >= 0


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            id="test_1",
            alert_type="disk_high",
            message="Disk usage high",
            severity=AlertSeverity.WARNING,
        )

        assert alert.id == "test_1"
        assert alert.alert_type == "disk_high"
        assert alert.message == "Disk usage high"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE
        assert alert.created_at is not None

    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = Alert(
            id="test_1",
            alert_type="memory_high",
            message="Memory usage high",
            severity=AlertSeverity.CRITICAL,
            data={"percent": 95},
        )

        d = alert.to_dict()

        assert d["id"] == "test_1"
        assert d["alert_type"] == "memory_high"
        assert d["severity"] == "critical"
        assert d["status"] == "active"
        assert d["data"]["percent"] == 95


class TestHealthCheck:
    """Tests for HealthCheck dataclass."""

    def test_health_check_creation(self):
        """Test creating a health check."""
        check = HealthCheck(
            name="disk",
            healthy=True,
            message="Disk OK",
            value=50.0,
            threshold=90.0,
        )

        assert check.name == "disk"
        assert check.healthy is True
        assert check.value == 50.0
        assert check.threshold == 90.0

    def test_health_check_to_dict(self):
        """Test health check serialization."""
        check = HealthCheck(
            name="memory",
            healthy=False,
            message="Memory high",
            value=95.0,
            threshold=85.0,
        )

        d = check.to_dict()

        assert d["name"] == "memory"
        assert d["healthy"] is False
        assert d["value"] == 95.0


class TestHealthMonitor:
    """Tests for HealthMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a health monitor."""
        return HealthMonitor(
            disk_threshold=90.0,
            memory_threshold=85.0,
            cpu_threshold=90.0,
        )

    def test_check_disk(self, monitor):
        """Test disk health check."""
        check = monitor.check_disk("/")

        assert check.name == "disk"
        assert isinstance(check.healthy, bool)
        assert check.threshold == 90.0

    def test_check_memory(self, monitor):
        """Test memory health check."""
        check = monitor.check_memory()

        assert check.name == "memory"
        assert isinstance(check.healthy, bool)

    def test_check_cpu(self, monitor):
        """Test CPU health check."""
        check = monitor.check_cpu()

        assert check.name == "cpu"
        # CPU check always returns healthy=True unless sustained high

    def test_check_all(self, monitor):
        """Test running all health checks."""
        checks = monitor.check_all()

        assert "disk" in checks
        assert "memory" in checks
        assert "cpu" in checks

    def test_get_overall_health(self, monitor):
        """Test getting overall health status."""
        health = monitor.get_overall_health()

        assert "healthy" in health
        assert "checks" in health
        assert "active_alerts" in health
        assert "uptime_seconds" in health

    def test_create_alert_on_threshold_exceeded(self):
        """Test that alerts are created when thresholds are exceeded."""
        # Use a very low threshold to trigger alert
        monitor = HealthMonitor(disk_threshold=0.1)

        check = monitor.check_disk("/")

        # Should have created an alert since disk usage > 0.1%
        if not check.healthy:
            alerts = monitor.get_alerts(status=AlertStatus.ACTIVE)
            assert len(alerts) > 0
            assert alerts[0].alert_type == "disk_high"

    def test_alert_callback(self, monitor):
        """Test that alert callbacks are called."""
        alerts_received = []

        def callback(alert):
            alerts_received.append(alert)

        monitor.add_callback(callback)

        # Manually create an alert
        monitor._create_alert(
            "test_alert",
            "Test message",
            AlertSeverity.INFO,
        )

        assert len(alerts_received) == 1
        assert alerts_received[0].alert_type == "test_alert"

    def test_acknowledge_alert(self, monitor):
        """Test acknowledging an alert."""
        alert = monitor._create_alert(
            "test_alert",
            "Test message",
            AlertSeverity.WARNING,
        )

        assert alert.status == AlertStatus.ACTIVE

        result = monitor.acknowledge_alert(alert.id)

        assert result is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None

    def test_resolve_alert(self, monitor):
        """Test resolving an alert."""
        alert = monitor._create_alert(
            "test_alert",
            "Test message",
            AlertSeverity.WARNING,
        )

        result = monitor.resolve_alert(alert.id)

        assert result is True
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_get_alerts_filtering(self, monitor):
        """Test filtering alerts."""
        # Create alerts with different severities
        monitor._create_alert("type1", "Info alert", AlertSeverity.INFO)
        monitor._create_alert("type2", "Warning alert", AlertSeverity.WARNING)
        monitor._create_alert("type3", "Critical alert", AlertSeverity.CRITICAL)

        # Filter by severity
        warnings = monitor.get_alerts(severity=AlertSeverity.WARNING)
        assert len(warnings) == 1
        assert warnings[0].severity == AlertSeverity.WARNING

        # Get all
        all_alerts = monitor.get_alerts()
        assert len(all_alerts) == 3

    def test_clear_resolved_alerts(self, monitor):
        """Test clearing old resolved alerts."""
        # Create and resolve an alert
        alert = monitor._create_alert("test", "Test", AlertSeverity.INFO)
        monitor.resolve_alert(alert.id)

        # Clear with 0 hour max age (should clear all resolved)
        cleared = monitor.clear_resolved_alerts(max_age_hours=0)

        assert cleared == 1
        assert len(monitor.get_alerts()) == 0

    def test_resolve_alerts_of_type(self, monitor):
        """Test resolving all alerts of a type."""
        monitor._create_alert("disk_high", "Disk 1", AlertSeverity.WARNING)
        monitor._create_alert("disk_high", "Disk 2", AlertSeverity.WARNING)
        monitor._create_alert("memory_high", "Memory", AlertSeverity.WARNING)

        monitor._resolve_alerts_of_type("disk_high")

        disk_alerts = [a for a in monitor.get_alerts() if a.alert_type == "disk_high"]
        memory_alerts = [
            a for a in monitor.get_alerts() if a.alert_type == "memory_high"
        ]

        assert all(a.status == AlertStatus.RESOLVED for a in disk_alerts)
        assert all(a.status == AlertStatus.ACTIVE for a in memory_alerts)


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertStatus:
    """Tests for AlertStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"

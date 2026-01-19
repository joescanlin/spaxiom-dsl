"""Tests for remote access and cloud connectivity."""

import pytest

from spaxiom.edge.remote import (
    ConnectionStatus,
    RemoteConfig,
    TelemetryData,
    CloudConnector,
    sign_request,
    create_connector_from_env,
)


class TestRemoteConfig:
    """Tests for RemoteConfig."""

    def test_config_creation(self):
        """Test creating remote config."""
        config = RemoteConfig(
            api_url="https://cloud.example.com",
            device_id="device-123",
            api_key="key-abc",
            api_secret="secret-xyz",
        )

        assert config.api_url == "https://cloud.example.com"
        assert config.device_id == "device-123"
        assert config.heartbeat_interval == 60
        assert config.enabled is True

    def test_config_to_dict_excludes_secrets(self):
        """Test that to_dict excludes API secret."""
        config = RemoteConfig(
            api_url="https://cloud.example.com",
            device_id="device-123",
            api_key="key-abc",
            api_secret="secret-xyz",
        )

        d = config.to_dict()

        assert "api_url" in d
        assert "device_id" in d
        assert "api_key" not in d
        assert "api_secret" not in d


class TestTelemetryData:
    """Tests for TelemetryData."""

    def test_telemetry_creation(self):
        """Test creating telemetry data."""
        data = TelemetryData(
            metric="cpu_usage",
            value=45.5,
            tags={"host": "edge-1"},
        )

        assert data.metric == "cpu_usage"
        assert data.value == 45.5
        assert data.tags["host"] == "edge-1"
        assert data.timestamp is not None

    def test_telemetry_to_dict(self):
        """Test telemetry serialization."""
        data = TelemetryData(
            metric="memory_usage",
            value=72.3,
        )

        d = data.to_dict()

        assert d["metric"] == "memory_usage"
        assert d["value"] == 72.3
        assert "timestamp" in d


class TestSignRequest:
    """Tests for request signing."""

    def test_sign_request(self):
        """Test signing a request."""
        signature = sign_request(
            method="POST",
            path="/api/v1/heartbeat",
            body='{"status": "online"}',
            timestamp="2024-01-01T00:00:00Z",
            api_secret="test-secret",
        )

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest

    def test_different_inputs_different_signatures(self):
        """Test that different inputs produce different signatures."""
        sig1 = sign_request("POST", "/path1", "{}", "2024-01-01T00:00:00Z", "secret")
        sig2 = sign_request("POST", "/path2", "{}", "2024-01-01T00:00:00Z", "secret")

        assert sig1 != sig2

    def test_same_inputs_same_signature(self):
        """Test that same inputs produce same signature."""
        sig1 = sign_request("POST", "/path", "{}", "2024-01-01T00:00:00Z", "secret")
        sig2 = sign_request("POST", "/path", "{}", "2024-01-01T00:00:00Z", "secret")

        assert sig1 == sig2


class TestCloudConnector:
    """Tests for CloudConnector."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return RemoteConfig(
            api_url="https://cloud.example.com",
            device_id="test-device",
            api_key="test-key",
            api_secret="test-secret",
        )

    @pytest.fixture
    def connector(self, config):
        """Create cloud connector."""
        return CloudConnector(config)

    def test_initial_status_disconnected(self, connector):
        """Test initial connection status."""
        assert connector.status == ConnectionStatus.DISCONNECTED

    def test_add_command_handler(self, connector):
        """Test registering command handler."""

        def handler():
            pass

        connector.add_command_handler("test_cmd", handler)

        assert "test_cmd" in connector._command_handlers

    def test_queue_telemetry(self, connector):
        """Test queueing telemetry data."""
        data = TelemetryData(metric="test", value=1.0)

        connector.queue_telemetry(data)

        assert len(connector._telemetry_buffer) == 1
        assert connector._telemetry_buffer[0].metric == "test"

    def test_telemetry_buffer_limit(self, connector):
        """Test that telemetry buffer is limited."""
        for i in range(1100):
            connector.queue_telemetry(TelemetryData(metric=f"m{i}", value=float(i)))

        assert len(connector._telemetry_buffer) == 1000

    def test_get_status(self, connector):
        """Test getting connector status."""
        status = connector.get_status()

        assert status["status"] == "disconnected"
        assert status["enabled"] is True
        assert status["device_id"] == "test-device"
        assert status["error_count"] == 0

    def test_disabled_connector_does_not_start(self):
        """Test that disabled connector doesn't connect."""
        config = RemoteConfig(
            api_url="https://cloud.example.com",
            device_id="test-device",
            api_key="test-key",
            api_secret="test-secret",
            enabled=False,
        )
        connector = CloudConnector(config)

        # Should return False when disabled
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(connector.connect())

        assert result is False


class TestConnectionStatus:
    """Tests for ConnectionStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.ERROR.value == "error"


class TestCreateConnectorFromEnv:
    """Tests for create_connector_from_env."""

    def test_returns_none_when_not_configured(self, monkeypatch):
        """Test that None is returned when env vars are missing."""
        monkeypatch.delenv("SPAXIOM_CLOUD_URL", raising=False)
        monkeypatch.delenv("SPAXIOM_DEVICE_ID", raising=False)
        monkeypatch.delenv("SPAXIOM_API_KEY", raising=False)
        monkeypatch.delenv("SPAXIOM_API_SECRET", raising=False)

        connector = create_connector_from_env()

        assert connector is None

    def test_creates_connector_when_configured(self, monkeypatch):
        """Test that connector is created when env vars are set."""
        monkeypatch.setenv("SPAXIOM_CLOUD_URL", "https://cloud.example.com")
        monkeypatch.setenv("SPAXIOM_DEVICE_ID", "device-123")
        monkeypatch.setenv("SPAXIOM_API_KEY", "key-abc")
        monkeypatch.setenv("SPAXIOM_API_SECRET", "secret-xyz")

        connector = create_connector_from_env()

        assert connector is not None
        assert connector.config.api_url == "https://cloud.example.com"
        assert connector.config.device_id == "device-123"

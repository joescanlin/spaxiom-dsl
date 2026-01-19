"""
Remote access and cloud connectivity for Spaxiom Edge.

Provides:
- Optional cloud connector for remote monitoring
- Telemetry upload
- Remote command execution
- Heartbeat/status reporting
"""

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Check for httpx availability
try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class ConnectionStatus(str, Enum):
    """Cloud connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class RemoteConfig:
    """Configuration for remote cloud connection."""

    api_url: str
    device_id: str
    api_key: str
    api_secret: str
    heartbeat_interval: int = 60  # seconds
    telemetry_interval: int = 300  # seconds
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary (without secrets)."""
        return {
            "api_url": self.api_url,
            "device_id": self.device_id,
            "heartbeat_interval": self.heartbeat_interval,
            "telemetry_interval": self.telemetry_interval,
            "enabled": self.enabled,
        }


@dataclass
class TelemetryData:
    """Telemetry data point."""

    metric: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


def sign_request(
    method: str,
    path: str,
    body: str,
    timestamp: str,
    api_secret: str,
) -> str:
    """Generate HMAC signature for API request.

    Args:
        method: HTTP method
        path: Request path
        body: Request body (JSON string)
        timestamp: ISO timestamp
        api_secret: API secret key

    Returns:
        HMAC-SHA256 signature
    """
    message = f"{method}\n{path}\n{body}\n{timestamp}"
    signature = hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature


class CloudConnector:
    """Handles connection to cloud service for remote monitoring."""

    def __init__(self, config: RemoteConfig):
        """Initialize cloud connector.

        Args:
            config: Remote configuration
        """
        self.config = config
        self._status = ConnectionStatus.DISCONNECTED
        self._last_heartbeat: Optional[datetime] = None
        self._last_telemetry: Optional[datetime] = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._telemetry_task: Optional[asyncio.Task] = None
        self._telemetry_buffer: List[TelemetryData] = []
        self._command_handlers: Dict[str, Callable] = {}
        self._error_count = 0
        self._max_errors = 5

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status

    def add_command_handler(self, command: str, handler: Callable) -> None:
        """Register a handler for remote commands.

        Args:
            command: Command name
            handler: Async function to handle command
        """
        self._command_handlers[command] = handler
        logger.debug(f"Registered command handler: {command}")

    def queue_telemetry(self, data: TelemetryData) -> None:
        """Queue telemetry data for upload.

        Args:
            data: Telemetry data point
        """
        self._telemetry_buffer.append(data)

        # Limit buffer size
        if len(self._telemetry_buffer) > 1000:
            self._telemetry_buffer = self._telemetry_buffer[-1000:]

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make authenticated API request.

        Args:
            method: HTTP method
            path: API path
            data: Request data

        Returns:
            Response data or None on error
        """
        if not HAS_HTTPX:
            logger.warning("httpx not installed, remote access disabled")
            return None

        url = urljoin(self.config.api_url, path)
        body = json.dumps(data) if data else ""
        timestamp = datetime.now(timezone.utc).isoformat()

        signature = sign_request(
            method,
            path,
            body,
            timestamp,
            self.config.api_secret,
        )

        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": self.config.device_id,
            "X-API-Key": self.config.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, content=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, content=body)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code == 200:
                    self._error_count = 0
                    return response.json()
                else:
                    logger.warning(
                        f"API request failed: {response.status_code} {response.text}"
                    )
                    self._error_count += 1
                    return None

        except Exception as e:
            logger.error(f"API request error: {e}")
            self._error_count += 1
            return None

    async def send_heartbeat(self) -> bool:
        """Send heartbeat to cloud service.

        Returns:
            True if successful
        """
        data = {
            "device_id": self.config.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "online",
        }

        result = await self._make_request("POST", "/api/v1/heartbeat", data)

        if result:
            self._last_heartbeat = datetime.now(timezone.utc)

            # Check for pending commands
            if "commands" in result:
                await self._process_commands(result["commands"])

            return True

        return False

    async def send_telemetry(self, data: List[TelemetryData]) -> bool:
        """Send telemetry data to cloud service.

        Args:
            data: List of telemetry data points

        Returns:
            True if successful
        """
        if not data:
            return True

        payload = {
            "device_id": self.config.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": [d.to_dict() for d in data],
        }

        result = await self._make_request("POST", "/api/v1/telemetry", payload)

        if result:
            self._last_telemetry = datetime.now(timezone.utc)
            return True

        return False

    async def _process_commands(self, commands: List[dict]) -> None:
        """Process remote commands.

        Args:
            commands: List of command objects
        """
        for cmd in commands:
            cmd_name = cmd.get("command")
            cmd_id = cmd.get("id")
            cmd_args = cmd.get("args", {})

            if cmd_name in self._command_handlers:
                try:
                    handler = self._command_handlers[cmd_name]
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(**cmd_args)
                    else:
                        result = handler(**cmd_args)

                    # Report command result
                    await self._make_request(
                        "POST",
                        f"/api/v1/commands/{cmd_id}/result",
                        {"status": "success", "result": result},
                    )

                except Exception as e:
                    logger.error(f"Command {cmd_name} failed: {e}")
                    await self._make_request(
                        "POST",
                        f"/api/v1/commands/{cmd_id}/result",
                        {"status": "error", "error": str(e)},
                    )
            else:
                logger.warning(f"Unknown command: {cmd_name}")

    async def connect(self) -> bool:
        """Establish connection to cloud service.

        Returns:
            True if connected successfully
        """
        if not self.config.enabled:
            logger.info("Remote access disabled")
            return False

        if not HAS_HTTPX:
            logger.warning("httpx not installed, cannot connect to cloud")
            self._status = ConnectionStatus.ERROR
            return False

        self._status = ConnectionStatus.CONNECTING
        logger.info(f"Connecting to cloud: {self.config.api_url}")

        # Send initial heartbeat to verify connection
        if await self.send_heartbeat():
            self._status = ConnectionStatus.CONNECTED
            logger.info("Connected to cloud service")
            return True
        else:
            self._status = ConnectionStatus.ERROR
            logger.error("Failed to connect to cloud service")
            return False

    async def disconnect(self) -> None:
        """Disconnect from cloud service."""
        self._status = ConnectionStatus.DISCONNECTED
        logger.info("Disconnected from cloud service")

    async def start(self) -> None:
        """Start background tasks for heartbeat and telemetry."""
        if self._running:
            return

        if not self.config.enabled:
            return

        self._running = True

        # Connect first
        await self.connect()

        if self._status == ConnectionStatus.CONNECTED:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._telemetry_task = asyncio.create_task(self._telemetry_loop())
            logger.info("Remote access background tasks started")

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False

        for task in [self._heartbeat_task, self._telemetry_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.disconnect()
        logger.info("Remote access stopped")

    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop."""
        while self._running:
            try:
                if not await self.send_heartbeat():
                    if self._error_count >= self._max_errors:
                        self._status = ConnectionStatus.ERROR
                        logger.error("Too many heartbeat failures, marking as error")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(self.config.heartbeat_interval)

    async def _telemetry_loop(self) -> None:
        """Background telemetry upload loop."""
        while self._running:
            await asyncio.sleep(self.config.telemetry_interval)

            try:
                if self._telemetry_buffer:
                    # Take buffered data
                    data = self._telemetry_buffer.copy()
                    self._telemetry_buffer.clear()

                    if not await self.send_telemetry(data):
                        # Put back on failure
                        self._telemetry_buffer = data + self._telemetry_buffer
            except Exception as e:
                logger.error(f"Telemetry error: {e}")

    def get_status(self) -> dict:
        """Get connector status.

        Returns:
            Status dictionary
        """
        return {
            "status": self._status.value,
            "enabled": self.config.enabled,
            "api_url": self.config.api_url,
            "device_id": self.config.device_id,
            "last_heartbeat": (
                self._last_heartbeat.isoformat() if self._last_heartbeat else None
            ),
            "last_telemetry": (
                self._last_telemetry.isoformat() if self._last_telemetry else None
            ),
            "error_count": self._error_count,
            "telemetry_buffer_size": len(self._telemetry_buffer),
        }


def create_connector_from_env() -> Optional[CloudConnector]:
    """Create cloud connector from environment variables.

    Environment variables:
        SPAXIOM_CLOUD_URL: Cloud API URL
        SPAXIOM_DEVICE_ID: Device identifier
        SPAXIOM_API_KEY: API key
        SPAXIOM_API_SECRET: API secret

    Returns:
        CloudConnector or None if not configured
    """
    import os

    api_url = os.environ.get("SPAXIOM_CLOUD_URL")
    device_id = os.environ.get("SPAXIOM_DEVICE_ID")
    api_key = os.environ.get("SPAXIOM_API_KEY")
    api_secret = os.environ.get("SPAXIOM_API_SECRET")

    if not all([api_url, device_id, api_key, api_secret]):
        return None

    config = RemoteConfig(
        api_url=api_url,
        device_id=device_id,
        api_key=api_key,
        api_secret=api_secret,
    )

    return CloudConnector(config)

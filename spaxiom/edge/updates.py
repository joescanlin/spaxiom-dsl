"""
Software update management for Spaxiom Edge.

Provides:
- Version checking
- Update download and installation
- Rollback support
- Update scheduling
"""

import asyncio
import hashlib
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


# Current version from package
def get_current_version() -> str:
    """Get current installed version."""
    try:
        from spaxiom import __version__

        return __version__
    except ImportError:
        return "0.0.0"


class UpdateStatus(str, Enum):
    """Update status."""

    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETE = "complete"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class VersionInfo:
    """Information about a software version."""

    version: str
    release_date: str
    changelog: str
    download_url: Optional[str] = None
    checksum: Optional[str] = None  # SHA256
    size_bytes: int = 0
    is_prerelease: bool = False
    min_python_version: str = "3.9"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "release_date": self.release_date,
            "changelog": self.changelog,
            "download_url": self.download_url,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "is_prerelease": self.is_prerelease,
            "min_python_version": self.min_python_version,
        }


@dataclass
class UpdateResult:
    """Result of an update operation."""

    success: bool
    message: str
    old_version: str
    new_version: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "timestamp": self.timestamp.isoformat(),
        }


def parse_version(version: str) -> tuple:
    """Parse version string into comparable tuple.

    Args:
        version: Version string (e.g., "1.2.3" or "1.2.3rc1")

    Returns:
        Tuple for comparison
    """
    # Remove 'v' prefix if present
    version = version.lstrip("v")

    # Handle pre-release versions
    base_version = version
    prerelease = None

    for marker in ["rc", "alpha", "beta", "dev"]:
        if marker in version:
            parts = version.split(marker)
            base_version = parts[0].rstrip(".")
            prerelease = (marker, int(parts[1]) if parts[1] else 0)
            break

    # Parse base version
    version_parts = []
    for part in base_version.split("."):
        try:
            version_parts.append(int(part))
        except ValueError:
            version_parts.append(0)

    # Pad to 3 parts
    while len(version_parts) < 3:
        version_parts.append(0)

    # Pre-release versions sort before release versions
    if prerelease:
        # Use negative number for pre-release ordering
        order = {"dev": -4, "alpha": -3, "beta": -2, "rc": -1}
        version_parts.append(order.get(prerelease[0], 0))
        version_parts.append(prerelease[1])
    else:
        version_parts.extend([0, 0])

    return tuple(version_parts)


def is_newer_version(current: str, candidate: str) -> bool:
    """Check if candidate version is newer than current.

    Args:
        current: Current version string
        candidate: Candidate version string

    Returns:
        True if candidate is newer
    """
    return parse_version(candidate) > parse_version(current)


def verify_checksum(file_path: str, expected_checksum: str) -> bool:
    """Verify file checksum.

    Args:
        file_path: Path to file
        expected_checksum: Expected SHA256 hex digest

    Returns:
        True if checksum matches
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    actual = sha256.hexdigest()
    return actual.lower() == expected_checksum.lower()


class UpdateManager:
    """Manages software updates."""

    def __init__(
        self,
        update_url: str = "https://updates.spaxiom.ai/api/v1",
        check_interval: int = 86400,  # 24 hours
        auto_install: bool = False,
        backup_dir: Optional[str] = None,
    ):
        """Initialize update manager.

        Args:
            update_url: Base URL for update server
            check_interval: Seconds between automatic checks
            auto_install: Whether to auto-install updates
            backup_dir: Directory for rollback backups
        """
        self.update_url = update_url
        self.check_interval = check_interval
        self.auto_install = auto_install
        self.backup_dir = (
            Path(backup_dir) if backup_dir else Path.home() / ".spaxiom" / "backups"
        )

        self._status = UpdateStatus.IDLE
        self._available_update: Optional[VersionInfo] = None
        self._last_check: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._update_history: List[UpdateResult] = []

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    @property
    def status(self) -> UpdateStatus:
        """Get current update status."""
        return self._status

    @property
    def available_update(self) -> Optional[VersionInfo]:
        """Get available update info."""
        return self._available_update

    def add_callback(self, callback: Callable) -> None:
        """Add callback for update events.

        Args:
            callback: Function called with (event_type, data)
        """
        self._callbacks.append(callback)

    def _notify(self, event: str, data: dict) -> None:
        """Notify callbacks of an event."""
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Update callback error: {e}")

    async def check_for_updates(self) -> Optional[VersionInfo]:
        """Check for available updates.

        Returns:
            VersionInfo if update is available, None otherwise
        """
        self._status = UpdateStatus.CHECKING
        self._last_check = datetime.now(timezone.utc)

        current = get_current_version()
        logger.info(f"Checking for updates (current: {current})")

        try:
            # In production, this would make an HTTP request
            # For now, we just return None (no updates)
            # This can be extended to check PyPI or a custom update server

            latest = await self._fetch_latest_version()

            if latest and is_newer_version(current, latest.version):
                self._available_update = latest
                self._status = UpdateStatus.AVAILABLE
                self._notify("update_available", latest.to_dict())
                logger.info(f"Update available: {latest.version}")
                return latest
            else:
                self._status = UpdateStatus.IDLE
                logger.info("No updates available")
                return None

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self._status = UpdateStatus.FAILED
            return None

    async def _fetch_latest_version(self) -> Optional[VersionInfo]:
        """Fetch latest version info from update server.

        Returns:
            VersionInfo or None if not available
        """
        # This is a placeholder - in production, fetch from update server
        # For now, check PyPI

        try:
            import subprocess

            result = subprocess.run(
                [sys.executable, "-m", "pip", "index", "versions", "spaxiom"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse pip output to find latest version
                # Output format: "spaxiom (X.Y.Z)"
                output = result.stdout
                if "(" in output and ")" in output:
                    version = output.split("(")[1].split(")")[0].strip()
                    return VersionInfo(
                        version=version,
                        release_date=datetime.now(timezone.utc).isoformat(),
                        changelog="See https://github.com/joescanlin/spaxiom-dsl/releases",
                        download_url=f"https://pypi.org/project/spaxiom/{version}/",
                    )
        except Exception as e:
            logger.debug(f"PyPI check failed: {e}")

        return None

    async def download_update(self) -> bool:
        """Download available update.

        Returns:
            True if download successful
        """
        if not self._available_update:
            logger.warning("No update available to download")
            return False

        self._status = UpdateStatus.DOWNLOADING
        logger.info(f"Downloading update: {self._available_update.version}")

        try:
            # For pip-based updates, we don't need to download separately
            self._status = UpdateStatus.AVAILABLE
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self._status = UpdateStatus.FAILED
            return False

    async def install_update(self) -> UpdateResult:
        """Install available update.

        Returns:
            UpdateResult with installation outcome
        """
        if not self._available_update:
            return UpdateResult(
                success=False,
                message="No update available",
                old_version=get_current_version(),
            )

        self._status = UpdateStatus.INSTALLING
        old_version = get_current_version()
        new_version = self._available_update.version

        logger.info(f"Installing update: {old_version} -> {new_version}")

        try:
            # Create backup before updating
            await self._create_backup(old_version)

            # Install via pip
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    f"spaxiom=={new_version}",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self._status = UpdateStatus.COMPLETE
                update_result = UpdateResult(
                    success=True,
                    message="Update installed successfully",
                    old_version=old_version,
                    new_version=new_version,
                )
                self._update_history.append(update_result)
                self._available_update = None
                self._notify("update_installed", update_result.to_dict())
                logger.info(f"Update installed: {new_version}")
                return update_result

            else:
                raise RuntimeError(f"pip install failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            self._status = UpdateStatus.FAILED
            return UpdateResult(
                success=False,
                message=str(e),
                old_version=old_version,
            )

    async def rollback(self, to_version: Optional[str] = None) -> UpdateResult:
        """Rollback to previous version.

        Args:
            to_version: Specific version to rollback to (default: previous)

        Returns:
            UpdateResult with rollback outcome
        """
        current = get_current_version()

        # Find version to rollback to
        if not to_version:
            # Get from history
            for result in reversed(self._update_history):
                if result.success and result.old_version:
                    to_version = result.old_version
                    break

        if not to_version:
            return UpdateResult(
                success=False,
                message="No previous version to rollback to",
                old_version=current,
            )

        logger.info(f"Rolling back: {current} -> {to_version}")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    f"spaxiom=={to_version}",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self._status = UpdateStatus.ROLLED_BACK
                rollback_result = UpdateResult(
                    success=True,
                    message="Rollback successful",
                    old_version=current,
                    new_version=to_version,
                )
                self._notify("rollback_complete", rollback_result.to_dict())
                logger.info(f"Rolled back to {to_version}")
                return rollback_result

            else:
                raise RuntimeError(f"pip install failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return UpdateResult(
                success=False,
                message=str(e),
                old_version=current,
            )

    async def _create_backup(self, version: str) -> None:
        """Create backup before update.

        Args:
            version: Version being backed up
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"spaxiom_{version}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        logger.debug(f"Creating pre-update backup: {backup_path}")

        # In a real implementation, this would backup configuration files
        # For now, we just note the version
        backup_info = {
            "version": version,
            "timestamp": timestamp,
            "python_version": sys.version,
        }

        backup_path.mkdir(parents=True, exist_ok=True)
        with open(backup_path / "info.json", "w") as f:
            json.dump(backup_info, f, indent=2)

    async def start(self) -> None:
        """Start automatic update checking."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"Update manager started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop automatic update checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Update manager stopped")

    async def _check_loop(self) -> None:
        """Background update check loop."""
        while self._running:
            try:
                update = await self.check_for_updates()

                if update and self.auto_install:
                    await self.install_update()

            except Exception as e:
                logger.error(f"Update check error: {e}")

            await asyncio.sleep(self.check_interval)

    def get_status(self) -> dict:
        """Get update manager status.

        Returns:
            Status dictionary
        """
        return {
            "status": self._status.value,
            "current_version": get_current_version(),
            "available_update": (
                self._available_update.to_dict() if self._available_update else None
            ),
            "last_check": (self._last_check.isoformat() if self._last_check else None),
            "auto_install": self.auto_install,
            "check_interval": self.check_interval,
            "update_history": [r.to_dict() for r in self._update_history[-10:]],
        }

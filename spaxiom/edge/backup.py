"""
Backup and restore functionality for Spaxiom Edge.

Provides:
- Database backup
- Configuration backup
- Backup scheduling
- Restore from backup
"""

import asyncio
import json
import logging
import os
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default backup directory
DEFAULT_BACKUP_DIR = "/var/lib/spaxiom/backups"


def get_backup_dir() -> Path:
    """Get the backup directory, creating if needed."""
    backup_dir = Path(os.environ.get("SPAXIOM_BACKUP_DIR", DEFAULT_BACKUP_DIR))
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def generate_backup_name(prefix: str = "backup") -> str:
    """Generate a backup filename with timestamp.

    Args:
        prefix: Filename prefix

    Returns:
        Backup filename (without path)
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{timestamp}.tar.gz"


def create_backup(
    db_path: str,
    config_dir: Optional[str] = None,
    backup_dir: Optional[str] = None,
    include_logs: bool = False,
    log_path: Optional[str] = None,
) -> Tuple[str, dict]:
    """Create a backup of the database and configuration.

    Args:
        db_path: Path to SQLite database file
        config_dir: Path to configuration directory (optional)
        backup_dir: Directory to store backup (optional)
        include_logs: Whether to include log files
        log_path: Path to log file (if include_logs is True)

    Returns:
        Tuple of (backup_path, backup_info)

    Raises:
        FileNotFoundError: If database doesn't exist
        IOError: If backup creation fails
    """
    if backup_dir:
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
    else:
        backup_path = get_backup_dir()

    # Check database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    backup_name = generate_backup_name()
    full_backup_path = backup_path / backup_name

    backup_info = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "contents": [],
    }

    logger.info(f"Creating backup: {full_backup_path}")

    try:
        with tarfile.open(full_backup_path, "w:gz") as tar:
            # Add database
            logger.info(f"Adding database: {db_path}")
            tar.add(db_path, arcname="spaxiom.db")
            backup_info["contents"].append(
                {
                    "type": "database",
                    "name": "spaxiom.db",
                    "original_path": db_path,
                    "size": os.path.getsize(db_path),
                }
            )

            # Add configuration directory
            if config_dir and os.path.exists(config_dir):
                logger.info(f"Adding config directory: {config_dir}")
                tar.add(config_dir, arcname="config")
                backup_info["contents"].append(
                    {
                        "type": "config",
                        "name": "config",
                        "original_path": config_dir,
                    }
                )

            # Add logs if requested
            if include_logs and log_path and os.path.exists(log_path):
                logger.info(f"Adding log file: {log_path}")
                tar.add(log_path, arcname="logs/spaxiom.log")
                backup_info["contents"].append(
                    {
                        "type": "log",
                        "name": "logs/spaxiom.log",
                        "original_path": log_path,
                    }
                )

            # Add backup manifest
            manifest_content = json.dumps(backup_info, indent=2).encode()
            import io

            manifest_file = io.BytesIO(manifest_content)
            manifest_info = tarfile.TarInfo(name="manifest.json")
            manifest_info.size = len(manifest_content)
            tar.addfile(manifest_info, manifest_file)

        backup_info["path"] = str(full_backup_path)
        backup_info["size"] = os.path.getsize(full_backup_path)

        logger.info(
            f"Backup created successfully: {full_backup_path} "
            f"({backup_info['size']} bytes)"
        )

        return str(full_backup_path), backup_info

    except Exception as e:
        # Clean up partial backup
        if full_backup_path.exists():
            full_backup_path.unlink()
        raise IOError(f"Backup creation failed: {e}") from e


def list_backups(backup_dir: Optional[str] = None) -> List[dict]:
    """List available backups.

    Args:
        backup_dir: Directory containing backups

    Returns:
        List of backup info dictionaries
    """
    if backup_dir:
        backup_path = Path(backup_dir)
    else:
        backup_path = get_backup_dir()

    backups = []

    if not backup_path.exists():
        return backups

    for file in sorted(backup_path.glob("backup_*.tar.gz"), reverse=True):
        try:
            info = get_backup_info(str(file))
            backups.append(info)
        except Exception as e:
            logger.warning(f"Could not read backup {file}: {e}")
            backups.append(
                {
                    "path": str(file),
                    "name": file.name,
                    "size": file.stat().st_size,
                    "error": str(e),
                }
            )

    return backups


def get_backup_info(backup_path: str) -> dict:
    """Get information about a backup.

    Args:
        backup_path: Path to backup file

    Returns:
        Backup info dictionary

    Raises:
        FileNotFoundError: If backup doesn't exist
        ValueError: If backup is invalid
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            # Try to read manifest
            try:
                manifest_file = tar.extractfile("manifest.json")
                if manifest_file:
                    manifest = json.load(manifest_file)
                    manifest["path"] = backup_path
                    manifest["name"] = os.path.basename(backup_path)
                    manifest["size"] = os.path.getsize(backup_path)
                    return manifest
            except KeyError:
                pass

            # No manifest, build info from contents
            contents = []
            for member in tar.getmembers():
                contents.append(
                    {
                        "name": member.name,
                        "size": member.size,
                        "type": "file" if member.isfile() else "directory",
                    }
                )

            return {
                "path": backup_path,
                "name": os.path.basename(backup_path),
                "size": os.path.getsize(backup_path),
                "contents": contents,
            }

    except tarfile.TarError as e:
        raise ValueError(f"Invalid backup file: {e}") from e


def restore_backup(
    backup_path: str,
    db_path: str,
    config_dir: Optional[str] = None,
    restore_logs: bool = False,
    log_path: Optional[str] = None,
) -> dict:
    """Restore from a backup.

    Args:
        backup_path: Path to backup file
        db_path: Path where database should be restored
        config_dir: Path where config should be restored
        restore_logs: Whether to restore log files
        log_path: Path where logs should be restored

    Returns:
        Dictionary with restore results

    Raises:
        FileNotFoundError: If backup doesn't exist
        IOError: If restore fails
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    result = {
        "backup_path": backup_path,
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "items": [],
    }

    logger.info(f"Restoring from backup: {backup_path}")

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            # Create temp extraction directory
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract all files
                tar.extractall(tmpdir)

                # Restore database
                extracted_db = os.path.join(tmpdir, "spaxiom.db")
                if os.path.exists(extracted_db):
                    # Backup existing database
                    if os.path.exists(db_path):
                        backup_existing = db_path + ".pre_restore"
                        shutil.copy2(db_path, backup_existing)
                        logger.info(f"Backed up existing database to {backup_existing}")

                    # Copy restored database
                    shutil.copy2(extracted_db, db_path)
                    result["items"].append(
                        {
                            "type": "database",
                            "source": "spaxiom.db",
                            "destination": db_path,
                            "status": "restored",
                        }
                    )
                    logger.info(f"Restored database to {db_path}")

                # Restore config
                extracted_config = os.path.join(tmpdir, "config")
                if config_dir and os.path.exists(extracted_config):
                    # Backup existing config
                    if os.path.exists(config_dir):
                        backup_existing = config_dir + ".pre_restore"
                        if os.path.exists(backup_existing):
                            shutil.rmtree(backup_existing)
                        shutil.copytree(config_dir, backup_existing)
                        logger.info(f"Backed up existing config to {backup_existing}")

                    # Copy restored config
                    if os.path.exists(config_dir):
                        shutil.rmtree(config_dir)
                    shutil.copytree(extracted_config, config_dir)
                    result["items"].append(
                        {
                            "type": "config",
                            "source": "config",
                            "destination": config_dir,
                            "status": "restored",
                        }
                    )
                    logger.info(f"Restored config to {config_dir}")

                # Restore logs if requested
                extracted_logs = os.path.join(tmpdir, "logs", "spaxiom.log")
                if restore_logs and log_path and os.path.exists(extracted_logs):
                    log_dir = os.path.dirname(log_path)
                    os.makedirs(log_dir, exist_ok=True)
                    shutil.copy2(extracted_logs, log_path)
                    result["items"].append(
                        {
                            "type": "log",
                            "source": "logs/spaxiom.log",
                            "destination": log_path,
                            "status": "restored",
                        }
                    )
                    logger.info(f"Restored logs to {log_path}")

        result["status"] = "success"
        logger.info("Restore completed successfully")

        return result

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        raise IOError(f"Restore failed: {e}") from e


def delete_backup(backup_path: str) -> bool:
    """Delete a backup file.

    Args:
        backup_path: Path to backup file

    Returns:
        True if deleted successfully

    Raises:
        FileNotFoundError: If backup doesn't exist
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    os.remove(backup_path)
    logger.info(f"Deleted backup: {backup_path}")
    return True


def cleanup_old_backups(
    backup_dir: Optional[str] = None,
    max_backups: int = 10,
    max_age_days: int = 30,
) -> List[str]:
    """Clean up old backups.

    Keeps the most recent `max_backups` backups and deletes backups
    older than `max_age_days`.

    Args:
        backup_dir: Directory containing backups
        max_backups: Maximum number of backups to keep
        max_age_days: Maximum age in days

    Returns:
        List of deleted backup paths
    """
    backups = list_backups(backup_dir)
    deleted = []

    # Sort by creation time (newest first)
    backups.sort(
        key=lambda b: b.get("created_at", ""),
        reverse=True,
    )

    now = datetime.now(timezone.utc)
    max_age_seconds = max_age_days * 86400

    for i, backup in enumerate(backups):
        should_delete = False

        # Keep only max_backups
        if i >= max_backups:
            should_delete = True

        # Delete if too old
        if "created_at" in backup:
            try:
                created_at = datetime.fromisoformat(
                    backup["created_at"].replace("Z", "+00:00")
                )
                age = (now - created_at).total_seconds()
                if age > max_age_seconds:
                    should_delete = True
            except (ValueError, TypeError):
                pass

        if should_delete and "path" in backup:
            try:
                delete_backup(backup["path"])
                deleted.append(backup["path"])
            except Exception as e:
                logger.error(f"Failed to delete backup {backup['path']}: {e}")

    return deleted


class BackupScheduler:
    """Schedules automatic backups."""

    def __init__(
        self,
        db_path: str,
        config_dir: Optional[str] = None,
        backup_dir: Optional[str] = None,
        interval_hours: int = 24,
        max_backups: int = 7,
    ):
        """Initialize backup scheduler.

        Args:
            db_path: Path to database
            config_dir: Path to config directory
            backup_dir: Directory for backups
            interval_hours: Hours between backups
            max_backups: Maximum backups to keep
        """
        self.db_path = db_path
        self.config_dir = config_dir
        self.backup_dir = backup_dir
        self.interval_hours = interval_hours
        self.max_backups = max_backups

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_backup: Optional[datetime] = None

    async def start(self) -> None:
        """Start scheduled backups."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._backup_loop())
        logger.info(
            f"Backup scheduler started (interval: {self.interval_hours}h, "
            f"max backups: {self.max_backups})"
        )

    async def stop(self) -> None:
        """Stop scheduled backups."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Backup scheduler stopped")

    async def _backup_loop(self) -> None:
        """Background backup loop."""
        while self._running:
            try:
                # Run backup
                backup_path, backup_info = create_backup(
                    self.db_path,
                    self.config_dir,
                    self.backup_dir,
                )
                self._last_backup = datetime.now(timezone.utc)

                # Cleanup old backups
                cleanup_old_backups(
                    self.backup_dir,
                    max_backups=self.max_backups,
                )

                logger.info(f"Scheduled backup completed: {backup_path}")

            except Exception as e:
                logger.error(f"Scheduled backup failed: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval_hours * 3600)

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._running,
            "interval_hours": self.interval_hours,
            "max_backups": self.max_backups,
            "last_backup": (
                self._last_backup.isoformat() if self._last_backup else None
            ),
            "next_backup_in_hours": (
                self.interval_hours
                - (datetime.now(timezone.utc) - self._last_backup).seconds / 3600
                if self._last_backup
                else self.interval_hours
            ),
        }

    async def run_now(self) -> Tuple[str, dict]:
        """Run a backup immediately.

        Returns:
            Tuple of (backup_path, backup_info)
        """
        backup_path, backup_info = create_backup(
            self.db_path,
            self.config_dir,
            self.backup_dir,
        )
        self._last_backup = datetime.now(timezone.utc)
        return backup_path, backup_info

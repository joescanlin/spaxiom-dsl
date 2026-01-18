"""
Logging configuration for Spaxiom Edge.

Provides structured logging with:
- File rotation (max 10MB, keep 5 files)
- Console output for debugging
- JSON format option for log aggregation
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class EdgeLogger:
    """Centralized logging configuration for edge deployment."""

    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        log_path: Optional[str] = None,
        level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        json_format: bool = False,
        console_output: bool = True,
    ):
        """Initialize logging configuration.

        Args:
            log_path: Path to log file (None for console only)
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            max_bytes: Max size per log file before rotation
            backup_count: Number of backup files to keep
            json_format: Use JSON format for file logs
            console_output: Also output to console
        """
        self.log_path = log_path
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.json_format = json_format
        self.console_output = console_output

        self._handlers: list = []

    def setup(self) -> None:
        """Configure logging with specified settings."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_handler.setFormatter(
                logging.Formatter(self.DEFAULT_FORMAT, self.DEFAULT_DATE_FORMAT)
            )
            root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)

        # File handler with rotation
        if self.log_path:
            log_dir = Path(self.log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                self.log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
            )
            file_handler.setLevel(self.level)

            if self.json_format:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(self.DEFAULT_FORMAT, self.DEFAULT_DATE_FORMAT)
                )

            root_logger.addHandler(file_handler)
            self._handlers.append(file_handler)

        # Set specific loggers to appropriate levels
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        logging.info(
            f"Logging initialized: level={logging.getLevelName(self.level)}, "
            f"file={self.log_path or 'None'}"
        )

    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)

    def set_level(self, level: str) -> None:
        """Change log level at runtime.

        Args:
            level: New log level
        """
        new_level = getattr(logging, level.upper(), logging.INFO)
        self.level = new_level

        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)

        for handler in self._handlers:
            handler.setLevel(new_level)

        logging.info(f"Log level changed to {level}")


def setup_logging(
    log_path: Optional[str] = None,
    level: str = "INFO",
    json_format: bool = False,
) -> EdgeLogger:
    """Convenience function to setup logging.

    Args:
        log_path: Path to log file
        level: Log level
        json_format: Use JSON format

    Returns:
        Configured EdgeLogger instance
    """
    logger = EdgeLogger(
        log_path=log_path,
        level=level,
        json_format=json_format,
    )
    logger.setup()
    return logger


def get_default_log_path() -> str:
    """Get default log path based on environment.

    Returns:
        Default log file path
    """
    # Check environment variable first
    env_path = os.environ.get("SPAXIOM_LOG_PATH")
    if env_path:
        return env_path

    # Use /var/log on Linux, user directory elsewhere
    if sys.platform.startswith("linux"):
        log_dir = Path("/var/log/spaxiom")
        if log_dir.exists() or os.access(log_dir.parent, os.W_OK):
            return str(log_dir / "spaxiom.log")

    # Fallback to user directory
    home = Path.home()
    log_dir = home / ".spaxiom" / "logs"
    return str(log_dir / "spaxiom.log")

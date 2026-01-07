"""Logging configuration for powermonitor using loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO", log_to_file: bool = True, enqueue: bool = True) -> None:
    """Configure loguru logger for powermonitor.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file in ~/.powermonitor/
        enqueue: Whether to enqueue log messages (async, thread-safe). Set to False for synchronous logging in tests.

    Features:
        - Console output for WARNING and above
        - File logging with rotation (10 MB max, 7 days retention)
        - Automatic log directory creation
    """
    # Remove default handler
    logger.remove()

    # Console handler (only warnings and errors)
    logger.add(
        sys.stderr,
        level="WARNING",
        format="<level>{level}</level>: {message}",
        colorize=True,
    )

    # File handler (all levels)
    if log_to_file:
        log_dir = Path.home() / ".powermonitor"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "powermonitor.log"

        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # Rotate when file reaches 10 MB
            retention="7 days",  # Keep logs for 7 days
            compression="zip",  # Compress rotated logs
            enqueue=enqueue,  # Thread-safe async logging (disable in tests for synchronous writes)
        )

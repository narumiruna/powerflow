"""Logging configuration for PowerFlow using loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO", log_to_file: bool = True) -> None:
    """Configure loguru logger for PowerFlow.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file in ~/.powerflow/

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
        log_dir = Path.home() / ".powerflow"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "powerflow.log"

        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # Rotate when file reaches 10 MB
            retention="7 days",  # Keep logs for 7 days
            compression="zip",  # Compress rotated logs
            enqueue=True,  # Thread-safe
        )


# Initialize logger on import
setup_logger()

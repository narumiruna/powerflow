"""Tests for logger configuration."""

from pathlib import Path

from loguru import logger

from powermonitor.logger import setup_logger


def test_setup_logger_with_defaults(tmp_path, monkeypatch):
    """Test logger setup with default settings."""
    # Use temp directory for logs
    log_dir = tmp_path / ".powermonitor"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Remove existing handlers
    logger.remove()

    # Setup logger with defaults
    setup_logger(level="INFO", log_to_file=True)

    # Verify log directory created
    assert log_dir.exists()
    assert (log_dir / "powermonitor.log").exists()


def test_setup_logger_debug_level(tmp_path, monkeypatch):
    """Test logger setup with DEBUG level."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    logger.remove()

    setup_logger(level="DEBUG", log_to_file=True)

    # Log debug message
    logger.debug("Test debug message")

    # Verify log file contains debug message
    log_file = tmp_path / ".powermonitor" / "powermonitor.log"
    assert log_file.exists()
    content = log_file.read_text()
    assert "DEBUG" in content
    assert "Test debug message" in content


def test_setup_logger_without_file(tmp_path, monkeypatch):
    """Test logger setup without file logging."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    logger.remove()

    setup_logger(level="INFO", log_to_file=False)

    # Log directory should not be created
    log_dir = tmp_path / ".powermonitor"
    assert not log_dir.exists()


def test_setup_logger_different_levels(tmp_path, monkeypatch):
    """Test logger with different log levels."""
    import time

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    log_file = tmp_path / ".powermonitor" / "powermonitor.log"

    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        logger.remove()

        # Clear log file for each level
        if log_file.exists():
            log_file.unlink()

        setup_logger(level=level, log_to_file=True)

        # Log at that level
        getattr(logger, level.lower())(f"Test {level} message")

        # Flush logger to ensure write completes (enqueue=True makes it async)
        logger.complete()
        time.sleep(0.1)  # Small delay to ensure file is written

        # Verify log file
        assert log_file.exists()
        content = log_file.read_text()
        assert level in content
        assert f"Test {level} message" in content


def test_setup_logger_creates_directory(tmp_path, monkeypatch):
    """Test that logger creates log directory if it doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    logger.remove()

    log_dir = tmp_path / ".powermonitor"
    assert not log_dir.exists()

    setup_logger(level="INFO", log_to_file=True)

    # Directory should be created
    assert log_dir.exists()
    assert log_dir.is_dir()

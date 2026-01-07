"""Pytest configuration and fixtures for powermonitor tests."""

import tempfile
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from powermonitor import config_loader
from powermonitor.database import Database
from powermonitor.models import PowerReading


@pytest.fixture
def temp_db():
    """Create a temporary database for testing.

    Yields:
        Path to temporary database file

    Cleanup:
        Removes database file after test
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def database(temp_db):
    """Create a Database instance with temporary database.

    Args:
        temp_db: Temporary database path fixture

    Yields:
        Database instance

    Cleanup:
        Closes database connections after test
    """
    db = Database(temp_db)
    yield db
    # Ensure all connections are closed
    db.close()


@pytest.fixture
def sample_reading():
    """Create a sample PowerReading for testing.

    Returns:
        PowerReading instance with test data
    """
    return PowerReading(
        timestamp=datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC),
        watts_actual=45.5,
        watts_negotiated=67,
        voltage=20.0,
        amperage=2.275,
        current_capacity=3500,
        max_capacity=4709,
        battery_percent=74,
        is_charging=True,
        external_connected=True,
        charger_name="USB-C Power Adapter",
        charger_manufacturer="Apple Inc.",
    )


@pytest.fixture
def ioreg_fixture_path():
    """Get path to real_mac.txt fixture.

    Returns:
        Path to ioreg output fixture
    """
    return Path(__file__).parent / "fixtures" / "real_mac.txt"


@pytest.fixture
def temp_config(temp_db, monkeypatch):
    """Create a temporary config file for testing.

    Args:
        temp_db: Temporary database path fixture
        monkeypatch: Pytest monkeypatch fixture

    Yields:
        Path to temporary config file

    Cleanup:
        Removes config file after test
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        config_content = f"""
[tui]
interval = 1.0
stats_limit = 100
chart_limit = 60

[database]
path = "{temp_db}"

[cli]
default_history_limit = 20
default_export_limit = 1000

[logging]
level = "INFO"
"""
        f.write(config_content)
        config_path = f.name

    # Monkeypatch get_config_path to return temp config
    # Note: config_loader is imported at module level to make dependency explicit
    monkeypatch.setattr(config_loader, "get_config_path", lambda: Path(config_path))

    yield config_path

    # Cleanup
    Path(config_path).unlink(missing_ok=True)

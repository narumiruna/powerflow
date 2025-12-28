"""Pytest configuration and fixtures for powermonitor tests."""

import tempfile
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest

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

    Returns:
        Database instance
    """
    return Database(temp_db)


@pytest.fixture
def sample_reading():
    """Create a sample PowerReading for testing.

    Returns:
        PowerReading instance with test data
    """
    return PowerReading(
        timestamp=datetime(2025, 12, 28, 12, 0, 0, tzinfo=timezone.utc),
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

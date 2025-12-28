"""Tests for database operations."""

import sqlite3
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from powermonitor.database import Database
from powermonitor.models import PowerReading


def test_database_initialization(database, temp_db):
    """Test database initializes with correct schema."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Check table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='power_readings'")
    assert cursor.fetchone() is not None

    # Check schema has all columns
    cursor.execute("PRAGMA table_info(power_readings)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        "id",
        "timestamp",
        "watts_actual",
        "watts_negotiated",
        "voltage",
        "amperage",
        "current_capacity",
        "max_capacity",
        "battery_percent",
        "is_charging",
        "external_connected",
        "charger_name",
        "charger_manufacturer",
    }

    assert columns == expected_columns
    conn.close()


def test_insert_reading(database, sample_reading):
    """Test inserting a power reading."""
    row_id = database.insert_reading(sample_reading)

    assert isinstance(row_id, int)
    assert row_id > 0


def test_insert_multiple_readings(database):
    """Test inserting multiple readings."""
    readings = []
    base_time = datetime.now(UTC)

    for i in range(5):
        reading = PowerReading(
            timestamp=base_time + timedelta(seconds=i * 2),
            watts_actual=40.0 + i,
            watts_negotiated=67,
            voltage=20.0,
            amperage=2.0 + (i * 0.1),
            current_capacity=3500,
            max_capacity=4709,
            battery_percent=74,
            is_charging=True,
            external_connected=True,
            charger_name=None,
            charger_manufacturer=None,
        )
        row_id = database.insert_reading(reading)
        readings.append((row_id, reading))

    # All insertions should succeed with unique IDs
    assert len(readings) == 5
    assert len(set(r[0] for r in readings)) == 5  # All unique IDs


def test_query_history(database, sample_reading):
    """Test querying reading history."""
    # Insert some readings
    for i in range(10):
        reading = PowerReading(
            timestamp=sample_reading.timestamp + timedelta(seconds=i),
            watts_actual=40.0 + i,
            watts_negotiated=67,
            voltage=20.0,
            amperage=2.0,
            current_capacity=3500,
            max_capacity=4709,
            battery_percent=74 - i,
            is_charging=True,
            external_connected=True,
            charger_name=None,
            charger_manufacturer=None,
        )
        database.insert_reading(reading)

    # Query last 5 readings
    history = database.query_history(limit=5)

    assert len(history) == 5
    # Should be in reverse chronological order (newest first)
    assert history[0].battery_percent == 65  # Last inserted (74 - 9)
    assert history[4].battery_percent == 69  # 5th from last (74 - 5)


def test_query_history_empty(database):
    """Test querying history when database is empty."""
    history = database.query_history()

    assert isinstance(history, list)
    assert len(history) == 0


def test_get_statistics(database):
    """Test calculating statistics from readings."""
    # Insert readings with known values
    base_time = datetime.now(UTC)
    watts_values = [10.0, 20.0, 30.0, 40.0, 50.0]

    for i, watts in enumerate(watts_values):
        reading = PowerReading(
            timestamp=base_time + timedelta(seconds=i),
            watts_actual=watts,
            watts_negotiated=67,
            voltage=20.0,
            amperage=watts / 20.0,
            current_capacity=3000 + (i * 100),
            max_capacity=4709,
            battery_percent=50 + (i * 5),
            is_charging=True,
            external_connected=True,
            charger_name=None,
            charger_manufacturer=None,
        )
        database.insert_reading(reading)

    stats = database.get_statistics()

    assert stats["count"] == 5
    assert stats["avg_watts"] == 30.0  # (10+20+30+40+50)/5
    assert stats["min_watts"] == 10.0
    assert stats["max_watts"] == 50.0
    assert stats["avg_battery"] == 60.0  # (50+55+60+65+70)/5
    assert stats["earliest"] is not None
    assert stats["latest"] is not None


def test_get_statistics_empty(database):
    """Test statistics when database is empty."""
    stats = database.get_statistics()

    assert stats["count"] == 0
    assert stats["avg_watts"] == 0.0
    assert stats["min_watts"] == 0.0
    assert stats["max_watts"] == 0.0
    assert stats["avg_battery"] == 0.0
    assert stats["earliest"] is None
    assert stats["latest"] is None


def test_clear_history(database, sample_reading):
    """Test clearing all historical readings."""
    # Insert some readings
    for _ in range(5):
        database.insert_reading(sample_reading)

    # Verify data exists
    history = database.query_history()
    assert len(history) == 5

    # Clear history
    rows_deleted = database.clear_history()
    assert rows_deleted == 5

    # Verify data is gone
    history = database.query_history()
    assert len(history) == 0


def test_clear_history_empty(database):
    """Test clearing history when database is already empty."""
    rows_deleted = database.clear_history()
    assert rows_deleted == 0


def test_reading_with_null_charger(database):
    """Test storing and retrieving reading with NULL charger fields."""
    reading = PowerReading(
        timestamp=datetime.now(UTC),
        watts_actual=-5.0,
        watts_negotiated=0,
        voltage=12.0,
        amperage=-0.417,
        current_capacity=3000,
        max_capacity=4709,
        battery_percent=64,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    row_id = database.insert_reading(reading)
    assert row_id > 0

    # Retrieve and verify
    history = database.query_history(limit=1)
    assert len(history) == 1
    assert history[0].charger_name is None
    assert history[0].charger_manufacturer is None


def test_database_index_exists(temp_db):
    """Test that timestamp index exists for performance."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Initialize database
    Database(temp_db)

    # Check index exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'")
    assert cursor.fetchone() is not None

    conn.close()

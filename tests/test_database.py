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
    assert len({r[0] for r in readings}) == 5  # All unique IDs


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


def test_database_timestamp_is_indexed(temp_db: str) -> None:
    """Test that timestamp column is indexed (name may vary)."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Initialize database
    db = Database(temp_db)
    db.close()

    # Find all indexes on power_readings
    cursor.execute("PRAGMA index_list('power_readings')")
    indexes = cursor.fetchall()

    # Ensure at least one index exists on timestamp column
    timestamp_index_found = False

    for _, index_name, *_ in indexes:
        # Validate index_name to prevent SQL injection
        # Index names should only contain alphanumeric characters and underscores
        if not index_name.replace("_", "").isalnum():
            continue
        cursor.execute(f"PRAGMA index_info('{index_name}')")
        indexed_columns = [row[2] for row in cursor.fetchall()]
        if "timestamp" in indexed_columns:
            timestamp_index_found = True
            break

    assert timestamp_index_found, "timestamp column should be indexed"

    conn.close()


def test_cleanup_old_data(database):
    """Test cleanup_old_data method."""
    base_time = datetime.now(UTC)

    # Create readings with different ages
    for i in range(5):
        reading = PowerReading(
            timestamp=base_time - timedelta(days=i * 10),  # 0, 10, 20, 30, 40 days old
            watts_actual=40.0,
            watts_negotiated=67,
            voltage=20.0,
            amperage=2.0,
            current_capacity=3500,
            max_capacity=4709,
            battery_percent=74,
            is_charging=True,
            external_connected=True,
            charger_name=None,
            charger_manufacturer=None,
        )
        database.insert_reading(reading)

    # Delete readings older than 25 days (should delete 2: 30 and 40 days old)
    deleted = database.cleanup_old_data(days=25)
    assert deleted == 2

    # Verify remaining readings
    remaining = database.query_history(limit=None)
    assert len(remaining) == 3


def test_cleanup_old_data_none_old(database):
    """Test cleanup_old_data when no readings are old enough."""
    # Create recent readings (all within last day)
    base_time = datetime.now(UTC)
    for i in range(3):
        reading = PowerReading(
            timestamp=base_time - timedelta(hours=i),
            watts_actual=40.0,
            watts_negotiated=67,
            voltage=20.0,
            amperage=2.0,
            current_capacity=3500,
            max_capacity=4709,
            battery_percent=74,
            is_charging=True,
            external_connected=True,
            charger_name=None,
            charger_manufacturer=None,
        )
        database.insert_reading(reading)

    # Try to delete readings older than 7 days (should delete 0)
    deleted = database.cleanup_old_data(days=7)
    assert deleted == 0

    # Verify all readings still exist
    remaining = database.query_history(limit=None)
    assert len(remaining) == 3


def test_cleanup_old_data_empty(database):
    """Test cleanup_old_data on empty database."""
    deleted = database.cleanup_old_data(days=30)
    assert deleted == 0


def test_get_battery_health_trend(database):
    """Test get_battery_health_trend method."""
    base_time = datetime.now(UTC)

    # Create readings over 7 days with slight capacity degradation
    for day in range(7):
        for i in range(5):  # 5 readings per day
            reading = PowerReading(
                timestamp=base_time - timedelta(days=day, hours=i),
                watts_actual=40.0,
                watts_negotiated=67,
                voltage=20.0,
                amperage=2.0,
                current_capacity=3500,
                max_capacity=4700 - day,  # Simulate degradation: 4700, 4699, 4698...
                battery_percent=74,
                is_charging=True,
                external_connected=True,
                charger_name=None,
                charger_manufacturer=None,
            )
            database.insert_reading(reading)

    # Get health trend
    results = database.get_battery_health_trend(days=7)

    # Should have 7 days of data
    assert len(results) == 7

    # Each result is (date, avg_max_capacity, reading_count)
    for result in results:
        assert len(result) == 3
        assert isinstance(result[0], str)  # date
        assert isinstance(result[1], float)  # avg_max_capacity
        assert isinstance(result[2], int)  # reading_count
        assert result[2] == 5  # 5 readings per day

    # Check that capacity values are in expected range
    capacities = [r[1] for r in results]
    assert all(4694 <= c <= 4700 for c in capacities)


def test_get_battery_health_trend_no_data(database):
    """Test get_battery_health_trend with no data."""
    results = database.get_battery_health_trend(days=7)
    assert len(results) == 0


def test_get_battery_health_trend_partial_days(database):
    """Test get_battery_health_trend with only some days having data."""
    base_time = datetime.now(UTC)

    # Create readings only for 3 specific days
    for day in [0, 2, 5]:
        for i in range(3):
            reading = PowerReading(
                timestamp=base_time - timedelta(days=day, hours=i),
                watts_actual=40.0,
                watts_negotiated=67,
                voltage=20.0,
                amperage=2.0,
                current_capacity=3500,
                max_capacity=4700,
                battery_percent=74,
                is_charging=True,
                external_connected=True,
                charger_name=None,
                charger_manufacturer=None,
            )
            database.insert_reading(reading)

    # Get health trend for 7 days
    results = database.get_battery_health_trend(days=7)

    # Should only have 3 days with data
    assert len(results) == 3
    for result in results:
        assert result[2] == 3  # 3 readings per day

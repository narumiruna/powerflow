"""SQLite database operations for powermonitor."""

import sqlite3
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from .models import PowerReading


def get_default_db_path() -> Path:
    """Get default database path.

    Returns:
        Path to ~/.powermonitor/powermonitor.db

    Note:
        This function is kept for backward compatibility.
        Prefer using PowerMonitorConfig.database_path in CLI/TUI code.
    """
    db_dir = Path.home() / ".powermonitor"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "powermonitor.db"


# Default database path (for backward compatibility)
# CLI and TUI should use config.database_path instead
DB_PATH = get_default_db_path()


class Database:
    """SQLite database manager for power readings.

    The Database class manages schema initialization and provides methods for
    reading/writing power data. Each database operation uses its own connection
    context manager, so there are no persistent connections to clean up.

    The context manager protocol (__enter__/__exit__) is provided for API
    consistency with common database patterns, but does not manage resources.
    You can use it with or without the 'with' statement:

        # With context manager (idiomatic, but functionally identical to without)
        with Database(path) as db:
            db.insert_reading(reading)

        # Without context manager (also valid)
        db = Database(path)
        db.insert_reading(reading)
    """

    def __init__(self, db_path: Path | str = DB_PATH):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        # Ensure parent directory exists for custom database paths
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def __enter__(self):
        """Enter context manager (no-op, provided for API consistency)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager (no-op, as each operation manages its own connection)."""
        # Nothing to clean up as we use context managers for each connection
        return False

    def _init_schema(self) -> None:
        """Create database schema if it doesn't exist.

        Complete schema with all 12 PowerReading fields.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create table with all 12 fields (was missing 4 fields in old version)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS power_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    watts_actual REAL NOT NULL,
                    watts_negotiated INTEGER NOT NULL,
                    voltage REAL NOT NULL,
                    amperage REAL NOT NULL,
                    current_capacity INTEGER NOT NULL,
                    max_capacity INTEGER NOT NULL,
                    battery_percent INTEGER NOT NULL,
                    is_charging INTEGER NOT NULL,
                    external_connected INTEGER NOT NULL,
                    charger_name TEXT,
                    charger_manufacturer TEXT
                )
            """)

            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON power_readings(timestamp DESC)
            """)
            # Commit is automatic with context manager

    def insert_reading(self, reading: PowerReading) -> int:
        """Insert power reading into database.

        Args:
            reading: PowerReading to insert

        Returns:
            Row ID of inserted reading
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO power_readings (
                    timestamp,
                    watts_actual,
                    watts_negotiated,
                    voltage,
                    amperage,
                    current_capacity,
                    max_capacity,
                    battery_percent,
                    is_charging,
                    external_connected,
                    charger_name,
                    charger_manufacturer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reading.timestamp.isoformat(),  # RFC3339 format
                    reading.watts_actual,
                    reading.watts_negotiated,
                    reading.voltage,
                    reading.amperage,
                    reading.current_capacity,
                    reading.max_capacity,
                    reading.battery_percent,
                    1 if reading.is_charging else 0,
                    1 if reading.external_connected else 0,
                    reading.charger_name,
                    reading.charger_manufacturer,
                ),
            )

            row_id = cursor.lastrowid
            # Commit is automatic with context manager

            assert row_id is not None, "Failed to insert reading"
            return row_id

    def query_history(self, limit: int | None = 20) -> list[PowerReading]:
        """Query most recent power readings.

        Args:
            limit: Maximum number of readings to return. None = all readings.

        Returns:
            List of PowerReading objects, ordered by timestamp DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Build query dynamically based on whether limit is specified
            query = """
                SELECT
                    timestamp,
                    watts_actual,
                    watts_negotiated,
                    voltage,
                    amperage,
                    current_capacity,
                    max_capacity,
                    battery_percent,
                    is_charging,
                    external_connected,
                    charger_name,
                    charger_manufacturer
                FROM power_readings
                ORDER BY timestamp DESC
            """

            if limit is None:
                cursor.execute(query)
            else:
                cursor.execute(query + " LIMIT ?", (limit,))

            rows = cursor.fetchall()

        # Convert rows to PowerReading objects
        readings = []
        for row in rows:
            readings.append(
                PowerReading(
                    timestamp=datetime.fromisoformat(row[0]),
                    watts_actual=row[1],
                    watts_negotiated=row[2],
                    voltage=row[3],
                    amperage=row[4],
                    current_capacity=row[5],
                    max_capacity=row[6],
                    battery_percent=row[7],
                    is_charging=bool(row[8]),
                    external_connected=bool(row[9]),
                    charger_name=row[10],
                    charger_manufacturer=row[11],
                )
            )

        return readings

    def get_statistics(self, limit: int | None = 100) -> dict:
        """Calculate statistics from recent readings.

        Args:
            limit: Number of recent readings to include in statistics. None = all readings.

        Returns:
            Dictionary with avg, min, max power and battery stats
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Build query dynamically based on whether limit is specified
            if limit is None:
                # Calculate statistics over all readings
                query = """
                    SELECT
                        AVG(watts_actual) as avg_watts,
                        MIN(watts_actual) as min_watts,
                        MAX(watts_actual) as max_watts,
                        AVG(battery_percent) as avg_battery,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest,
                        COUNT(*) as count
                    FROM power_readings
                """
                cursor.execute(query)
            else:
                # Calculate statistics over the most recent N readings
                query = """
                    SELECT
                        AVG(watts_actual) as avg_watts,
                        MIN(watts_actual) as min_watts,
                        MAX(watts_actual) as max_watts,
                        AVG(battery_percent) as avg_battery,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest,
                        COUNT(*) as count
                    FROM (
                        SELECT watts_actual, battery_percent, timestamp
                        FROM power_readings
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                """
                cursor.execute(query, (limit,))

            row = cursor.fetchone()

        if row and row[6] > 0:  # count > 0
            return {
                "avg_watts": row[0] or 0.0,
                "min_watts": row[1] or 0.0,
                "max_watts": row[2] or 0.0,
                "avg_battery": row[3] or 0.0,
                "earliest": row[4],
                "latest": row[5],
                "count": row[6],
            }

        return {
            "avg_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0,
            "avg_battery": 0.0,
            "earliest": None,
            "latest": None,
            "count": 0,
        }

    def clear_history(self) -> int:
        """Clear all power readings from database.

        Returns:
            Number of rows deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM power_readings")
            rows_deleted = cursor.rowcount
            # Commit is automatic with context manager

            return rows_deleted

    def cleanup_old_data(self, days: int) -> int:
        """Delete power readings older than specified number of days.

        Args:
            days: Number of days - readings older than this will be deleted

        Returns:
            Number of rows deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM power_readings WHERE timestamp < ?", (cutoff.isoformat(),))
            rows_deleted = cursor.rowcount
            # Commit is automatic with context manager

            return rows_deleted

    def get_battery_health_trend(self, days: int = 30) -> list[tuple[str, float, int]]:
        """Get daily average battery health (max_capacity) over specified period.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            List of tuples: (date, avg_max_capacity, reading_count)
            Ordered by date ascending
        """
        if days <= 0:
            raise ValueError("days must be a positive integer")
        cutoff = datetime.now(UTC) - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    AVG(max_capacity) as avg_max_capacity,
                    COUNT(*) as reading_count
                FROM power_readings
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date ASC
                """,
                (cutoff.isoformat(),),
            )

            return cursor.fetchall()


# Module-level convenience functions
_db_instances: dict[Path, Database] = {}


def get_database(db_path: Path | str = DB_PATH) -> Database:
    """Get database instance for the specified path.

    Uses caching to return the same instance for the same path.
    Paths are normalized to absolute paths for consistent caching.

    Args:
        db_path: Path to database file

    Returns:
        Database instance for the specified path
    """
    # Normalize path to absolute path for consistent caching
    path = Path(db_path).resolve()

    if path not in _db_instances:
        _db_instances[path] = Database(path)

    return _db_instances[path]


def insert_reading(reading: PowerReading, db_path: Path | str = DB_PATH) -> int:
    """Convenience function to insert reading using default database.

    Args:
        reading: PowerReading to insert
        db_path: Path to database file

    Returns:
        Row ID of inserted reading
    """
    return get_database(db_path).insert_reading(reading)


def query_history(limit: int | None = 20, db_path: Path | str = DB_PATH) -> list[PowerReading]:
    """Convenience function to query history using default database.

    Args:
        limit: Maximum number of readings. None = all readings.
        db_path: Path to database file

    Returns:
        List of PowerReading objects
    """
    return get_database(db_path).query_history(limit)


def get_statistics(limit: int | None = 100, db_path: Path | str = DB_PATH) -> dict:
    """Convenience function to get statistics using default database.

    Args:
        limit: Number of recent readings to include. None = all readings.
        db_path: Path to database file

    Returns:
        Statistics dictionary
    """
    return get_database(db_path).get_statistics(limit)

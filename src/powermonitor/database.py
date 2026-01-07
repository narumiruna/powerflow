"""SQLite database operations for powermonitor."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from peewee import fn

from .models import PowerReading
from .models import PowerReadingModel
from .models import db


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
    """SQLite database manager for power readings using Peewee ORM.

    The Database class manages schema initialization and provides methods for
    reading/writing power data. Uses Peewee ORM for simplified database operations.

    The context manager protocol (__enter__/__exit__) is provided for API
    consistency with common database patterns.

    Usage:
        # With context manager (idiomatic)
        with Database(path) as db:
            db.insert_reading(reading)

        # Without context manager (also valid)
        db = Database(path)
        db.insert_reading(reading)
        db.close()  # Recommended when not using context manager
    """

    def __init__(self, db_path: Path | str = DB_PATH):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        # Ensure parent directory exists for custom database paths
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Peewee database
        db.init(str(self.db_path))
        db.create_tables([PowerReadingModel])
        
        # Create index with specific name for backward compatibility
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON power_readings(timestamp DESC)"
        )

    def __enter__(self):
        """Enter context manager (no-op, provided for API consistency)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, closing database connection."""
        self.close()
        return False

    def close(self) -> None:
        """Close database connection.

        Closes the Peewee database connection if it's open.
        """
        if not db.is_closed():
            db.close()

    def insert_reading(self, reading: PowerReading) -> int:
        """Insert power reading into database.

        Args:
            reading: PowerReading to insert

        Returns:
            Row ID of inserted reading
        """
        model = PowerReadingModel.create(
            timestamp=reading.timestamp,
            watts_actual=reading.watts_actual,
            watts_negotiated=reading.watts_negotiated,
            voltage=reading.voltage,
            amperage=reading.amperage,
            current_capacity=reading.current_capacity,
            max_capacity=reading.max_capacity,
            battery_percent=reading.battery_percent,
            is_charging=reading.is_charging,
            external_connected=reading.external_connected,
            charger_name=reading.charger_name,
            charger_manufacturer=reading.charger_manufacturer,
        )
        return model.id

    def query_history(self, limit: int | None = 20) -> list[PowerReading]:
        """Query most recent power readings.

        Args:
            limit: Maximum number of readings to return. None = all readings.

        Returns:
            List of PowerReading objects, ordered by timestamp DESC
        """
        query = PowerReadingModel.select().order_by(PowerReadingModel.timestamp.desc())
        if limit is not None:
            query = query.limit(limit)

        return [
            PowerReading(
                timestamp=r.timestamp if isinstance(r.timestamp, datetime) else datetime.fromisoformat(r.timestamp),
                watts_actual=r.watts_actual,
                watts_negotiated=r.watts_negotiated,
                voltage=r.voltage,
                amperage=r.amperage,
                current_capacity=r.current_capacity,
                max_capacity=r.max_capacity,
                battery_percent=r.battery_percent,
                is_charging=r.is_charging,
                external_connected=r.external_connected,
                charger_name=r.charger_name,
                charger_manufacturer=r.charger_manufacturer,
            )
            for r in query
        ]

    def get_statistics(self, limit: int | None = 100) -> dict:
        """Calculate statistics from recent readings.

        Args:
            limit: Number of recent readings to include in statistics. None = all readings.

        Returns:
            Dictionary with avg, min, max power and battery stats
        """
        query = PowerReadingModel.select()
        if limit is not None:
            query = query.order_by(PowerReadingModel.timestamp.desc()).limit(limit)

        if query.count() == 0:
            return {
                "avg_watts": 0.0,
                "min_watts": 0.0,
                "max_watts": 0.0,
                "avg_battery": 0.0,
                "earliest": None,
                "latest": None,
                "count": 0,
            }

        readings = list(query)
        
        # Handle timestamp - could be datetime or string depending on Peewee's behavior
        timestamps = [r.timestamp if isinstance(r.timestamp, datetime) else datetime.fromisoformat(r.timestamp) for r in readings]
        
        return {
            "avg_watts": sum(r.watts_actual for r in readings) / len(readings),
            "min_watts": min(r.watts_actual for r in readings),
            "max_watts": max(r.watts_actual for r in readings),
            "avg_battery": sum(r.battery_percent for r in readings) / len(readings),
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
            "count": len(readings),
        }

    def clear_history(self) -> int:
        """Clear all power readings from database.

        Returns:
            Number of rows deleted
        """
        return PowerReadingModel.delete().execute()

    def cleanup_old_data(self, days: int) -> int:
        """Delete power readings older than specified number of days.

        Args:
            days: Number of days - readings older than this will be deleted

        Returns:
            Number of rows deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        return PowerReadingModel.delete().where(PowerReadingModel.timestamp < cutoff).execute()

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

        # Use Peewee's fn.DATE() and aggregation
        query = (
            PowerReadingModel.select(
                fn.DATE(PowerReadingModel.timestamp).alias("date"),
                fn.AVG(PowerReadingModel.max_capacity).alias("avg_max_capacity"),
                fn.COUNT(PowerReadingModel.id).alias("reading_count"),
            )
            .where(PowerReadingModel.timestamp >= cutoff)
            .group_by(fn.DATE(PowerReadingModel.timestamp))
            .order_by(fn.DATE(PowerReadingModel.timestamp))
        )

        # Convert date to string if it's returned as datetime
        return [
            (row.date if isinstance(row.date, str) else row.date.strftime("%Y-%m-%d"), row.avg_max_capacity, row.reading_count)
            for row in query
        ]


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

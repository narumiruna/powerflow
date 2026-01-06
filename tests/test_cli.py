"""Tests for CLI commands."""

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from typer.testing import CliRunner

from powermonitor.cli import app
from powermonitor.database import Database
from powermonitor.models import PowerReading

runner = CliRunner()


def create_test_readings(database: Database, count: int = 10) -> list[PowerReading]:
    """Create test readings in database.

    Args:
        database: Database instance
        count: Number of readings to create

    Returns:
        List of created PowerReading objects
    """
    readings = []
    base_time = datetime.now(UTC)

    for i in range(count):
        reading = PowerReading(
            timestamp=base_time - timedelta(seconds=i * 60),  # 1 minute apart
            watts_actual=40.0 + i,
            watts_negotiated=67,
            voltage=20.0,
            amperage=2.0 + (i * 0.1),
            current_capacity=3500,
            max_capacity=4709,
            battery_percent=74,
            is_charging=True,
            external_connected=True,
            charger_name="USB-C Power Adapter" if i % 2 == 0 else None,
            charger_manufacturer="Apple Inc." if i % 2 == 0 else None,
        )
        database.insert_reading(reading)
        readings.append(reading)

    return readings


def test_export_csv(database, temp_db, tmp_path):
    """Test exporting readings to CSV format."""
    # Create test data
    create_test_readings(database, count=5)

    # Export to CSV
    output_file = tmp_path / "test_export.csv"
    result = runner.invoke(
        app,
        ["export", str(output_file), "--limit", "5"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )

    assert result.exit_code == 0
    assert "Exported 5 readings" in result.stdout
    assert output_file.exists()

    # Verify CSV content
    content = output_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 6  # Header + 5 data rows
    assert lines[0].startswith("timestamp,watts_actual,watts_negotiated")


def test_export_json(database, temp_db, tmp_path):
    """Test exporting readings to JSON format."""
    # Create test data
    create_test_readings(database, count=3)

    # Export to JSON
    output_file = tmp_path / "test_export.json"
    result = runner.invoke(
        app,
        ["export", str(output_file), "--limit", "3"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )

    assert result.exit_code == 0
    assert "Exported 3 readings" in result.stdout
    assert output_file.exists()

    # Verify JSON content
    with output_file.open() as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 3
    assert "timestamp" in data[0]
    assert "watts_actual" in data[0]


def test_export_auto_detect_format(database, temp_db, tmp_path):
    """Test export format auto-detection from file extension."""
    # Create test data
    create_test_readings(database, count=2)

    # Test CSV detection
    csv_file = tmp_path / "auto.csv"
    result = runner.invoke(
        app,
        ["export", str(csv_file)],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert csv_file.exists()

    # Test JSON detection
    json_file = tmp_path / "auto.json"
    result = runner.invoke(
        app,
        ["export", str(json_file)],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert json_file.exists()


def test_export_invalid_format(temp_db, tmp_path):
    """Test export with invalid format."""
    output_file = tmp_path / "test.txt"
    result = runner.invoke(
        app,
        ["export", str(output_file)],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 1
    assert "Cannot detect format" in result.stdout


def test_export_no_readings(database, temp_db, tmp_path):
    """Test export with empty database."""
    output_file = tmp_path / "empty.csv"
    result = runner.invoke(
        app,
        ["export", str(output_file)],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "No readings found" in result.stdout


def test_export_with_limit(database, temp_db, tmp_path):
    """Test export with limit parameter."""
    # Create 10 readings
    create_test_readings(database, count=10)

    # Export only 3
    output_file = tmp_path / "limited.csv"
    result = runner.invoke(
        app,
        ["export", str(output_file), "--limit", "3"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Exported 3 readings" in result.stdout


def test_stats_command(database, temp_db):
    """Test stats command."""
    # Create test data
    create_test_readings(database, count=5)

    result = runner.invoke(
        app,
        ["stats"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Database Statistics" in result.stdout
    assert "Total readings" in result.stdout
    assert "5" in result.stdout


def test_stats_empty_database(database, temp_db):
    """Test stats command with empty database."""
    result = runner.invoke(
        app,
        ["stats"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "No readings in database" in result.stdout


def test_cleanup_with_days(database, temp_db):
    """Test cleanup command with --days parameter."""
    # Create readings with different timestamps
    base_time = datetime.now(UTC)
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

    # Delete readings older than 25 days (should delete 2)
    result = runner.invoke(
        app,
        ["cleanup", "--days", "25"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Deleted 2 old readings" in result.stdout

    # Verify remaining readings
    remaining = database.query_history(limit=None)
    assert len(remaining) == 3


def test_cleanup_all_with_confirmation(database, temp_db):
    """Test cleanup --all with user confirmation."""
    # Create test data
    create_test_readings(database, count=5)

    # Confirm deletion
    result = runner.invoke(
        app,
        ["cleanup", "--all"],
        input="y\n",
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Deleted all 5 readings" in result.stdout

    # Verify database is empty
    remaining = database.query_history(limit=None)
    assert len(remaining) == 0


def test_cleanup_all_cancelled(database, temp_db):
    """Test cleanup --all when user cancels."""
    # Create test data
    create_test_readings(database, count=3)

    # Cancel deletion
    result = runner.invoke(
        app,
        ["cleanup", "--all"],
        input="n\n",
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Operation cancelled" in result.stdout

    # Verify data still exists
    remaining = database.query_history(limit=None)
    assert len(remaining) == 3


def test_cleanup_missing_parameters(temp_db):
    """Test cleanup command with missing parameters."""
    result = runner.invoke(
        app,
        ["cleanup"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 1
    assert "Must specify either --days N or --all" in result.stdout


def test_history_command(database, temp_db):
    """Test history command."""
    # Create test data
    create_test_readings(database, count=5)

    result = runner.invoke(
        app,
        ["history", "--limit", "5"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Recent Power Readings" in result.stdout
    assert "Time" in result.stdout
    assert "Power" in result.stdout


def test_history_empty_database(database, temp_db):
    """Test history command with empty database."""
    result = runner.invoke(
        app,
        ["history"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "No readings in database" in result.stdout


def test_health_command(database, temp_db):
    """Test health command."""
    # Create readings over multiple days
    base_time = datetime.now(UTC)
    for day in range(7):
        for i in range(5):  # 5 readings per day
            reading = PowerReading(
                timestamp=base_time - timedelta(days=day, hours=i),
                watts_actual=40.0,
                watts_negotiated=67,
                voltage=20.0,
                amperage=2.0,
                current_capacity=3500,
                max_capacity=4700 - day,  # Simulate slight degradation
                battery_percent=74,
                is_charging=True,
                external_connected=True,
                charger_name=None,
                charger_manufacturer=None,
            )
            database.insert_reading(reading)

    result = runner.invoke(
        app,
        ["health", "--days", "7"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "Battery Health Analysis" in result.stdout
    assert "mAh" in result.stdout


def test_health_no_data(database, temp_db):
    """Test health command with no data."""
    result = runner.invoke(
        app,
        ["health", "--days", "7"],
        env={"POWERMONITOR_DB_PATH": str(temp_db)},
    )
    assert result.exit_code == 0
    assert "No readings found" in result.stdout

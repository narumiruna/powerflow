"""Tests for PowerReading model."""

from datetime import datetime
from datetime import timezone

from powermonitor.models import PowerReading


def test_power_reading_creation(sample_reading):
    """Test PowerReading can be created with all fields."""
    assert sample_reading.watts_actual == 45.5
    assert sample_reading.watts_negotiated == 67
    assert sample_reading.voltage == 20.0
    assert sample_reading.amperage == 2.275
    assert sample_reading.current_capacity == 3500
    assert sample_reading.max_capacity == 4709
    assert sample_reading.battery_percent == 74
    assert sample_reading.is_charging is True
    assert sample_reading.external_connected is True
    assert sample_reading.charger_name == "USB-C Power Adapter"
    assert sample_reading.charger_manufacturer == "Apple Inc."


def test_power_reading_timestamp():
    """Test PowerReading timestamp is datetime with timezone."""
    reading = PowerReading(
        timestamp=datetime.now(timezone.utc),
        watts_actual=0.0,
        watts_negotiated=0,
        voltage=0.0,
        amperage=0.0,
        current_capacity=0,
        max_capacity=0,
        battery_percent=0,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    assert isinstance(reading.timestamp, datetime)
    assert reading.timestamp.tzinfo is not None


def test_power_reading_optional_fields():
    """Test PowerReading with optional fields as None."""
    reading = PowerReading(
        timestamp=datetime.now(timezone.utc),
        watts_actual=10.5,
        watts_negotiated=0,
        voltage=12.0,
        amperage=0.875,
        current_capacity=2000,
        max_capacity=4000,
        battery_percent=50,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    assert reading.charger_name is None
    assert reading.charger_manufacturer is None


def test_power_reading_negative_discharge():
    """Test PowerReading with negative watts_actual (discharging)."""
    reading = PowerReading(
        timestamp=datetime.now(timezone.utc),
        watts_actual=-15.2,  # Negative = discharging
        watts_negotiated=0,
        voltage=12.5,
        amperage=-1.216,  # Negative current
        current_capacity=3000,
        max_capacity=4709,
        battery_percent=64,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    assert reading.watts_actual < 0
    assert reading.amperage < 0
    assert reading.is_charging is False


def test_power_reading_full_battery():
    """Test PowerReading at 100% battery."""
    reading = PowerReading(
        timestamp=datetime.now(timezone.utc),
        watts_actual=0.0,
        watts_negotiated=70,
        voltage=13.34,
        amperage=0.0,
        current_capacity=4709,
        max_capacity=4709,
        battery_percent=100,
        is_charging=False,
        external_connected=True,
        charger_name="USB-C",
        charger_manufacturer=None,
    )

    assert reading.battery_percent == 100
    assert reading.current_capacity == reading.max_capacity
    assert reading.watts_actual == 0.0  # Full battery, not charging

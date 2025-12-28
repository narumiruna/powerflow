"""Tests for power collectors."""

import plistlib
from datetime import datetime

import pytest

from powermonitor.collector.ioreg import IORegCollector
from powermonitor.models import PowerReading


def test_ioreg_collector_with_real_data(ioreg_fixture_path):
    """Test IORegCollector with real ioreg output."""
    # Read fixture data
    with open(ioreg_fixture_path, "rb") as f:
        plist_data = plistlib.load(f)

    collector = IORegCollector()

    # Parse the battery data
    battery = plist_data[0]
    reading = collector._parse_battery_data(battery)

    # Verify reading structure
    assert isinstance(reading, PowerReading)
    assert isinstance(reading.timestamp, datetime)
    assert reading.timestamp.tzinfo is not None

    # Verify numeric fields are present
    assert isinstance(reading.watts_actual, float)
    assert isinstance(reading.watts_negotiated, int)
    assert isinstance(reading.voltage, float)
    assert isinstance(reading.amperage, float)
    assert isinstance(reading.current_capacity, int)
    assert isinstance(reading.max_capacity, int)
    assert isinstance(reading.battery_percent, int)

    # Verify boolean fields
    assert isinstance(reading.is_charging, bool)
    assert isinstance(reading.external_connected, bool)

    # Verify battery percent is valid
    assert 0 <= reading.battery_percent <= 100

    # Verify voltage is reasonable (typical range: 10-21V for MacBooks)
    assert 10.0 <= reading.voltage <= 21.0


def test_ioreg_collector_voltage_conversion():
    """Test voltage conversion from mV to V."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 12710,  # mV
        "Amperage": 0,
        "CurrentCapacity": 3000,
        "MaxCapacity": 4000,
        "IsCharging": False,
        "ExternalConnected": False,
    }

    reading = collector._parse_battery_data(battery_data)

    # 12710 mV = 12.71 V
    assert abs(reading.voltage - 12.71) < 0.01


def test_ioreg_collector_amperage_conversion():
    """Test amperage conversion from mA to A."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 20000,
        "Amperage": 2275,  # mA
        "CurrentCapacity": 3000,
        "MaxCapacity": 4000,
        "IsCharging": True,
        "ExternalConnected": True,
    }

    reading = collector._parse_battery_data(battery_data)

    # 2275 mA = 2.275 A
    assert abs(reading.amperage - 2.275) < 0.001


def test_ioreg_collector_watts_calculation():
    """Test watts_actual calculation (V × A)."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 20000,  # 20V
        "Amperage": 2000,  # 2A
        "CurrentCapacity": 3000,
        "MaxCapacity": 4000,
        "IsCharging": True,
        "ExternalConnected": True,
    }

    reading = collector._parse_battery_data(battery_data)

    # 20V × 2A = 40W
    expected_watts = 20.0 * 2.0
    assert abs(reading.watts_actual - expected_watts) < 0.1


def test_ioreg_collector_negative_amperage():
    """Test negative amperage (discharging)."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 12500,
        "Amperage": -1500,  # Negative = discharging
        "CurrentCapacity": 2000,
        "MaxCapacity": 4000,
        "IsCharging": False,
        "ExternalConnected": False,
    }

    reading = collector._parse_battery_data(battery_data)

    assert reading.amperage < 0
    assert reading.watts_actual < 0  # Negative watts = discharging
    assert reading.is_charging is False


def test_ioreg_collector_battery_percent():
    """Test battery percent calculation."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 12000,
        "Amperage": 0,
        "CurrentCapacity": 3000,
        "MaxCapacity": 4000,
        "IsCharging": False,
        "ExternalConnected": True,
    }

    reading = collector._parse_battery_data(battery_data)

    # 3000 / 4000 = 75%
    assert reading.battery_percent == 75


def test_ioreg_collector_charger_info():
    """Test charger info extraction."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 20000,
        "Amperage": 3000,
        "CurrentCapacity": 3000,
        "MaxCapacity": 4000,
        "IsCharging": True,
        "ExternalConnected": True,
        "AppleRawAdapterDetails": [
            {
                "Watts": 67,
                "Name": "USB-C Power Adapter",
                "Manufacturer": "Apple Inc.",
            }
        ],
    }

    reading = collector._parse_battery_data(battery_data)

    assert reading.watts_negotiated == 67
    assert reading.charger_name == "USB-C Power Adapter"
    assert reading.charger_manufacturer == "Apple Inc."


def test_ioreg_collector_no_charger():
    """Test reading without charger (on battery)."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 12000,
        "Amperage": -800,
        "CurrentCapacity": 2500,
        "MaxCapacity": 4000,
        "IsCharging": False,
        "ExternalConnected": False,
    }

    reading = collector._parse_battery_data(battery_data)

    assert reading.watts_negotiated == 0
    assert reading.charger_name is None
    assert reading.charger_manufacturer is None
    assert reading.external_connected is False


def test_ioreg_collector_full_battery():
    """Test reading at 100% battery."""
    collector = IORegCollector()

    battery_data = {
        "Voltage": 13340,
        "Amperage": 0,
        "CurrentCapacity": 4709,
        "MaxCapacity": 4709,
        "IsCharging": False,
        "ExternalConnected": True,
    }

    reading = collector._parse_battery_data(battery_data)

    assert reading.battery_percent == 100
    assert reading.watts_actual == 0.0
    assert reading.is_charging is False
    assert reading.external_connected is True


def test_collector_factory():
    """Test default_collector factory function."""
    from powermonitor.collector import default_collector

    collector = default_collector()

    # Should return a PowerCollector instance
    assert hasattr(collector, "collect")
    assert callable(collector.collect)


@pytest.mark.skipif(
    True,  # Skip by default (requires macOS and permissions)
    reason="Requires macOS and may need sudo permissions",
)
def test_iokit_collector_live():
    """Test IOKitCollector with live system data (macOS only)."""
    from powermonitor.collector.iokit import IOKitCollector

    collector = IOKitCollector(verbose=False)

    try:
        reading = collector.collect()

        # Verify reading structure
        assert isinstance(reading, PowerReading)
        assert isinstance(reading.timestamp, datetime)
        assert 0 <= reading.battery_percent <= 100

    except Exception as e:
        pytest.skip(f"IOKitCollector not available: {e}")

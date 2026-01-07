"""Tests for IOKit/SMC components."""

import struct
import sys
from typing import TYPE_CHECKING

import pytest

# Skip entire module on non-macOS platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="IOKit tests require macOS",
)

# Conditional imports to avoid loading IOKit on non-macOS
if sys.platform == "darwin" or TYPE_CHECKING:
    from powermonitor.collector.iokit.parser import bytes_to_float
    from powermonitor.collector.iokit.structures import key_to_str
    from powermonitor.collector.iokit.structures import str_to_key
    from powermonitor.collector.iokit.structures import type_to_str


def test_str_to_key():
    """Test converting 4-char string to u32 key."""
    # Test valid 4-char keys
    assert str_to_key("PDTR") > 0
    assert str_to_key("PPBR") > 0
    assert str_to_key("TB0T") > 0

    # Different strings should produce different keys
    assert str_to_key("PDTR") != str_to_key("PPBR")

    # Invalid length should return 0
    assert str_to_key("ABC") == 0
    assert str_to_key("ABCDE") == 0
    assert str_to_key("") == 0


def test_key_to_str():
    """Test converting u32 key back to string."""
    # Round-trip test
    original = "PDTR"
    key = str_to_key(original)
    result = key_to_str(key)

    assert result == original


def test_type_to_str():
    """Test converting data type u32 to string."""
    # Create a data type value (e.g., "sp78")
    data_type = int.from_bytes(b"sp78", byteorder="big")
    result = type_to_str(data_type)

    assert result == "sp78"


def test_bytes_to_float_signed_fixed_point():
    """Test parsing signed fixed-point types (sp78, sp87, etc.)."""
    # sp78: signed fixed-point divided by 256
    # Example: 0x2800 = 10240 / 256 = 40.0
    raw_bytes = struct.pack(">h", 10240)  # Big-endian signed 16-bit
    result = bytes_to_float(raw_bytes, "sp78", 2)

    assert abs(result - 40.0) < 0.01


def test_bytes_to_float_unsigned_fixed_point():
    """Test parsing unsigned fixed-point types (fp88, fp79, etc.)."""
    # fp88: unsigned fixed-point divided by 256
    # Example: 0x1000 = 4096 / 256 = 16.0
    raw_bytes = struct.pack(">H", 4096)  # Big-endian unsigned 16-bit
    result = bytes_to_float(raw_bytes, "fp88", 2)

    assert abs(result - 16.0) < 0.01


def test_bytes_to_float_ieee_754():
    """Test parsing IEEE 754 float."""
    # flt: IEEE 754 32-bit float
    # Example: 45.5
    raw_bytes = struct.pack(">f", 45.5)  # Big-endian float
    result = bytes_to_float(raw_bytes, "flt ", 4)

    assert abs(result - 45.5) < 0.01


def test_bytes_to_float_ui8():
    """Test parsing unsigned 8-bit integer."""
    raw_bytes = bytes([100])
    result = bytes_to_float(raw_bytes, "ui8 ", 1)

    assert result == 100.0


def test_bytes_to_float_ui16():
    """Test parsing unsigned 16-bit integer."""
    raw_bytes = struct.pack(">H", 1000)
    result = bytes_to_float(raw_bytes, "ui16", 2)

    assert result == 1000.0


def test_bytes_to_float_ui32():
    """Test parsing unsigned 32-bit integer."""
    raw_bytes = struct.pack(">I", 100000)
    result = bytes_to_float(raw_bytes, "ui32", 4)

    assert result == 100000.0


def test_bytes_to_float_negative_fixed_point():
    """Test parsing negative values in signed fixed-point."""
    # Negative value: -10.5 * 256 = -2688
    raw_bytes = struct.pack(">h", -2688)
    result = bytes_to_float(raw_bytes, "sp78", 2)

    assert abs(result - (-10.5)) < 0.01


def test_bytes_to_float_zero():
    """Test parsing zero values."""
    raw_bytes = struct.pack(">h", 0)
    result = bytes_to_float(raw_bytes, "sp78", 2)

    assert result == 0.0


def test_bytes_to_float_insufficient_data():
    """Test parsing with insufficient data returns 0."""
    # Only 1 byte when 2 expected
    raw_bytes = bytes([0])
    result = bytes_to_float(raw_bytes, "sp78", 2)

    assert result == 0.0


def test_bytes_to_float_unknown_type():
    """Test parsing unknown type falls back to size-based parsing."""
    # Unknown type with 2 bytes
    raw_bytes = struct.pack(">H", 1234)
    result = bytes_to_float(raw_bytes, "xxxx", 2)

    assert result == 1234.0


def test_bytes_to_float_all_fixed_point_types():
    """Test all fixed-point type variations."""
    test_value = 2560  # = 10.0 when divided by 256

    signed_types = ["sp78", "sp87", "sp96", "spa5", "spb4", "spf0"]
    for dtype in signed_types:
        raw_bytes = struct.pack(">h", test_value)
        result = bytes_to_float(raw_bytes, dtype, 2)
        assert abs(result - 10.0) < 0.01, f"Failed for {dtype}"

    unsigned_types = ["fp88", "fp79", "fp6a", "fp4c"]
    for dtype in unsigned_types:
        raw_bytes = struct.pack(">H", test_value)
        result = bytes_to_float(raw_bytes, dtype, 2)
        assert abs(result - 10.0) < 0.01, f"Failed for {dtype}"


def test_get_kern_return_name():
    """Test kern_return_t error code name mapping."""
    from powermonitor.collector.iokit.connection import _get_kern_return_name

    # Test known error codes
    assert _get_kern_return_name(0) == "KERN_SUCCESS"
    assert _get_kern_return_name(1) == "KERN_INVALID_ADDRESS"
    assert _get_kern_return_name(2) == "KERN_PROTECTION_FAILURE"
    assert _get_kern_return_name(3) == "KERN_NO_SPACE"
    assert _get_kern_return_name(4) == "KERN_INVALID_ARGUMENT"
    assert _get_kern_return_name(5) == "KERN_FAILURE"

    # Test IOKit error codes
    assert _get_kern_return_name(0xE00002C2) == "kIOReturnNoDevice"
    assert _get_kern_return_name(0xE00002C0) == "kIOReturnError"
    assert _get_kern_return_name(0xE00002C1) == "kIOReturnNoMemory"
    assert _get_kern_return_name(0xE00002C3) == "kIOReturnNoResources"

    # Test unknown error code
    unknown_code = 0xDEADBEEF
    result = _get_kern_return_name(unknown_code)
    assert "Unknown error" in result
    assert "0xDEADBEEF" in result


def test_smc_error():
    """Test SMCError exception."""
    from powermonitor.collector.iokit.connection import SMCError

    # Test basic exception
    error = SMCError("Test error message")
    assert str(error) == "Test error message"
    assert isinstance(error, Exception)


def test_smc_connection_read_key_invalid_length():
    """Test SMCConnection.read_key() with invalid key length."""
    from powermonitor.collector.iokit.connection import SMCConnection

    # Mock connection (won't actually try to open on macOS)
    conn = object.__new__(SMCConnection)
    conn.connection = 0
    conn.service = 0

    # Test keys with invalid length
    with pytest.raises(ValueError, match="must be exactly 4 characters"):
        conn.read_key("ABC")  # Too short

    with pytest.raises(ValueError, match="must be exactly 4 characters"):
        conn.read_key("ABCDE")  # Too long

    with pytest.raises(ValueError, match="must be exactly 4 characters"):
        conn.read_key("")  # Empty


def test_iokit_collector_initialization():
    """Test IOKitCollector initialization."""
    from powermonitor.collector.iokit.collector import IOKitCollector

    # Test default initialization
    collector = IOKitCollector()
    assert collector.verbose is False
    assert collector.fallback_collector is not None

    # Test verbose initialization
    collector_verbose = IOKitCollector(verbose=True)
    assert collector_verbose.verbose is True
    assert collector_verbose.fallback_collector is not None


def test_smc_power_data_initialization():
    """Test SMCPowerData dataclass initialization."""
    from powermonitor.collector.iokit.collector import SMCPowerData

    # Test default initialization (all None)
    data = SMCPowerData()
    assert data.battery_power is None
    assert data.power_input is None
    assert data.system_power is None
    assert data.heatpipe_power is None
    assert data.display_power is None
    assert data.battery_temp is None
    assert data.charging_status is None

    # Test with values
    data = SMCPowerData(
        battery_power=10.5,
        power_input=20.3,
        system_power=15.2,
        heatpipe_power=5.1,
        display_power=3.2,
        battery_temp=35.0,
        charging_status=1.0,
    )
    assert data.battery_power == 10.5
    assert data.power_input == 20.3
    assert data.system_power == 15.2
    assert data.heatpipe_power == 5.1
    assert data.display_power == 3.2
    assert data.battery_temp == 35.0
    assert data.charging_status == 1.0


def test_iokit_collector_fallback_on_smc_error(monkeypatch):
    """Test IOKitCollector falls back to IORegCollector when SMC fails."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.connection import SMCError
    from powermonitor.models import PowerReading

    # Create a mock PowerReading for fallback
    mock_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=80,
        watts_actual=15.5,
        watts_negotiated=60,
        voltage=12.0,
        amperage=1.3,
        current_capacity=5000,
        max_capacity=6000,
        is_charging=True,
        external_connected=True,
        charger_name="Test Charger",
        charger_manufacturer="Test Manufacturer",
    )

    # Mock _collect_with_smc to raise SMCError
    def mock_collect_with_smc(self):
        raise SMCError("Mock SMC connection failed")

    # Mock fallback_collector.collect to return mock reading
    def mock_fallback_collect(self):
        return mock_reading

    collector = IOKitCollector(verbose=False)

    monkeypatch.setattr(collector, "_collect_with_smc", lambda: mock_collect_with_smc(collector))
    monkeypatch.setattr(
        collector.fallback_collector, "collect", lambda: mock_fallback_collect(collector.fallback_collector)
    )

    # Should fall back without error
    reading = collector.collect()
    assert reading == mock_reading


def test_iokit_collector_fallback_on_general_exception(monkeypatch):
    """Test IOKitCollector falls back on any exception."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.models import PowerReading

    # Create a mock PowerReading for fallback
    mock_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=75,
        watts_actual=12.3,
        watts_negotiated=60,
        voltage=12.0,
        amperage=1.0,
        current_capacity=4500,
        max_capacity=6000,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    # Mock _collect_with_smc to raise a general exception
    def mock_collect_with_smc(self):
        raise RuntimeError("Unexpected error")

    # Mock fallback_collector.collect to return mock reading
    def mock_fallback_collect(self):
        return mock_reading

    collector = IOKitCollector(verbose=False)

    monkeypatch.setattr(collector, "_collect_with_smc", lambda: mock_collect_with_smc(collector))
    monkeypatch.setattr(
        collector.fallback_collector, "collect", lambda: mock_fallback_collect(collector.fallback_collector)
    )

    # Should fall back without error
    reading = collector.collect()
    assert reading == mock_reading


def test_iokit_collector_fallback_verbose_mode(monkeypatch):
    """Test IOKitCollector falls back in verbose mode."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.connection import SMCError
    from powermonitor.models import PowerReading

    mock_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=70,
        watts_actual=10.0,
        watts_negotiated=60,
        voltage=11.5,
        amperage=0.9,
        current_capacity=4200,
        max_capacity=6000,
        is_charging=True,
        external_connected=True,
        charger_name="USB-C",
        charger_manufacturer="Apple",
    )

    # Mock _collect_with_smc to raise SMCError
    def mock_collect_with_smc(self):
        raise SMCError("Mock SMC error")

    # Mock fallback_collector.collect to return mock reading
    def mock_fallback_collect(self):
        return mock_reading

    collector = IOKitCollector(verbose=True)

    monkeypatch.setattr(collector, "_collect_with_smc", lambda: mock_collect_with_smc(collector))
    monkeypatch.setattr(
        collector.fallback_collector, "collect", lambda: mock_fallback_collect(collector.fallback_collector)
    )

    # Should fall back successfully
    reading = collector.collect()
    assert reading == mock_reading


def test_collect_with_smc_enhances_reading(monkeypatch):
    """Test _collect_with_smc enhances reading with SMC power_input."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.collector import SMCPowerData
    from powermonitor.models import PowerReading

    # Mock base reading from IORegistry
    base_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=85,
        watts_actual=5.0,  # Will be overridden
        watts_negotiated=65,
        voltage=12.5,
        amperage=0.4,
        current_capacity=5100,
        max_capacity=6000,
        is_charging=True,
        external_connected=True,
        charger_name="USB PD",
        charger_manufacturer="Apple",
    )

    # Mock SMC data with power_input
    smc_data = SMCPowerData(
        power_input=18.5,
        battery_power=10.0,
        system_power=15.0,
    )

    collector = IOKitCollector(verbose=False)

    # Mock _read_smc_sensors to return our mock data
    monkeypatch.setattr(collector, "_read_smc_sensors", lambda: smc_data)

    # Mock fallback_collector.collect to return base reading
    monkeypatch.setattr(collector.fallback_collector, "collect", lambda: base_reading)

    # Collect with SMC
    reading = collector._collect_with_smc()

    # Should use PDTR (power_input) for watts_actual
    assert reading.watts_actual == 18.5
    assert reading.battery_percent == 85.0


def test_collect_with_smc_no_power_input(monkeypatch):
    """Test _collect_with_smc when power_input is None."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.collector import SMCPowerData
    from powermonitor.models import PowerReading

    # Mock base reading from IORegistry
    base_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=85,
        watts_actual=5.0,  # Should remain unchanged
        watts_negotiated=65,
        voltage=12.5,
        amperage=0.4,
        current_capacity=5100,
        max_capacity=6000,
        is_charging=False,
        external_connected=False,
        charger_name=None,
        charger_manufacturer=None,
    )

    # Mock SMC data without power_input
    smc_data = SMCPowerData(
        power_input=None,  # No PDTR data
        battery_power=10.0,
    )

    collector = IOKitCollector(verbose=False)

    monkeypatch.setattr(collector, "_read_smc_sensors", lambda: smc_data)
    monkeypatch.setattr(collector.fallback_collector, "collect", lambda: base_reading)

    # Collect with SMC
    reading = collector._collect_with_smc()

    # Should keep original watts_actual
    assert reading.watts_actual == 5.0
    assert reading.battery_percent == 85.0


def test_collect_with_smc_verbose_logging(monkeypatch):
    """Test _collect_with_smc with verbose mode enabled."""
    from datetime import datetime

    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.collector import SMCPowerData
    from powermonitor.models import PowerReading

    base_reading = PowerReading(
        timestamp=datetime.fromtimestamp(1234567890.0),
        battery_percent=90,
        watts_actual=5.0,
        watts_negotiated=87,
        voltage=13.0,
        amperage=0.4,
        current_capacity=5400,
        max_capacity=6000,
        is_charging=True,
        external_connected=True,
        charger_name="96W USB-C",
        charger_manufacturer="Apple",
    )

    smc_data = SMCPowerData(
        power_input=20.5,
        battery_power=12.3,
        system_power=18.0,
        heatpipe_power=3.5,
        display_power=2.1,
        battery_temp=35.5,
        charging_status=1.0,
    )

    collector = IOKitCollector(verbose=True)

    monkeypatch.setattr(collector, "_read_smc_sensors", lambda: smc_data)
    monkeypatch.setattr(collector.fallback_collector, "collect", lambda: base_reading)

    reading = collector._collect_with_smc()

    # Should use PDTR (power_input) for watts_actual
    assert reading.watts_actual == 20.5


def test_read_smc_sensors_with_mock_connection(monkeypatch):
    """Test _read_smc_sensors reads all sensor keys."""
    from powermonitor.collector.iokit.collector import IOKitCollector

    # Track which keys were read
    read_keys = []

    # Mock SMCConnection context manager
    class MockSMCConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def read_key(self, key: str) -> float:
            read_keys.append(key)
            # Return different values for each key
            values = {
                "PPBR": 10.5,
                "PDTR": 20.3,
                "PSTR": 15.2,
                "PHPC": 5.1,
                "PDBR": 3.2,
                "TB0T": 35.0,
                "CHCC": 1.0,
            }
            return values.get(key, 0.0)

    # Replace SMCConnection with mock
    monkeypatch.setattr("powermonitor.collector.iokit.collector.SMCConnection", MockSMCConnection)

    collector = IOKitCollector()
    data = collector._read_smc_sensors()

    # Check all keys were attempted
    assert "PPBR" in read_keys
    assert "PDTR" in read_keys
    assert "PSTR" in read_keys
    assert "PHPC" in read_keys
    assert "PDBR" in read_keys
    assert "TB0T" in read_keys
    assert "CHCC" in read_keys

    # Check values were assigned correctly
    assert data.battery_power == 10.5
    assert data.power_input == 20.3
    assert data.system_power == 15.2
    assert data.heatpipe_power == 5.1
    assert data.display_power == 3.2
    assert data.battery_temp == 35.0
    assert data.charging_status == 1.0


def test_read_smc_sensors_handles_missing_sensors(monkeypatch):
    """Test _read_smc_sensors handles missing sensors gracefully."""
    from powermonitor.collector.iokit.collector import IOKitCollector
    from powermonitor.collector.iokit.connection import SMCError

    # Mock SMCConnection that fails for some keys
    class MockSMCConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def read_key(self, key: str) -> float:
            # PDTR and TB0T succeed, others fail
            if key in ["PDTR", "TB0T"]:
                return {"PDTR": 18.0, "TB0T": 32.0}[key]
            raise SMCError(f"Sensor {key} not available")

    monkeypatch.setattr("powermonitor.collector.iokit.collector.SMCConnection", MockSMCConnection)

    collector = IOKitCollector()
    data = collector._read_smc_sensors()

    # Only PDTR and TB0T should have values
    assert data.power_input == 18.0
    assert data.battery_temp == 32.0

    # Others should be None
    assert data.battery_power is None
    assert data.system_power is None
    assert data.heatpipe_power is None
    assert data.display_power is None
    assert data.charging_status is None


@pytest.mark.skipif(
    True,  # Skip by default (requires macOS and permissions)
    reason="Requires macOS and appropriate permissions",
)
def test_smc_connection_live():
    """Test SMC connection with live system (macOS only)."""
    from powermonitor.collector.iokit import SMCConnection

    try:
        with SMCConnection() as smc:
            # Try to read a common sensor
            # Note: Not all Macs have all sensors
            keys_to_try = ["TC0P", "TB0T", "PDTR"]

            for key in keys_to_try:
                try:
                    value = smc.read_key(key)
                    assert isinstance(value, float)
                    # Temperature sensors typically 0-100°C
                    # Power sensors typically 0-100W
                    assert -50.0 <= value <= 200.0
                    print(f"Read {key}: {value}")
                    break  # Success on at least one sensor
                except Exception:
                    continue
            else:
                pytest.skip("No readable SMC sensors found")

    except Exception as e:
        pytest.skip(f"SMC connection not available: {e}")

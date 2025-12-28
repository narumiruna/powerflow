"""Tests for IOKit/SMC components."""

import struct

import pytest

from powermonitor.collector.iokit.parser import bytes_to_float
from powermonitor.collector.iokit.structures import str_to_key, key_to_str, type_to_str


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

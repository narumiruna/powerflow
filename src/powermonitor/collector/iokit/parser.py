"""Binary data parsing for SMC sensor values."""

import struct


def _parse_signed_fixed(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    raw = struct.unpack(">h", data[:2])[0]
    return raw / 256.0


def _parse_unsigned_fixed(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    raw = struct.unpack(">H", data[:2])[0]
    return raw / 256.0


def _parse_float(data: bytes) -> float:
    if len(data) < 4:
        return 0.0
    return struct.unpack(">f", data[:4])[0]


def _parse_ui8(data: bytes) -> float:
    if len(data) < 1:
        return 0.0
    return float(data[0])


def _parse_ui16(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    return float(struct.unpack(">H", data[:2])[0])


def _parse_ui32(data: bytes) -> float:
    if len(data) < 4:
        return 0.0
    return float(struct.unpack(">I", data[:4])[0])


def _parse_unknown(data: bytes, data_size: int) -> float:
    if data_size == 1 and len(data) >= 1:
        return float(data[0])
    if data_size == 2 and len(data) >= 2:
        return float(struct.unpack(">H", data[:2])[0])
    if data_size == 4 and len(data) >= 4:
        return float(struct.unpack(">I", data[:4])[0])
    return 0.0


def bytes_to_float(data: bytes, data_type: str, data_size: int) -> float:
    """Convert raw SMC bytes to float based on data type.

    Supports 13 SMC data types with proper big-endian conversion.

    Args:
        data: Raw bytes from SMC
        data_type: 4-character type string (e.g., "sp78", "flt ", "ui16")
        data_size: Number of bytes in the value

    Returns:
        Parsed float value

    Raises:
        ValueError: If data is insufficient for the type
    """
    data_type = data_type.ljust(4)
    signed_fixed_types = {"sp78", "sp87", "sp96", "spa5", "spb4", "spf0"}
    unsigned_fixed_types = {"fp88", "fp79", "fp6a", "fp4c"}
    type_parsers = {
        "flt ": _parse_float,
        "ui8 ": _parse_ui8,
        "ui16": _parse_ui16,
        "ui32": _parse_ui32,
    }

    if data_type in signed_fixed_types:
        return _parse_signed_fixed(data)
    if data_type in unsigned_fixed_types:
        return _parse_unsigned_fixed(data)
    if data_type in type_parsers:
        return type_parsers[data_type](data)
    return _parse_unknown(data, data_size)

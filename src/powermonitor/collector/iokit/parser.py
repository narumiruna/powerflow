"""Binary data parsing for SMC sensor values."""

import struct


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
    # Ensure data_type is padded to 4 characters
    data_type = data_type.ljust(4)

    # Signed fixed-point types (divide by 256)
    if data_type in ("sp78", "sp87", "sp96", "spa5", "spb4", "spf0"):
        if len(data) < 2:
            return 0.0
        # Big-endian signed 16-bit integer
        raw = struct.unpack(">h", data[:2])[0]
        return raw / 256.0

    # Unsigned fixed-point types (divide by 256)
    elif data_type in ("fp88", "fp79", "fp6a", "fp4c"):
        if len(data) < 2:
            return 0.0
        # Big-endian unsigned 16-bit integer
        raw = struct.unpack(">H", data[:2])[0]
        return raw / 256.0

    # IEEE 754 float (4 bytes)
    elif data_type == "flt ":
        if len(data) < 4:
            return 0.0
        # Big-endian float
        return struct.unpack(">f", data[:4])[0]

    # Unsigned 8-bit integer
    elif data_type == "ui8 ":
        if len(data) < 1:
            return 0.0
        return float(data[0])

    # Unsigned 16-bit integer
    elif data_type == "ui16":
        if len(data) < 2:
            return 0.0
        return float(struct.unpack(">H", data[:2])[0])

    # Unsigned 32-bit integer
    elif data_type == "ui32":
        if len(data) < 4:
            return 0.0
        return float(struct.unpack(">I", data[:4])[0])

    # Unknown type - try to parse as unsigned integer based on size
    else:
        if data_size == 1 and len(data) >= 1:
            return float(data[0])
        elif data_size == 2 and len(data) >= 2:
            return float(struct.unpack(">H", data[:2])[0])
        elif data_size == 4 and len(data) >= 4:
            return float(struct.unpack(">I", data[:4])[0])
        else:
            return 0.0

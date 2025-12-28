"""SMC data structures matching the C layout."""

from ctypes import Structure
from ctypes import c_uint8
from ctypes import c_uint16
from ctypes import c_uint32

# SMC Constants
KERNEL_INDEX_SMC = 2
SMC_CMD_READ_BYTES = 5
SMC_CMD_READ_KEYINFO = 9
SMC_KEY_SIZE = 4
SMC_DATA_SIZE = 32
SMC_BYTES_SIZE = 32


class SMCVersion(Structure):
    """SMC version structure."""

    _pack_ = 1  # Packed C struct
    _fields_ = [
        ("major", c_uint8),
        ("minor", c_uint8),
        ("build", c_uint8),
        ("reserved", c_uint8),
        ("release", c_uint16),
    ]


class SMCPLimitData(Structure):
    """SMC power limit data."""

    _pack_ = 1
    _fields_ = [
        ("version", c_uint16),
        ("length", c_uint16),
        ("cpu_plimit", c_uint32),
        ("gpu_plimit", c_uint32),
        ("mem_plimit", c_uint32),
    ]


class KeyInfo(Structure):
    """SMC key information."""

    _pack_ = 1
    _fields_ = [
        ("data_size", c_uint32),
        ("data_type", c_uint32),
        ("data_attributes", c_uint8),
    ]


class SMCKeyData(Structure):
    """SMC key data structure (80 bytes total)."""

    _pack_ = 1
    _fields_ = [
        ("key", c_uint32),
        ("vers", SMCVersion),
        ("p_limit_data", SMCPLimitData),
        ("key_info", KeyInfo),
        ("result", c_uint8),
        ("status", c_uint8),
        ("data8", c_uint8),
        ("data32", c_uint32),
        ("bytes", c_uint8 * SMC_BYTES_SIZE),
    ]


def str_to_key(s: str) -> int:
    """Convert 4-character SMC key string to u32 (big-endian).

    Args:
        s: 4-character key string (e.g., "PDTR")

    Returns:
        u32 key value in big-endian format
    """
    if len(s) != 4:
        return 0

    bytes_val = s.encode("ascii")
    return int.from_bytes(bytes_val, byteorder="big")


def key_to_str(key: int) -> str:
    """Convert u32 key to 4-character string.

    Args:
        key: u32 key value

    Returns:
        4-character string
    """
    bytes_val = key.to_bytes(4, byteorder="big")
    return bytes_val.decode("ascii", errors="replace")


def type_to_str(data_type: int) -> str:
    """Convert data type u32 to string.

    Args:
        data_type: u32 data type value

    Returns:
        4-character type string
    """
    bytes_val = data_type.to_bytes(4, byteorder="big")
    return bytes_val.decode("ascii", errors="replace")

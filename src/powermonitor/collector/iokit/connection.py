"""SMC connection for reading sensor values."""

import ctypes

from loguru import logger

from .bindings import KERN_SUCCESS
from .bindings import IOConnectCallStructMethod
from .bindings import IOIteratorNext
from .bindings import IOMasterPort
from .bindings import IOObjectRelease
from .bindings import IOServiceClose
from .bindings import IOServiceGetMatchingServices
from .bindings import IOServiceMatching
from .bindings import IOServiceOpen
from .bindings import mach_task_self
from .parser import bytes_to_float
from .structures import KERNEL_INDEX_SMC
from .structures import SMC_CMD_READ_BYTES
from .structures import SMC_CMD_READ_KEYINFO
from .structures import KeyInfo
from .structures import SMCKeyData
from .structures import key_to_str
from .structures import str_to_key
from .structures import type_to_str


class SMCError(Exception):
    """SMC operation error."""


def _get_kern_return_name(kr: int) -> str:
    """Get human-readable name for kern_return_t error code.

    Args:
        kr: kern_return_t error code

    Returns:
        String describing the error code
    """
    # Common IOKit error codes
    # From mach/kern_return.h and IOKit/IOReturn.h
    error_names = {
        0: "KERN_SUCCESS",
        1: "KERN_INVALID_ADDRESS",
        2: "KERN_PROTECTION_FAILURE",
        3: "KERN_NO_SPACE",
        4: "KERN_INVALID_ARGUMENT",
        5: "KERN_FAILURE",
        0xE00002C2: "kIOReturnNoDevice",
        0xE00002C0: "kIOReturnError",
        0xE00002C1: "kIOReturnNoMemory",
        0xE00002C3: "kIOReturnNoResources",
        0xE00002C7: "kIOReturnBusy",
        0xE00002C8: "kIOReturnTimeout",
        0xE00002D8: "kIOReturnNotPrivileged",
        0xE00002E2: "kIOReturnExclusiveAccess",
    }
    return error_names.get(kr, f"Unknown error 0x{kr:08X}")


class SMCConnection:
    """Connection to AppleSMC for reading sensor values.

    Usage:
        with SMCConnection() as smc:
            power = smc.read_key("PDTR")  # Read power delivery rate
            temp = smc.read_key("TB0T")   # Read battery temperature
    """

    def __init__(self):
        """Open connection to AppleSMC.

        Raises:
            SMCError: If connection fails
        """
        self.connection: int = 0
        self.service: int = 0
        self._open()

    def _open(self) -> None:
        """Open IOKit connection to AppleSMC.

        Raises:
            SMCError: If any IOKit operation fails
        """
        logger.debug("Opening IOKit connection to AppleSMC")

        # Get master port
        master_port = ctypes.c_uint32(0)
        kr = IOMasterPort(0, ctypes.byref(master_port))
        if kr != KERN_SUCCESS:
            error_name = _get_kern_return_name(kr)
            raise SMCError(f"IOMasterPort failed: {error_name} ({kr})")

        logger.debug("IOMasterPort successful")

        # Find AppleSMC service
        matching = IOServiceMatching(b"AppleSMC\0")
        if not matching:
            raise SMCError("IOServiceMatching returned NULL (out of memory or invalid name)")

        # Get matching services
        iterator = ctypes.c_uint32(0)
        kr = IOServiceGetMatchingServices(master_port.value, matching, ctypes.byref(iterator))
        if kr != KERN_SUCCESS:
            error_name = _get_kern_return_name(kr)
            raise SMCError(f"IOServiceGetMatchingServices failed: {error_name} ({kr})")

        # Get first matching service
        self.service = IOIteratorNext(iterator.value)

        # Release iterator regardless of success
        kr_release = IOObjectRelease(iterator.value)
        if kr_release != KERN_SUCCESS:
            logger.warning(f"Failed to release iterator: {_get_kern_return_name(kr_release)} ({kr_release})")

        if self.service == 0:
            raise SMCError("AppleSMC service not found (IOIteratorNext returned 0)")

        logger.debug(f"Found AppleSMC service: {self.service}")

        # Open connection to service
        connection = ctypes.c_uint32(0)
        kr = IOServiceOpen(self.service, mach_task_self(), 0, ctypes.byref(connection))
        if kr != KERN_SUCCESS:
            error_name = _get_kern_return_name(kr)
            # Clean up service before raising
            kr_release = IOObjectRelease(self.service)
            if kr_release != KERN_SUCCESS:
                release_error = _get_kern_return_name(kr_release)
                logger.warning(f"Failed to release service during cleanup: {release_error} ({kr_release})")
            self.service = 0
            raise SMCError(f"IOServiceOpen failed: {error_name} ({kr}). Try running with sudo?")

        self.connection = connection.value
        logger.debug(f"IOKit connection established: {self.connection}")

    def read_key(self, key: str) -> float:
        """Read SMC sensor key and return value as float.

        Args:
            key: 4-character SMC key (e.g., "PDTR", "TB0T")

        Returns:
            Sensor value as float

        Raises:
            SMCError: If read fails
            ValueError: If key is invalid format
        """
        if len(key) != 4:
            raise ValueError(f"SMC key must be exactly 4 characters, got: '{key}' ({len(key)} chars)")

        logger.debug(f"Reading SMC key: {key}")
        key_code = str_to_key(key)

        # First get key info (data type and size)
        key_info = self._read_key_info(key_code)
        data_type = type_to_str(key_info.data_type)
        logger.debug(f"Key {key} info: type={data_type}, size={key_info.data_size}")

        # Then read the actual value bytes
        value_bytes = self._read_key_bytes(key_code, key_info)

        # Convert bytes to float based on data type
        value = bytes_to_float(value_bytes, data_type, key_info.data_size)
        logger.debug(f"Key {key} value: {value}")

        return value

    def _read_key_info(self, key: int) -> KeyInfo:
        """Read key metadata (data type and size).

        Args:
            key: u32 key code

        Returns:
            KeyInfo structure

        Raises:
            SMCError: If read fails
        """
        input_data = SMCKeyData()
        output_data = SMCKeyData()

        input_data.key = key
        input_data.data8 = SMC_CMD_READ_KEYINFO

        input_size = ctypes.sizeof(SMCKeyData)
        output_size = ctypes.c_uint(ctypes.sizeof(SMCKeyData))

        kr = IOConnectCallStructMethod(
            self.connection,
            KERNEL_INDEX_SMC,
            ctypes.byref(input_data),
            input_size,
            ctypes.byref(output_data),
            ctypes.byref(output_size),
        )

        if kr != KERN_SUCCESS:
            key_name = key_to_str(key)
            error_name = _get_kern_return_name(kr)
            raise SMCError(f"Read key info failed for '{key_name}': {error_name} ({kr})")

        return output_data.key_info

    def _read_key_bytes(self, key: int, key_info: KeyInfo) -> bytes:
        """Read key value bytes.

        Args:
            key: u32 key code
            key_info: KeyInfo from _read_key_info

        Returns:
            Raw bytes of the sensor value

        Raises:
            SMCError: If read fails
        """
        input_data = SMCKeyData()
        output_data = SMCKeyData()

        input_data.key = key
        input_data.data8 = SMC_CMD_READ_BYTES
        input_data.key_info = key_info

        input_size = ctypes.sizeof(SMCKeyData)
        output_size = ctypes.c_uint(ctypes.sizeof(SMCKeyData))

        kr = IOConnectCallStructMethod(
            self.connection,
            KERNEL_INDEX_SMC,
            ctypes.byref(input_data),
            input_size,
            ctypes.byref(output_data),
            ctypes.byref(output_size),
        )

        if kr != KERN_SUCCESS:
            key_name = key_to_str(key)
            error_name = _get_kern_return_name(kr)
            raise SMCError(f"Read key bytes failed for '{key_name}': {error_name} ({kr})")

        # Extract bytes up to data_size
        size = key_info.data_size
        return bytes(output_data.bytes[:size])

    def close(self) -> None:
        """Close SMC connection and release resources.

        Always attempts to close both connection and service, even if one fails.
        Logs warnings for any cleanup failures but does not raise exceptions.
        """
        logger.debug("Closing IOKit connection")

        # Close connection first
        if self.connection != 0:
            kr = IOServiceClose(self.connection)
            if kr != KERN_SUCCESS:
                error_name = _get_kern_return_name(kr)
                logger.warning(f"IOServiceClose failed: {error_name} ({kr}) for connection {self.connection}")
            else:
                logger.debug(f"IOServiceClose successful for connection {self.connection}")
            self.connection = 0

        # Release service object
        if self.service != 0:
            kr = IOObjectRelease(self.service)
            if kr != KERN_SUCCESS:
                error_name = _get_kern_return_name(kr)
                logger.warning(f"IOObjectRelease failed: {error_name} ({kr}) for service {self.service}")
            else:
                logger.debug(f"IOObjectRelease successful for service {self.service}")
            self.service = 0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensure resources are released."""
        self.close()

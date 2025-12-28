"""SMC connection for reading sensor values."""

import ctypes

from .bindings import (
    KERN_SUCCESS,
    IOMasterPort,
    IOServiceMatching,
    IOServiceGetMatchingServices,
    IOIteratorNext,
    IOObjectRelease,
    IOServiceOpen,
    IOServiceClose,
    IOConnectCallStructMethod,
    mach_task_self,
)
from .structures import (
    SMCKeyData,
    KeyInfo,
    str_to_key,
    key_to_str,
    type_to_str,
    KERNEL_INDEX_SMC,
    SMC_CMD_READ_KEYINFO,
    SMC_CMD_READ_BYTES,
)
from .parser import bytes_to_float


class SMCError(Exception):
    """SMC operation error."""

    pass


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
        """Open IOKit connection to AppleSMC."""
        # Get master port
        master_port = ctypes.c_uint32(0)
        kr = IOMasterPort(0, ctypes.byref(master_port))
        if kr != KERN_SUCCESS:
            raise SMCError(f"IOMasterPort failed: {kr}")

        # Find AppleSMC service
        matching = IOServiceMatching(b"AppleSMC\0")
        if not matching:
            raise SMCError("IOServiceMatching failed")

        # Get matching services
        iterator = ctypes.c_uint32(0)
        kr = IOServiceGetMatchingServices(
            master_port.value, matching, ctypes.byref(iterator)
        )
        if kr != KERN_SUCCESS:
            raise SMCError(f"IOServiceGetMatchingServices failed: {kr}")

        # Get first matching service
        self.service = IOIteratorNext(iterator.value)
        IOObjectRelease(iterator.value)

        if self.service == 0:
            raise SMCError("AppleSMC service not found")

        # Open connection to service
        connection = ctypes.c_uint32(0)
        kr = IOServiceOpen(self.service, mach_task_self(), 0, ctypes.byref(connection))
        if kr != KERN_SUCCESS:
            IOObjectRelease(self.service)
            raise SMCError(f"IOServiceOpen failed: {kr}")

        self.connection = connection.value

    def read_key(self, key: str) -> float:
        """Read SMC sensor key and return value as float.

        Args:
            key: 4-character SMC key (e.g., "PDTR", "TB0T")

        Returns:
            Sensor value as float

        Raises:
            SMCError: If read fails
        """
        key_code = str_to_key(key)

        # First get key info (data type and size)
        key_info = self._read_key_info(key_code)

        # Then read the actual value bytes
        value_bytes = self._read_key_bytes(key_code, key_info)

        # Convert bytes to float based on data type
        data_type = type_to_str(key_info.data_type)
        value = bytes_to_float(value_bytes, data_type, key_info.data_size)

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
            raise SMCError(f"Read key info failed for {key_to_str(key)}: {kr}")

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
            raise SMCError(f"Read key bytes failed for {key_to_str(key)}: {kr}")

        # Extract bytes up to data_size
        size = key_info.data_size
        return bytes(output_data.bytes[:size])

    def close(self) -> None:
        """Close SMC connection and release resources."""
        if self.connection != 0:
            IOServiceClose(self.connection)
            self.connection = 0

        if self.service != 0:
            IOObjectRelease(self.service)
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

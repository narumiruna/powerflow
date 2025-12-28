"""ctypes bindings for IOKit framework."""

from ctypes import CDLL
from ctypes import POINTER
from ctypes import c_char_p
from ctypes import c_int
from ctypes import c_uint
from ctypes import c_uint32
from ctypes import c_void_p

# Load IOKit framework
iokit = CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")

# Type aliases matching IOKit
mach_port_t = c_uint32
io_object_t = c_uint32
io_connect_t = c_uint32
io_iterator_t = c_uint32
kern_return_t = c_int

# Constants
KERN_SUCCESS = 0

# Function signatures
IOMasterPort = iokit.IOMasterPort
IOMasterPort.argtypes = [mach_port_t, POINTER(mach_port_t)]
IOMasterPort.restype = kern_return_t

IOServiceMatching = iokit.IOServiceMatching
IOServiceMatching.argtypes = [c_char_p]
IOServiceMatching.restype = c_void_p

IOServiceGetMatchingServices = iokit.IOServiceGetMatchingServices
IOServiceGetMatchingServices.argtypes = [mach_port_t, c_void_p, POINTER(io_iterator_t)]
IOServiceGetMatchingServices.restype = kern_return_t

IOIteratorNext = iokit.IOIteratorNext
IOIteratorNext.argtypes = [io_iterator_t]
IOIteratorNext.restype = io_object_t

IOObjectRelease = iokit.IOObjectRelease
IOObjectRelease.argtypes = [io_object_t]
IOObjectRelease.restype = kern_return_t

# Get mach_task_self() - special case
# mach_task_self_ is not a function but a global variable holding the task port
# We access it using CDLL to get the variable address
libsystem = CDLL("/usr/lib/system/libsystem_kernel.dylib")

# mach_task_self_ is a global variable, not a function
# We need to access it using in_dll
_mach_task_self_port = c_uint32.in_dll(libsystem, "mach_task_self_")


def mach_task_self() -> int:
    """Get the current mach task port.

    Returns the value of the global mach_task_self_ variable.
    """
    return _mach_task_self_port.value


IOServiceOpen = iokit.IOServiceOpen
IOServiceOpen.argtypes = [io_object_t, mach_port_t, c_uint32, POINTER(io_connect_t)]
IOServiceOpen.restype = kern_return_t

IOServiceClose = iokit.IOServiceClose
IOServiceClose.argtypes = [io_connect_t]
IOServiceClose.restype = kern_return_t

IOConnectCallStructMethod = iokit.IOConnectCallStructMethod
IOConnectCallStructMethod.argtypes = [
    io_connect_t,  # connection
    c_uint32,  # selector (KERNEL_INDEX_SMC = 2)
    c_void_p,  # input struct
    c_uint,  # input struct size
    c_void_p,  # output struct
    POINTER(c_uint),  # output struct size (in/out)
]
IOConnectCallStructMethod.restype = kern_return_t

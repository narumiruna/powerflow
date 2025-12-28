"""Collector factory - provides default collector based on platform and capabilities.

Matches Rust implementation from powerflow-core/src/collector/mod.rs
"""

import sys

from .base import PowerCollector
from .ioreg import IORegCollector


def default_collector() -> PowerCollector:
    """Get the default power collector for this platform.

    Returns IOKitCollector if available (requires IOKit feature),
    otherwise falls back to IORegCollector (subprocess-based).

    Returns:
        PowerCollector instance

    Raises:
        RuntimeError: If platform is not macOS
    """
    if sys.platform != "darwin":
        raise RuntimeError("PowerFlow only supports macOS")

    # For now, always use IORegCollector
    # TODO: Try IOKitCollector first, fallback to IORegCollector on permission error
    # try:
    #     from .iokit import IOKitCollector
    #     return IOKitCollector()
    # except (ImportError, PermissionError, OSError):
    #     return IORegCollector()

    return IORegCollector()

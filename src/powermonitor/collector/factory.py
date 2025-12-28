"""Collector factory - provides default collector based on platform and capabilities."""

import sys

from loguru import logger

from .base import PowerCollector
from .ioreg import IORegCollector


def default_collector(verbose: bool = False) -> PowerCollector:
    """Get the default power collector for this platform.

    Returns IOKitCollector if available (direct SMC access),
    otherwise falls back to IORegCollector (subprocess-based).

    Args:
        verbose: If True, print debug info about collector selection and SMC sensors

    Returns:
        PowerCollector instance

    Raises:
        RuntimeError: If platform is not macOS
    """
    if sys.platform != "darwin":
        raise RuntimeError("powermonitor only supports macOS")

    # Try IOKitCollector first (direct SMC access for better accuracy)
    # Falls back to IORegCollector if SMC access fails
    try:
        from .iokit import IOKitCollector

        if verbose:
            logger.info("Using IOKitCollector (SMC sensors)")
        return IOKitCollector(verbose=verbose)
    except (ImportError, PermissionError, OSError) as e:
        if verbose:
            logger.warning(f"IOKitCollector unavailable ({e}), using IORegCollector")
        return IORegCollector()

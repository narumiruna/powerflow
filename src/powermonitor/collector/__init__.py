"""Power data collectors for macOS."""

from .base import PowerCollector
from .factory import default_collector

__all__ = ["PowerCollector", "default_collector"]

"""Base protocol for power collectors."""

from typing import Protocol

from ..models import PowerReading


class PowerCollector(Protocol):
    """Protocol for power data collectors.

    Matches Rust's PowerCollector trait from powerflow-core/src/collector/mod.rs
    """

    def collect(self) -> PowerReading:
        """Collect current power reading from the system.

        Returns:
            PowerReading with current power data

        Raises:
            PowerCollectorError: If collection fails
        """
        ...

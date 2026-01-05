"""Configuration management for powermonitor."""

from dataclasses import dataclass


@dataclass(slots=True)
class PowerMonitorConfig:
    """Configuration for powermonitor application.

    Attributes:
        collection_interval: Time between data collections in seconds (must be > 0)
        stats_history_limit: Number of readings to include in statistics (must be > 0)
        chart_history_limit: Number of readings to display in chart (must be > 0)
    """

    collection_interval: float = 1.0  # seconds
    stats_history_limit: int = 100  # number of readings for statistics
    chart_history_limit: int = 60  # number of readings to display in chart

    def __post_init__(self) -> None:
        """Validate configuration values after initialization.

        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.collection_interval <= 0:
            raise ValueError(f"collection_interval must be positive, got {self.collection_interval}")

        if self.stats_history_limit <= 0:
            raise ValueError(f"stats_history_limit must be positive, got {self.stats_history_limit}")

        if self.chart_history_limit <= 0:
            raise ValueError(f"chart_history_limit must be positive, got {self.chart_history_limit}")

        # Warn about very short intervals (performance concerns)
        if self.collection_interval < 0.1:
            import warnings

            warnings.warn(
                f"Very short collection interval ({self.collection_interval}s) may cause high CPU usage. "
                "Recommended minimum: 0.5s",
                UserWarning,
                stacklevel=2,
            )

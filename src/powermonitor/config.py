"""Configuration management for powermonitor."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PowerMonitorConfig:
    """Configuration for powermonitor application.

    Attributes:
        collection_interval: Time between data collections in seconds (must be > 0)
        stats_history_limit: Number of readings to include in statistics (must be > 0)
        chart_history_limit: Number of readings to display in chart (must be > 0)
        database_path: Path to SQLite database file
        default_history_limit: Default number of readings for history command (must be > 0)
        default_export_limit: Default number of readings for export command (must be > 0)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    collection_interval: float = 1.0  # seconds
    stats_history_limit: int = 100  # number of readings for statistics
    chart_history_limit: int = 60  # number of readings to display in chart
    database_path: Path = Path.home() / ".powermonitor" / "powermonitor.db"
    default_history_limit: int = 20  # default for history command
    default_export_limit: int = 1000  # default for export command
    log_level: str = "INFO"  # logging level

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

        if self.default_history_limit <= 0:
            raise ValueError(f"default_history_limit must be positive, got {self.default_history_limit}")

        if self.default_export_limit <= 0:
            raise ValueError(f"default_export_limit must be positive, got {self.default_export_limit}")

        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"log_level must be one of {valid_levels}, got {self.log_level}. "
                "Valid values: DEBUG, INFO, WARNING, ERROR"
            )

        # Normalize log level to uppercase
        self.log_level = self.log_level.upper()

        # Ensure database_path is a Path object
        if not isinstance(self.database_path, Path):
            self.database_path = Path(self.database_path)

        # Warn about very short intervals (performance concerns)
        if self.collection_interval < 0.1:
            import warnings

            warnings.warn(
                f"Very short collection interval ({self.collection_interval}s) may cause high CPU usage. "
                "Recommended minimum: 0.5s",
                UserWarning,
                stacklevel=2,
            )

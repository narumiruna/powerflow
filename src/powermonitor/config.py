"""Configuration management for powermonitor."""

from dataclasses import dataclass
from pathlib import Path


def _get_default_db_path() -> Path:
    """Get default database path.

    This is a factory function to avoid evaluating Path.home() at module import time.

    Returns:
        Path to default database location
    """
    return Path.home() / ".powermonitor" / "powermonitor.db"


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
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR) - stored in uppercase

    Notes:
        - log_level is automatically normalized to uppercase in __post_init__
        - database_path is converted to Path object if needed in __post_init__
        - Very short collection intervals (&lt;0.1s) trigger a performance warning
    """

    collection_interval: float = 1.0  # seconds
    stats_history_limit: int = 100  # number of readings for statistics
    chart_history_limit: int = 60  # number of readings to display in chart
    database_path: Path | str = _get_default_db_path()  # Will use factory default if None
    default_history_limit: int = 20  # default for history command
    default_export_limit: int = 1000  # default for export command
    log_level: str = "INFO"  # logging level (normalized to uppercase)

    def __post_init__(self) -> None:
        """Validate and normalize configuration values after initialization.

        This method performs necessary normalization (log_level uppercase, database_path
        conversion) using object.__setattr__() to work with slots=True dataclasses.

        Normalization is done here rather than before instance creation because:
        1. It allows users to pass lowercase log levels (more user-friendly)
        2. It allows passing string paths that get converted to Path objects
        3. It provides a factory default for database_path when None

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Ensure database_path is a Path object with expanded user path
        if not isinstance(self.database_path, Path):
            object.__setattr__(self, "database_path", Path(self.database_path).expanduser())
        else:
            object.__setattr__(self, "database_path", self.database_path.expanduser())

        # Normalize and validate log_level
        if not isinstance(self.log_level, str):
            raise ValueError(f"log_level must be a string, got {type(self.log_level).__name__}")
        object.__setattr__(self, "log_level", self.log_level.upper())

        # Validate numeric parameters
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
        valid_levels_str = ", ".join(sorted(valid_levels))
        if self.log_level not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels_str}, got {self.log_level}.")

        # Warn about very short intervals (performance concerns)
        if self.collection_interval < 0.1:
            import warnings

            warnings.warn(
                f"Very short collection interval ({self.collection_interval}s) may cause high CPU usage. "
                "Recommended minimum: 0.5s",
                UserWarning,
                stacklevel=2,
            )

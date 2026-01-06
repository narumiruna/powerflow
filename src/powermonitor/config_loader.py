"""Configuration file loader for powermonitor."""

import tomllib
from pathlib import Path

from loguru import logger

from .config import PowerMonitorConfig


def get_config_path() -> Path:
    """Get path to user configuration file.

    Returns:
        Path to ~/.powermonitor/config.toml
    """
    return Path.home() / ".powermonitor" / "config.toml"


def load_config() -> PowerMonitorConfig:  # noqa: C901
    """Load configuration from TOML file or use defaults.

    Priority: Config file > Defaults
    (CLI arguments will override in cli.py)

    If config file doesn't exist or is invalid, falls back to defaults
    with a warning message.

    Returns:
        PowerMonitorConfig with merged settings

    Examples:
        # Without config file - uses defaults
        config = load_config()

        # With config file - merges with defaults
        config = load_config()
        # CLI can then override: config.collection_interval = 2.0
    """
    config_path = get_config_path()

    # Get default values from PowerMonitorConfig (single source of truth)
    default_config = PowerMonitorConfig()
    defaults = {
        "tui": {
            "interval": default_config.collection_interval,
            "stats_limit": default_config.stats_history_limit,
            "chart_limit": default_config.chart_history_limit,
        },
        "database": {
            "path": str(default_config.database_path),
        },
        "cli": {
            "default_history_limit": default_config.default_history_limit,
            "default_export_limit": default_config.default_export_limit,
        },
        "logging": {
            "level": default_config.log_level,
        },
    }

    # Try to load user config if it exists
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                user_config = tomllib.load(f)

            # Merge user config with defaults (user values override defaults)
            for section, values in user_config.items():
                if section in defaults and isinstance(defaults[section], dict):
                    if isinstance(values, dict):
                        defaults[section].update(values)
                    else:
                        logger.warning(
                            f"Config section [{section}] in {config_path} must be a table, "
                            f"but got {type(values).__name__} - ignoring section"
                        )
                else:
                    # Log warning for unknown sections but don't fail
                    logger.warning(f"Unknown config section [{section}] in {config_path} - ignoring")

        except tomllib.TOMLDecodeError as e:
            logger.warning(f"Failed to parse TOML config from {config_path}: {e}")
            logger.warning("Using default configuration")
        except OSError as e:
            logger.warning(f"Failed to read config file {config_path}: {e}")
            logger.warning("Using default configuration")

    # Expand ~ in database path to absolute path
    db_path_str: str = str(defaults["database"]["path"])
    db_path = Path(db_path_str).expanduser()

    # Validate and convert configuration values before constructing PowerMonitorConfig
    try:
        collection_interval = defaults["tui"]["interval"]
        try:
            collection_interval = float(collection_interval)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid 'tui.interval' value {collection_interval!r}; expected a number") from None

        stats_history_limit = defaults["tui"]["stats_limit"]
        try:
            stats_history_limit = int(stats_history_limit)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid 'tui.stats_limit' value {stats_history_limit!r}; expected an integer") from None

        chart_history_limit = defaults["tui"]["chart_limit"]
        try:
            chart_history_limit = int(chart_history_limit)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid 'tui.chart_limit' value {chart_history_limit!r}; expected an integer") from None

        default_history_limit = defaults["cli"]["default_history_limit"]
        try:
            default_history_limit = int(default_history_limit)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid 'cli.default_history_limit' value {default_history_limit!r}; expected an integer"
            ) from None

        default_export_limit = defaults["cli"]["default_export_limit"]
        try:
            default_export_limit = int(default_export_limit)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid 'cli.default_export_limit' value {default_export_limit!r}; expected an integer"
            ) from None

        log_level = defaults["logging"]["level"]
        # Ensure log_level is a string; avoid surprising conversions of non-string types
        if not isinstance(log_level, str):
            raise ValueError(f"Invalid 'logging.level' value {log_level!r}; expected a string")

        # Create PowerMonitorConfig instance (validation happens in __post_init__)
        # Type assertions help type checker understand these are the correct types
        return PowerMonitorConfig(
            collection_interval=collection_interval,
            stats_history_limit=stats_history_limit,
            chart_history_limit=chart_history_limit,
            database_path=db_path,
            default_history_limit=default_history_limit,
            default_export_limit=default_export_limit,
            log_level=log_level,
        )
    except ValueError as e:
        # Config validation failed - log error and use completely safe defaults
        logger.error(f"Invalid configuration values: {e}")
        logger.warning("Falling back to safe default configuration")
        return PowerMonitorConfig()  # Use all defaults

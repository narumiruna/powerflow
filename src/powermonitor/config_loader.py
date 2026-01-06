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


def load_config() -> PowerMonitorConfig:
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

    # Default values (matching PowerMonitorConfig defaults)
    defaults = {
        "tui": {
            "interval": 1.0,
            "stats_limit": 100,
            "chart_limit": 60,
        },
        "database": {
            "path": "~/.powermonitor/powermonitor.db",
        },
        "cli": {
            "default_history_limit": 20,
            "default_export_limit": 1000,
        },
        "logging": {
            "level": "INFO",
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
                    defaults[section].update(values)
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

    # Create PowerMonitorConfig instance (validation happens in __post_init__)
    # Type assertions help type checker understand these are the correct types
    try:
        return PowerMonitorConfig(
            collection_interval=float(defaults["tui"]["interval"]),
            stats_history_limit=int(defaults["tui"]["stats_limit"]),
            chart_history_limit=int(defaults["tui"]["chart_limit"]),
            database_path=db_path,
            default_history_limit=int(defaults["cli"]["default_history_limit"]),
            default_export_limit=int(defaults["cli"]["default_export_limit"]),
            log_level=str(defaults["logging"]["level"]),
        )
    except ValueError as e:
        # Config validation failed - log error and use completely safe defaults
        logger.error(f"Invalid configuration values: {e}")
        logger.warning("Falling back to safe default configuration")
        return PowerMonitorConfig()  # Use all defaults

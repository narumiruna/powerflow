"""Configuration file loader for powermonitor."""

import tomllib
from pathlib import Path
from typing import Any

from loguru import logger

from .config import PowerMonitorConfig


def get_config_path() -> Path:
    """Get path to user configuration file.

    Returns:
        Path to ~/.powermonitor/config.toml
    """
    return Path.home() / ".powermonitor" / "config.toml"


def _convert_to_type(value: Any, target_type: type, field_name: str) -> Any:
    """Convert a value to the target type with descriptive error messages.

    Args:
        value: The value to convert
        target_type: The type to convert to (int, float, str, etc.)
        field_name: Dotted field name for error messages (e.g., 'tui.interval')

    Returns:
        Converted value

    Raises:
        ValueError: If conversion fails
    """
    try:
        return target_type(value)
    except (TypeError, ValueError):
        type_name = target_type.__name__
        if target_type is float:
            type_name = "a number"
        elif target_type is int:
            type_name = "an integer"
        raise ValueError(f"Invalid '{field_name}' value {value!r}; expected {type_name}") from None


def _get_nested_value(config: dict[str, Any], key_path: str, default: Any) -> Any:
    """Get a value from nested dict using dot notation.

    Args:
        config: The configuration dictionary
        key_path: Dot-separated path (e.g., 'tui.interval')
        default: Default value if path doesn't exist

    Returns:
        Value at the path or default
    """
    parts = key_path.split(".")
    current = config

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]

    return current


def _warn_unknown_keys(user_config: dict[str, Any], section: str, valid_keys: set[str], config_path: Path) -> None:
    """Warn about unknown keys in a TOML section.

    Args:
        user_config: User configuration dictionary
        section: Section name (e.g., 'tui')
        valid_keys: Set of valid key names for this section
        config_path: Path to config file for error messages
    """
    if section not in user_config:
        return

    section_data = user_config[section]
    if not isinstance(section_data, dict):
        return

    for key in section_data:
        if key not in valid_keys:
            logger.warning(
                f"Unknown key '{key}' in [{section}] section of {config_path} - ignoring "
                f"(valid keys: {', '.join(sorted(valid_keys))})"
            )


def _load_toml_file(config_path: Path) -> dict[str, Any] | None:
    """Load and parse TOML file, returning None on any error.

    Args:
        config_path: Path to TOML file

    Returns:
        Parsed TOML dict or None on error
    """
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        logger.warning(f"Failed to parse TOML config from {config_path}: {e}")
        return None
    except OSError as e:
        logger.warning(f"Failed to read config file {config_path}: {e}")
        return None


def _validate_config_structure(user_config: dict[str, Any], config_path: Path) -> None:
    """Validate TOML structure and warn about unknown sections/keys.

    Args:
        user_config: Loaded TOML configuration
        config_path: Path to config file for error messages
    """
    # Validate sections and warn about unknown keys
    _warn_unknown_keys(user_config, "tui", {"interval", "stats_limit", "chart_limit"}, config_path)
    _warn_unknown_keys(user_config, "database", {"path"}, config_path)
    _warn_unknown_keys(user_config, "cli", {"default_history_limit", "default_export_limit"}, config_path)
    _warn_unknown_keys(user_config, "logging", {"level"}, config_path)

    # Warn about unknown sections
    valid_sections = {"tui", "database", "cli", "logging"}
    for section in user_config:
        if section not in valid_sections:
            logger.warning(f"Unknown config section [{section}] in {config_path} - ignoring")

    # Check section types
    for section in user_config:
        if section in valid_sections and not isinstance(user_config[section], dict):
            logger.warning(
                f"Config section [{section}] in {config_path} must be a table, "
                f"but got {type(user_config[section]).__name__} - ignoring section"
            )


def load_config() -> PowerMonitorConfig:
    """Load configuration from TOML file or use defaults.

    Priority: Config file > Defaults
    (CLI arguments will override in cli.py)

    Uses field-level fallback: if a single field is invalid, only that field
    falls back to default (other valid fields are preserved).

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

    # If config file doesn't exist, return defaults
    if not config_path.exists():
        return default_config

    # Load TOML file
    user_config = _load_toml_file(config_path)
    if user_config is None:
        logger.warning("Using default configuration")
        return default_config

    # Validate structure and warn about issues
    _validate_config_structure(user_config, config_path)

    # Extract values with field-level fallback to defaults
    # If a field conversion fails, we use the default for that field only
    def safe_convert(key_path: str, target_type: type, default: Any) -> Any:
        """Get and convert a config value, falling back to default on error."""
        raw_value = _get_nested_value(user_config, key_path, default)
        if raw_value is default:
            return default
        try:
            return _convert_to_type(raw_value, target_type, key_path)
        except ValueError as e:
            logger.warning(f"{e} - using default value {default!r}")
            return default

    collection_interval = safe_convert("tui.interval", float, default_config.collection_interval)
    stats_history_limit = safe_convert("tui.stats_limit", int, default_config.stats_history_limit)
    chart_history_limit = safe_convert("tui.chart_limit", int, default_config.chart_history_limit)
    default_history_limit = safe_convert("cli.default_history_limit", int, default_config.default_history_limit)
    default_export_limit = safe_convert("cli.default_export_limit", int, default_config.default_export_limit)

    # Database path (ensure it's a string or Path; expanduser happens in __post_init__)
    database_path_raw = _get_nested_value(user_config, "database.path", default_config.database_path)
    if not isinstance(database_path_raw, (str, Path)):
        logger.warning(
            f"Invalid 'database.path' value {database_path_raw!r}; expected a string or Path - "
            f"using default value {default_config.database_path!r}"
        )
        database_path = default_config.database_path
    else:
        database_path = database_path_raw

    # Log level (ensure it's a string, validation happens in __post_init__)
    log_level_raw = _get_nested_value(user_config, "logging.level", default_config.log_level)
    if not isinstance(log_level_raw, str):
        logger.warning(
            f"Invalid 'logging.level' value {log_level_raw!r}; expected a string - "
            f"using default value {default_config.log_level!r}"
        )
        log_level = default_config.log_level
    else:
        log_level = log_level_raw

    # Create PowerMonitorConfig instance (validation happens in __post_init__)
    try:
        return PowerMonitorConfig(
            collection_interval=collection_interval,
            stats_history_limit=stats_history_limit,
            chart_history_limit=chart_history_limit,
            database_path=database_path,
            default_history_limit=default_history_limit,
            default_export_limit=default_export_limit,
            log_level=log_level,
        )
    except ValueError as e:
        # This should rarely happen now (only if __post_init__ validation fails)
        logger.error(f"Invalid configuration values: {e}")
        logger.warning("Falling back to safe default configuration")
        return PowerMonitorConfig()  # Use all defaults

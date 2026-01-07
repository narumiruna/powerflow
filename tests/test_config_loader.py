"""Tests for config_loader module helper functions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger

from powermonitor.config_loader import _convert_to_type
from powermonitor.config_loader import _get_nested_value
from powermonitor.config_loader import _load_toml_file
from powermonitor.config_loader import _validate_config_structure
from powermonitor.config_loader import _warn_unknown_keys
from powermonitor.config_loader import load_config


class TestConvertToType:
    """Tests for _convert_to_type helper function."""

    def test_convert_to_int_success(self):
        """Test successful integer conversion."""
        result = _convert_to_type("42", int, "test.field")
        assert result == 42
        assert isinstance(result, int)

    def test_convert_to_float_success(self):
        """Test successful float conversion."""
        result = _convert_to_type("3.14", float, "test.field")
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_to_str_success(self):
        """Test successful string conversion."""
        result = _convert_to_type(123, str, "test.field")
        assert result == "123"
        assert isinstance(result, str)

    def test_convert_to_int_from_float(self):
        """Test converting float to int."""
        result = _convert_to_type(3.14, int, "test.field")
        assert result == 3
        assert isinstance(result, int)

    def test_convert_to_int_invalid_string(self):
        """Test that invalid string raises ValueError with 'an integer'."""
        with pytest.raises(ValueError, match="Invalid 'test.field' value 'not_a_number'; expected an integer"):
            _convert_to_type("not_a_number", int, "test.field")

    def test_convert_to_float_invalid_string(self):
        """Test that invalid string raises ValueError with 'a number'."""
        with pytest.raises(ValueError, match="Invalid 'test.field' value 'invalid'; expected a number"):
            _convert_to_type("invalid", float, "test.field")

    def test_convert_type_error(self):
        """Test that TypeError is converted to ValueError."""
        with pytest.raises(ValueError, match="Invalid 'test.field'"):
            _convert_to_type(None, int, "test.field")

    def test_error_message_includes_field_name(self):
        """Test that error message includes the field name."""
        with pytest.raises(ValueError, match="'tui.interval'"):
            _convert_to_type("bad", int, "tui.interval")


class TestGetNestedValue:
    """Tests for _get_nested_value helper function."""

    def test_get_top_level_value(self):
        """Test getting a top-level value."""
        config = {"key": "value"}
        result = _get_nested_value(config, "key", "default")
        assert result == "value"

    def test_get_nested_value_two_levels(self):
        """Test getting a nested value (two levels)."""
        config = {"section": {"key": "value"}}
        result = _get_nested_value(config, "section.key", "default")
        assert result == "value"

    def test_get_nested_value_three_levels(self):
        """Test getting a deeply nested value (three levels)."""
        config = {"level1": {"level2": {"level3": "value"}}}
        result = _get_nested_value(config, "level1.level2.level3", "default")
        assert result == "value"

    def test_get_missing_key_returns_default(self):
        """Test that missing key returns default."""
        config = {"key": "value"}
        result = _get_nested_value(config, "missing", "default")
        assert result == "default"

    def test_get_missing_nested_key_returns_default(self):
        """Test that missing nested key returns default."""
        config = {"section": {"key": "value"}}
        result = _get_nested_value(config, "section.missing", "default")
        assert result == "default"

    def test_get_missing_section_returns_default(self):
        """Test that missing section returns default."""
        config = {"section": {"key": "value"}}
        result = _get_nested_value(config, "missing.key", "default")
        assert result == "default"

    def test_get_non_dict_section_returns_default(self):
        """Test that non-dict intermediate value returns default."""
        config = {"section": "not_a_dict"}
        result = _get_nested_value(config, "section.key", "default")
        assert result == "default"

    def test_get_empty_config_returns_default(self):
        """Test that empty config returns default."""
        config = {}
        result = _get_nested_value(config, "any.key", "default")
        assert result == "default"


class TestLoadTomlFile:
    """Tests for _load_toml_file helper function."""

    def test_load_valid_toml_file(self):
        """Test loading a valid TOML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[section]\nkey = 'value'\n")
            temp_path = Path(f.name)

        try:
            result = _load_toml_file(temp_path)
            assert result is not None
            assert result == {"section": {"key": "value"}}
        finally:
            temp_path.unlink()

    def test_load_invalid_toml_file(self):
        """Test that invalid TOML returns None and logs warning."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("invalid toml [[[\n")
            temp_path = Path(f.name)

        try:
            result = _load_toml_file(temp_path)
            assert result is None
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test that nonexistent file returns None and logs warning."""
        temp_path = Path("/tmp/nonexistent_powermonitor_test_file.toml")
        result = _load_toml_file(temp_path)
        assert result is None

    def test_load_file_with_unicode(self):
        """Test loading TOML file with unicode characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False, encoding="utf-8") as f:
            f.write('[section]\nkey = "日本語テスト"\n')
            temp_path = Path(f.name)

        try:
            result = _load_toml_file(temp_path)
            assert result is not None
            assert result["section"]["key"] == "日本語テスト"
        finally:
            temp_path.unlink()


class TestWarnUnknownKeys:
    """Tests for _warn_unknown_keys helper function."""

    def test_warn_unknown_key_in_section(self):
        """Test that unknown key triggers warning."""
        user_config = {"tui": {"interval": 1.0, "unknown_key": "value"}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _warn_unknown_keys(user_config, "tui", {"interval", "stats_limit"}, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key 'unknown_key'" in log_text
        assert "[tui]" in log_text
        assert "interval, stats_limit" in log_text

    def test_no_warning_for_valid_keys(self):
        """Test that valid keys don't trigger warnings."""
        user_config = {"tui": {"interval": 1.0, "stats_limit": 100}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _warn_unknown_keys(user_config, "tui", {"interval", "stats_limit", "chart_limit"}, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key" not in log_text

    def test_no_warning_for_missing_section(self):
        """Test that missing section doesn't trigger warnings."""
        user_config = {"other": {"key": "value"}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _warn_unknown_keys(user_config, "tui", {"interval"}, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key" not in log_text

    def test_no_warning_for_non_dict_section(self):
        """Test that non-dict section doesn't trigger warnings."""
        user_config = {"tui": "not_a_dict"}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _warn_unknown_keys(user_config, "tui", {"interval"}, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key" not in log_text

    def test_warn_multiple_unknown_keys(self):
        """Test that multiple unknown keys all trigger warnings."""
        user_config = {"tui": {"interval": 1.0, "unknown1": "a", "unknown2": "b"}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _warn_unknown_keys(user_config, "tui", {"interval"}, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key 'unknown1'" in log_text
        assert "Unknown key 'unknown2'" in log_text


class TestValidateConfigStructure:
    """Tests for _validate_config_structure helper function."""

    def test_valid_config_no_warnings(self):
        """Test that valid config structure doesn't trigger warnings."""
        user_config = {
            "tui": {"interval": 1.0, "stats_limit": 100, "chart_limit": 60},
            "database": {"path": "~/test.db"},
            "cli": {"default_history_limit": 20, "default_export_limit": 1000},
            "logging": {"level": "INFO"},
        }
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _validate_config_structure(user_config, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown" not in log_text
        assert "ignoring" not in log_text

    def test_unknown_section_warning(self):
        """Test that unknown section triggers warning."""
        user_config = {"unknown_section": {"key": "value"}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _validate_config_structure(user_config, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown config section [unknown_section]" in log_text

    def test_non_dict_section_warning(self):
        """Test that non-dict section triggers warning."""
        user_config = {"tui": "not_a_dict"}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _validate_config_structure(user_config, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "[tui]" in log_text
        assert "must be a table" in log_text
        assert "str" in log_text

    def test_unknown_key_in_valid_section_warning(self):
        """Test that unknown key in valid section triggers warning."""
        user_config = {"tui": {"interval": 1.0, "typo_key": "value"}}
        config_path = Path("/test/config.toml")

        messages = []
        handler_id = logger.add(messages.append, format="{message}")
        try:
            _validate_config_structure(user_config, config_path)
        finally:
            logger.remove(handler_id)

        log_text = "\n".join(messages)
        assert "Unknown key 'typo_key'" in log_text
        assert "[tui]" in log_text


class TestLoadConfig:
    """Integration tests for load_config function."""

    def test_load_config_no_file_returns_defaults(self):
        """Test that load_config returns defaults when file doesn't exist."""
        with patch("powermonitor.config_loader.get_config_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/config.toml")
            config = load_config()

            assert config.collection_interval == 1.0
            assert config.stats_history_limit == 100
            assert config.chart_history_limit == 60

    def test_load_config_with_valid_file(self):
        """Test loading config from valid TOML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[tui]
interval = 2.5
stats_limit = 200
chart_limit = 120

[database]
path = "~/custom.db"

[logging]
level = "DEBUG"
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                assert config.collection_interval == 2.5
                assert config.stats_history_limit == 200
                assert config.chart_history_limit == 120
                assert config.log_level == "DEBUG"
        finally:
            temp_path.unlink()

    def test_load_config_field_level_fallback(self):
        """Test that invalid field falls back to default while preserving valid fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[tui]
interval = "invalid"
stats_limit = 200
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                # Invalid interval should use default
                assert config.collection_interval == 1.0
                # Valid stats_limit should be preserved
                assert config.stats_history_limit == 200
        finally:
            temp_path.unlink()

    def test_load_config_invalid_database_path_type(self):
        """Test that invalid database_path type falls back to default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[database]
path = 12345
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                # Should use default path
                assert "powermonitor.db" in str(config.database_path)
        finally:
            temp_path.unlink()

    def test_load_config_invalid_log_level_type(self):
        """Test that invalid log_level type falls back to default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[logging]
level = 123
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                # Should use default log level
                assert config.log_level == "INFO"
        finally:
            temp_path.unlink()

    def test_load_config_lowercase_log_level_normalized(self):
        """Test that lowercase log level is normalized to uppercase."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[logging]
level = "debug"
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                assert config.log_level == "DEBUG"
        finally:
            temp_path.unlink()

    def test_load_config_path_tilde_expansion(self):
        """Test that tilde in database path is expanded."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[database]
path = "~/test.db"
""")
            temp_path = Path(f.name)

        try:
            with patch("powermonitor.config_loader.get_config_path") as mock_path:
                mock_path.return_value = temp_path
                config = load_config()

                # Tilde should be expanded
                assert "~" not in str(config.database_path)
                assert str(config.database_path).startswith(str(Path.home()))
        finally:
            temp_path.unlink()

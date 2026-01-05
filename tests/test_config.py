"""Tests for PowerMonitorConfig."""

import warnings

import pytest

from powermonitor.config import PowerMonitorConfig


def test_config_default_values():
    """Test PowerMonitorConfig with default values."""
    config = PowerMonitorConfig()

    assert config.collection_interval == 1.0
    assert config.stats_history_limit == 100
    assert config.chart_history_limit == 60


def test_config_custom_values():
    """Test PowerMonitorConfig with custom values."""
    config = PowerMonitorConfig(
        collection_interval=2.5,
        stats_history_limit=200,
        chart_history_limit=120,
    )

    assert config.collection_interval == 2.5
    assert config.stats_history_limit == 200
    assert config.chart_history_limit == 120


def test_config_negative_collection_interval():
    """Test that negative collection_interval raises ValueError."""
    with pytest.raises(ValueError, match="collection_interval must be positive"):
        PowerMonitorConfig(collection_interval=-1.0)


def test_config_zero_collection_interval():
    """Test that zero collection_interval raises ValueError."""
    with pytest.raises(ValueError, match="collection_interval must be positive"):
        PowerMonitorConfig(collection_interval=0.0)


def test_config_negative_stats_limit():
    """Test that negative stats_history_limit raises ValueError."""
    with pytest.raises(ValueError, match="stats_history_limit must be positive"):
        PowerMonitorConfig(stats_history_limit=-10)


def test_config_zero_stats_limit():
    """Test that zero stats_history_limit raises ValueError."""
    with pytest.raises(ValueError, match="stats_history_limit must be positive"):
        PowerMonitorConfig(stats_history_limit=0)


def test_config_negative_chart_limit():
    """Test that negative chart_history_limit raises ValueError."""
    with pytest.raises(ValueError, match="chart_history_limit must be positive"):
        PowerMonitorConfig(chart_history_limit=-5)


def test_config_zero_chart_limit():
    """Test that zero chart_history_limit raises ValueError."""
    with pytest.raises(ValueError, match="chart_history_limit must be positive"):
        PowerMonitorConfig(chart_history_limit=0)


def test_config_very_short_interval_warning():
    """Test that very short interval triggers a warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = PowerMonitorConfig(collection_interval=0.05)

        # Check that a warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, UserWarning)
        assert "high CPU usage" in str(w[0].message)
        assert "0.05" in str(w[0].message)

        # Config should still be created successfully
        assert config.collection_interval == 0.05


def test_config_minimum_safe_interval_no_warning():
    """Test that 0.1s interval does not trigger warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = PowerMonitorConfig(collection_interval=0.1)

        # No warning should be issued at exactly 0.1s
        assert len(w) == 0
        assert config.collection_interval == 0.1


def test_config_normal_interval_no_warning():
    """Test that normal intervals don't trigger warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = PowerMonitorConfig(collection_interval=1.0)

        assert len(w) == 0
        assert config.collection_interval == 1.0

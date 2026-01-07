"""Tests for collector factory."""

import sys
from unittest.mock import patch

import pytest

from powermonitor.collector.factory import default_collector


def test_default_collector_on_macos():
    """Test that default_collector returns a collector on macOS."""
    if sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    collector = default_collector()
    assert collector is not None
    assert hasattr(collector, "collect")


def test_default_collector_verbose_mode():
    """Test default_collector with verbose mode enabled."""
    if sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    # Should not raise any errors
    collector = default_collector(verbose=True)
    assert collector is not None


@patch("powermonitor.collector.factory.sys.platform", "linux")
def test_default_collector_non_macos():
    """Test that default_collector raises error on non-macOS platforms."""
    with pytest.raises(RuntimeError, match="only supports macOS"):
        default_collector()

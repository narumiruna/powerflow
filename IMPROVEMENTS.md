# powermonitor - Improvement Roadmap

This document outlines remaining improvements for the powermonitor project.

## Remaining Issues

### 8. Missing TUI Tests (LOW PRIORITY - REQUIRES MACOS)

**Problem**: TUI components (174 lines) have 0% test coverage.

**Limitations**:
- Requires macOS environment to run
- TUI depends on IOKit which only works on macOS
- Cannot test on Linux CI/CD

**Recommendation**: Add Textual unit tests using `textual.pilot` (if developing on macOS):

**File**: `tests/test_tui.py` (new file)
```python
"""Tests for TUI components."""

import pytest
from datetime import datetime, UTC
from textual.pilot import Pilot

from powermonitor.models import PowerReading
from powermonitor.tui.app import PowerMonitorApp
from powermonitor.tui.widgets import LiveDataPanel, StatsPanel


@pytest.fixture
def sample_reading():
    """Sample power reading for testing."""
    return PowerReading(
        timestamp=datetime.now(UTC),
        watts_actual=45.2,
        watts_negotiated=67,
        voltage=20.0,
        amperage=2.26,
        current_capacity=3500,
        max_capacity=4709,
        battery_percent=74,
        is_charging=True,
        external_connected=True,
        charger_name="USB-C Power Adapter",
        charger_manufacturer="Apple Inc.",
    )


def test_live_data_panel_update(sample_reading):
    """Test LiveDataPanel updates with new reading."""
    panel = LiveDataPanel()

    # Initially should show waiting message
    initial = panel._render_reading()
    assert "Waiting for data" in initial

    # After update, should show reading data
    panel.update_reading(sample_reading)
    rendered = panel._render_reading()

    assert "45.2W" in rendered
    assert "74%" in rendered
    assert "Charging" in rendered


def test_stats_panel_empty():
    """Test StatsPanel with empty statistics."""
    panel = StatsPanel()

    empty_stats = {
        "count": 0,
        "avg_watts": 0.0,
        "min_watts": 0.0,
        "max_watts": 0.0,
        "avg_battery": 0.0,
        "earliest": None,
        "latest": None,
    }

    panel.update_stats(empty_stats)
    rendered = panel._render_stats()

    assert "No historical data" in rendered


def test_stats_panel_with_data():
    """Test StatsPanel with statistics data."""
    panel = StatsPanel()

    stats = {
        "count": 100,
        "avg_watts": 42.5,
        "min_watts": 12.3,
        "max_watts": 67.8,
        "avg_battery": 75.5,
        "earliest": "2025-01-05T10:00:00",
        "latest": "2025-01-05T10:10:00",
    }

    panel.update_stats(stats)
    rendered = panel._render_stats()

    assert "100 readings" in rendered
    assert "42.5W" in rendered
    assert "75.5%" in rendered


async def test_app_launches():
    """Test that PowerMonitorApp can launch without errors."""
    app = PowerMonitorApp(collection_interval=1.0)

    async with app.run_test() as pilot:
        # App should have header, footer, and 3 panels
        assert app.query_one("#live-data") is not None
        assert app.query_one("#stats") is not None
        assert app.query_one("#chart") is not None


async def test_app_refresh_action():
    """Test that refresh action works."""
    app = PowerMonitorApp(collection_interval=1.0)

    async with app.run_test() as pilot:
        # Trigger refresh action
        await pilot.press("r")

        # Should show notification
        # (actual verification would require mocking collector)
```

**Benefits**:
- Catches UI regressions early
- Documents expected widget behavior
- Enables refactoring with confidence

---

## Optional Future Enhancements

### Configuration Management Commands

**Recommendation**: Add CLI commands for config file management:

- `powermonitor config show` - Display current effective configuration (CLI args + config file + defaults)
- `powermonitor config init` - Generate default config.toml file with comments
- `powermonitor config validate` - Check config file syntax and values without running app
- `powermonitor config edit` - Open config file in $EDITOR

### Advanced Features

- Dynamic config reload in TUI - Watch config file for changes and reload without restart
- Multiple config profiles - Support different configs for different scenarios (e.g., `--profile work`)
- User guide for data analysis workflows
- Examples of using exported CSV data
- Battery health interpretation guide

---

## Current Test Coverage Status

**Overall**: 21% coverage (very low)

**Good coverage** (>80%):
- ✅ Database: 88%
- ✅ Config: 100%
- ✅ Models: 94%

**Zero coverage** (needs work):
- ❌ TUI: 0% (174 lines) - Requires macOS
- ❌ IOKit: 0% (318 lines) - Requires macOS
- ❌ CLI: 0% (30 lines) - Can test commands
- ❌ Logger: 0% (12 lines) - Easy to test

**Recommended**: Focus on testing new CLI commands as they're added

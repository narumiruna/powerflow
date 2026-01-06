# powermonitor - Improvement Roadmap

This document outlines recommended improvements for the powermonitor project, organized by priority.

## Completed Issues ✅

### Critical Issues (Phase 1)

**1. Database Connection Management** - ✅ Completed (commit `376154f`, 2026-01-06)
- Implemented Option B: Context managers for all database operations
- Added error handling for database writes in TUI app
- All 25 tests pass, 89% database coverage
- Files: `src/powermonitor/database.py`, `src/powermonitor/tui/app.py`

**2. Resource Cleanup in Error Paths** - ✅ Completed (fixed by #1)
- Context managers ensure proper connection cleanup on errors

**3. Missing Error Handling for Database Writes** - ✅ Completed (commit `376154f`)
- TUI now displays warnings on database failures without crashing
- UI continues working even if persistence fails

### Moderate Issues (Phase 2)

**4. Magic Numbers Throughout Codebase** - ✅ Completed (commit `8a89f57`, 2026-01-06)
- Created `PowerMonitorConfig` dataclass with validation
- Replaced hardcoded values: collection_interval, stats_history_limit, chart_history_limit
- Added CLI options: `--interval`, `--stats-limit`, `--chart-limit`
- Implemented `__post_init__` validation with helpful error messages
- Dynamic chart title based on actual reading count
- 11 config tests pass, 100% config coverage
- Files: `src/powermonitor/config.py`, `src/powermonitor/cli.py`, `src/powermonitor/tui/app.py`, `src/powermonitor/tui/widgets.py`

**5. Insufficient Input Validation** - ✅ Completed (fixed by #4)
- PowerMonitorConfig validates all inputs in `__post_init__`
- CLI catches ValueError from config and exits with error message
- Validates: positive values, warns on very short intervals (< 0.1s)
- All validation covered by tests

**7. Singleton Pattern Bug** - ✅ Completed (2026-01-06)
- Replaced global singleton with path-aware caching using `dict[Path, Database]`
- Now correctly handles multiple database paths
- Paths are normalized to absolute paths for consistent caching
- Files: `src/powermonitor/database.py:263-284`

### Minor Issues (Completed)

**11. Redundant Pass Statements** - ✅ Completed (2026-01-06)
- Removed unnecessary `pass` statements from exception classes with docstrings
- Cleaned up: `PowerCollectorError`, `CommandFailedError`, `ParseError`, `IOKitError`
- Files: `src/powermonitor/models.py:59-80`

**12. Potential Data Loss on Quit** - ✅ Completed (2026-01-06)
- Improved `action_quit()` with graceful shutdown sequence
- Shows "Shutting down..." notification
- Cancels collection task and waits for completion
- Gives pending database writes time to complete (100ms sleep)
- Files: `src/powermonitor/tui/app.py:206-226`

**6. Limited Logging Configuration** - ✅ Completed (commit `94815a6`, 2026-01-06)
- Added `setup_logger()` function with configurable log levels
- CLI has `--debug` option to enable DEBUG level logging
- Default level is INFO for normal operation
- Uses loguru with custom formatting
- Files: `src/powermonitor/logger.py`, `src/powermonitor/cli.py:56-60`

### Phase 3 Completed

**9. Inconsistent Error Handling in IOKit** - ✅ Completed (2026-01-06)
- Added kern_return_t error code translation with `_get_kern_return_name()`
- All IOKit function calls now have proper return value checking
- Added return value checks for IOServiceClose and IOObjectRelease
- Improved error messages with human-readable error names
- Added comprehensive debug logging for all IOKit operations
- close() method now always attempts cleanup of both resources
- Added input validation for SMC keys (must be 4 characters)
- Files: `src/powermonitor/collector/iokit/connection.py:28-275`

---

## Remaining Issues (Reprioritized)

### Critical Missing Features

These are essential features that users need but are currently missing:

### 13. Data Export Command (HIGH PRIORITY)

**Problem**: Users cannot export their collected power data for external analysis.

**Current State**:
- Data is collected and stored in SQLite
- No way to access it except through TUI
- Users want CSV/JSON exports for Excel, Python, etc.

**Recommendation**: Add export subcommand

```bash
# Export to CSV
powermonitor export data.csv --limit 1000

# Export to JSON
powermonitor export data.json --from "2026-01-01" --to "2026-01-06"

# Export all data
powermonitor export backup.csv
```

**Implementation**:
- Add `export` command to CLI with typer
- Reuse `Database.query_history()` method
- Support CSV and JSON formats (detect from extension)
- Add `--limit`, `--from`, `--to` filters

**Files**: `src/powermonitor/cli.py`, `src/powermonitor/database.py`

---

### 14. Data Cleanup Command (HIGH PRIORITY)

**Problem**: Database grows indefinitely, no automated cleanup mechanism.

**Current State**:
- Every reading is saved permanently
- Database can grow to hundreds of MB over time
- Users have to manually delete the database file

**Recommendation**: Add cleanup/stats commands

```bash
# Delete readings older than 30 days
powermonitor cleanup --days 30

# Show database statistics
powermonitor stats
# Output:
#   Total readings: 12,450
#   Earliest: 2025-12-01 10:30:00
#   Latest: 2026-01-06 15:22:00
#   Database size: 2.4 MB

# Clear all history (with confirmation)
powermonitor cleanup --all
```

**Implementation**:
- Add `cleanup` and `stats` commands
- Add `Database.cleanup_old_data(days)` method
- Add `Database.get_statistics_full()` method
- Require confirmation for destructive operations

**Files**: `src/powermonitor/cli.py`, `src/powermonitor/database.py`

---

### 15. History Query Command (HIGH PRIORITY)

**Problem**: Cannot view historical data without launching TUI.

**Current State**:
- Must launch full TUI to see any data
- No quick way to check recent readings

**Recommendation**: Add history query command

```bash
# Show last 20 readings
powermonitor history --limit 20

# Show readings from specific time range
powermonitor history --from "2026-01-06 10:00" --to "2026-01-06 12:00"

# Show only charging sessions
powermonitor history --charging-only
```

**Implementation**:
- Add `history` command to CLI
- Format output as table using rich
- Add filters: limit, from, to, charging-only
- Show key metrics: time, watts, battery %, status

**Files**: `src/powermonitor/cli.py`

---

### 16. Battery Health Tracking Command (MEDIUM PRIORITY)

**Problem**: No way to track battery degradation over time.

**Current State**:
- `max_capacity` field is collected but not analyzed
- Users want to know if battery is degrading

**Recommendation**: Add health tracking command

```bash
# Show battery health trend (last 30 days)
powermonitor health --days 30
# Output:
#   First avg capacity: 4,709 mAh (2025-12-06)
#   Last avg capacity: 4,650 mAh (2026-01-06)
#   Change: -59 mAh (-1.25%)
#   Status: Degrading (normal wear)
```

**Implementation**:
- Add `health` command to CLI
- Add `Database.get_battery_health_trend(days)` method
- Calculate daily average max_capacity
- Show trend (stable/degrading) and percentage change

**Files**: `src/powermonitor/cli.py`, `src/powermonitor/database.py`

---

## Lower Priority Issues

These are less urgent but still valuable:

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

### 10. Configuration File Support (LOW PRIORITY - MAYBE NOT NEEDED)

**Problem**: Currently requires CLI arguments for configuration.

**Current State**:
- CLI has `--interval`, `--stats-limit`, `--chart-limit`, `--debug` options
- Options work well for most use cases
- Environment variable `POWERMONITOR_DB_PATH` for database location

**Consideration**: Config file might be over-engineering
- Most users run with defaults
- CLI options are sufficient for customization
- Adds complexity (file parsing, precedence rules, etc.)
- Consider only if users request it

**Recommendation** (if needed): Add TOML configuration file support.

**File**: `~/.powermonitor/config.toml` (user config)
```toml
[database]
path = "~/.powermonitor/powermonitor.db"

[collection]
interval = 1.0  # seconds
auto_start = true

[display]
chart_history = 60
stats_limit = 100
theme = "dark"

[logging]
level = "INFO"
file = "~/.powermonitor/powermonitor.log"
```

**Implementation**: Add config module

**File**: `src/powermonitor/config.py` (new file)
```python
"""Configuration management for powermonitor."""

from pathlib import Path
from typing import Any
import tomllib

DEFAULT_CONFIG = {
    "database": {
        "path": "~/.powermonitor/powermonitor.db",
    },
    "collection": {
        "interval": 1.0,
    },
    "display": {
        "chart_history": 60,
        "stats_limit": 100,
    },
    "logging": {
        "level": "INFO",
    },
}


def get_config_path() -> Path:
    """Get path to user configuration file."""
    return Path.home() / ".powermonitor" / "config.toml"


def load_config() -> dict[str, Any]:
    """Load configuration from file or use defaults.

    Returns:
        Configuration dictionary
    """
    config_path = get_config_path()

    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)

        # Merge with defaults
        config = DEFAULT_CONFIG.copy()
        for section, values in user_config.items():
            if section in config:
                config[section].update(values)
            else:
                config[section] = values

        return config

    except Exception as e:
        # Log warning and use defaults
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return DEFAULT_CONFIG.copy()


def save_default_config() -> None:
    """Save default configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to TOML format
    lines = [
        "# powermonitor configuration file",
        "",
        "[database]",
        f'path = "{DEFAULT_CONFIG["database"]["path"]}"',
        "",
        "[collection]",
        f'interval = {DEFAULT_CONFIG["collection"]["interval"]}',
        "",
        "[display]",
        f'chart_history = {DEFAULT_CONFIG["display"]["chart_history"]}',
        f'stats_limit = {DEFAULT_CONFIG["display"]["stats_limit"]}',
        "",
        "[logging]",
        f'level = "{DEFAULT_CONFIG["logging"]["level"]}"',
    ]

    config_path.write_text("\n".join(lines))
```

**Update CLI**:
```python
from .config import load_config

@app.command()
def main(interval: float | None = None, ...) -> None:
    """Main entry point."""
    config = load_config()

    # CLI args override config file
    collection_interval = interval or config["collection"]["interval"]

    PowerMonitorApp(collection_interval=collection_interval).run()
```

---

## Implementation Priority

### Phase 1 (Critical - Do First) ✅ COMPLETED
1. ✅ Fix database connection management (#1)
2. ✅ Add resource cleanup (#2)
3. ✅ Add database write error handling (#3)

### Phase 2 (Important - Do Soon) ✅ COMPLETED
4. ✅ Replace magic numbers with constants (#4)
5. ✅ Add input validation (#5)
6. ✅ Configure logging properly (#6)
7. ✅ Fix singleton pattern bug (#7)

### Phase 3 (Code Quality) ✅ COMPLETED
9. ✅ Improve IOKit error handling (#9)
11. ✅ Remove redundant pass statements (#11)
12. ✅ Improve shutdown sequence (#12)

### Phase 4 (Essential Features - DO NEXT) 🎯
**These are the most valuable features to implement:**
13. **Data export command** (#13) - 30 min - Users need this
14. **Data cleanup command** (#14) - 30 min - Database grows indefinitely
15. **History query command** (#15) - 20 min - Quick data viewing
16. **Battery health tracking** (#16) - 45 min - Useful insights

### Phase 5 (Lower Priority - Optional)
8. Add TUI tests (#8) - Requires macOS, 2-3 hours
10. Add configuration file support (#10) - Probably not needed

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

---

## Documentation Updates Needed

When implementing Phase 4 features:

1. Update README.md with new CLI commands
   - Add `powermonitor export` usage examples
   - Add `powermonitor cleanup` usage examples
   - Add `powermonitor history` usage examples
   - Add `powermonitor health` usage examples

2. Update CLAUDE.md with:
   - New CLI command descriptions
   - Database cleanup strategies
   - Export format specifications

3. Consider adding:
   - User guide for data analysis workflows
   - Examples of using exported CSV data
   - Battery health interpretation guide

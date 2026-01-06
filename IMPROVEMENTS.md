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

### Phase 4 Completed ✅

**13. Data Export Command** - ✅ Completed (2026-01-06)
- Added `export` command to CLI with typer
- Supports CSV and JSON formats
- Auto-detects format from file extension (.csv, .json)
- Manual format override with `--format` option
- `--limit` parameter to restrict number of readings
- Files: `src/powermonitor/cli.py:99-232`

**14. Data Cleanup Command** - ✅ Completed (2026-01-06)
- Added `cleanup` command with `--days` and `--all` options
- Requires confirmation for `--all` to prevent accidental data loss
- Uses SQL DELETE with timestamp filtering for old data
- Files: `src/powermonitor/cli.py:287-350`

**15. History Query Command** - ✅ Completed (2026-01-06)
- Added `history` command with rich table output
- Shows time, power, battery %, voltage, current, status
- Status icons: ⚡ Charging / 🔌 AC Power / 🔋 Battery
- `--limit` option to control number of readings (default: 20)
- Files: `src/powermonitor/cli.py:353-412`

**16. Battery Health Tracking Command** - ✅ Completed (2026-01-06)
- Added `health` command to analyze battery degradation
- Calculates daily average max_capacity over N days
- Shows change in mAh and percentage
- Status indicators: Stable / Degrading (normal) / Degrading (significant)
- Daily trend table for last 7 days
- Files: `src/powermonitor/cli.py:403-477`

**Additional Improvements** - ✅ Completed (2026-01-06)
- Added `stats` command to show database statistics
- All commands use rich formatting for professional output
- Comprehensive error handling for all operations
- All type checks pass (ty)
- All linting passes (ruff)

---

## Remaining Issues

### Lower Priority Issues

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

### 10. Configuration File Support - ✅ COMPLETED (2026-01-06)

**Status**: Implemented TOML configuration file support at `~/.powermonitor/config.toml`

**Implementation**:
- Created `config_loader.py` module with `load_config()` function
- Extended `PowerMonitorConfig` dataclass with new fields:
  - `database_path: Path` - Database file location
  - `default_history_limit: int = 20` - For history command
  - `default_export_limit: int = 1000` - For export command
  - `log_level: str = "INFO"` - Logging level
- Configuration priority: **CLI arguments > Config file > Defaults**
- Removed `POWERMONITOR_DB_PATH` environment variable support
- All CLI commands now use config for database path and defaults
- TUI uses config for database path and collection settings

**Breaking Changes**:
- `POWERMONITOR_DB_PATH` environment variable no longer supported
- Users should use `[database]` section in config file instead

**Config File Format** (`~/.powermonitor/config.toml`):
```toml
# powermonitor configuration file

[tui]
interval = 1.0           # Data collection interval in seconds
stats_limit = 100        # Number of readings for statistics
chart_limit = 60         # Number of readings to display in chart

[database]
path = "~/.powermonitor/powermonitor.db"  # Database file location

[cli]
default_history_limit = 20           # Default limit for history command
default_export_limit = 1000          # Default limit for export command

[logging]
level = "INFO"           # Logging level: DEBUG, INFO, WARNING, ERROR
```

**Future Enhancements** (Not yet implemented):
- `powermonitor config show` - Display current effective configuration (CLI args + config file + defaults)
- `powermonitor config init` - Generate default config.toml file with comments
- `powermonitor config validate` - Check config file syntax and values without running app
- `powermonitor config edit` - Open config file in $EDITOR
- Dynamic config reload in TUI - Watch config file for changes and reload without restart
- Multiple config profiles - Support different configs for different scenarios (e.g., `--profile work`)

**Files**:
- `src/powermonitor/config.py` - Extended PowerMonitorConfig dataclass
- `src/powermonitor/config_loader.py` - TOML loading and parsing
- `src/powermonitor/cli.py` - All commands updated to use config
- `src/powermonitor/tui/app.py` - Uses config.database_path
- `src/powermonitor/database.py` - Simplified, removed environment variable

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

### Phase 4 (Essential Features) ✅ COMPLETED
13. ✅ Data export command (#13) - Users need this
14. ✅ Data cleanup command (#14) - Database grows indefinitely
15. ✅ History query command (#15) - Quick data viewing
16. ✅ Battery health tracking (#16) - Useful insights
17. ✅ Database statistics command (bonus)

### Phase 5 (Lower Priority - Optional) ✅ PARTIALLY COMPLETED
8. Add TUI tests (#8) - Requires macOS, 2-3 hours
10. ✅ Add configuration file support (#10) - Completed 2026-01-06

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

## Documentation Updates ✅ COMPLETED

Phase 4 documentation has been updated:

1. ✅ Updated README.md with new CLI commands
   - Added `powermonitor export` usage examples
   - Added `powermonitor cleanup` usage examples
   - Added `powermonitor history` usage examples
   - Added `powermonitor health` usage examples
   - Added `powermonitor stats` command
   - Added TUI configuration options

2. ✅ Updated CLAUDE.md with:
   - New CLI command descriptions
   - Database cleanup strategies
   - Export format specifications

3. Future enhancements (optional):
   - User guide for data analysis workflows
   - Examples of using exported CSV data
   - Battery health interpretation guide

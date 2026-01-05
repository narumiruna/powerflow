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

---

## Moderate Issues

### 4. Magic Numbers Throughout Codebase

**Files**: Multiple

**Problem**: Hardcoded limits and intervals scattered throughout code make configuration difficult.

**Locations**:
- `src/powermonitor/tui/app.py:72` - `collection_interval = 1.0`
- `src/powermonitor/tui/app.py:150` - `limit=100` (statistics)
- `src/powermonitor/tui/app.py:155` - `limit=60` (chart history)
- `src/powermonitor/tui/widgets.py:171` - Chart title references hardcoded "60"

**Recommendation**: Define as class constants with descriptive names:

```python
class PowerMonitorApp(App):
    """powermonitor TUI application."""

    # Configuration constants
    DEFAULT_COLLECTION_INTERVAL = 1.0  # seconds
    STATS_HISTORY_LIMIT = 100         # number of readings for statistics
    CHART_HISTORY_LIMIT = 60          # number of readings to display in chart

    # ... existing code ...

    def __init__(self, collection_interval: float = DEFAULT_COLLECTION_INTERVAL, **kwargs):
        super().__init__(**kwargs)
        self.collection_interval = collection_interval
        # ...

    def _update_all_widgets(self, reading: PowerReading) -> None:
        stats = self.database.get_statistics(limit=self.STATS_HISTORY_LIMIT)
        history = self.database.query_history(limit=self.CHART_HISTORY_LIMIT)
        # ...
```

---

### 5. Insufficient Input Validation

**File**: `src/powermonitor/cli.py:16-24`

**Problem**: CLI accepts invalid interval values (negative, zero, extremely small).

**Current Code**:
```python
def main(interval: Annotated[float, ...] = 1.0) -> None:
    """Main entry point for powermonitor CLI."""
    # No validation of interval value
    PowerMonitorApp(collection_interval=interval).run()
```

**Recommendation**: Add input validation:

```python
def main(
    interval: Annotated[
        float,
        typer.Option(
            "-i",
            "--interval",
            help="Data collection interval in seconds",
            show_default=True,
        ),
    ] = 1.0,
) -> None:
    """Main entry point for powermonitor CLI."""
    # Validate interval
    if interval <= 0:
        logger.error("Collection interval must be positive (got {interval})")
        raise typer.Exit(code=1)

    if interval < 0.1:
        logger.warning(
            f"Very short interval ({interval}s) may cause high CPU usage. "
            "Recommended minimum: 0.5s"
        )

    # Check platform
    if sys.platform != "darwin":
        logger.error("powermonitor only supports macOS")
        raise typer.Exit(code=1)

    # Launch TUI
    try:
        logger.info("Starting powermonitor TUI...")
        PowerMonitorApp(collection_interval=interval).run()
    except KeyboardInterrupt:
        logger.info("Exiting powermonitor...")
        raise typer.Exit(code=0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise typer.Exit(code=1)
```

---

### 6. Limited Logging Configuration

**File**: `src/powermonitor/cli.py`

**Problem**: loguru is imported but never configured. Default settings may be too verbose or not verbose enough for different use cases.

**Recommendation**: Add logging configuration with verbosity levels:

```python
import sys
from loguru import logger
import typer

def configure_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure loguru logging based on verbosity level.

    Args:
        verbose: Enable INFO level logging
        debug: Enable DEBUG level logging
    """
    logger.remove()  # Remove default handler

    if debug:
        level = "DEBUG"
    elif verbose:
        level = "INFO"
    else:
        level = "WARNING"

    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )

@app.command()
def main(
    interval: Annotated[float, ...] = 1.0,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose logging")
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug logging")
    ] = False,
) -> None:
    """Main entry point for powermonitor CLI."""
    configure_logging(verbose=verbose, debug=debug)

    # ... rest of main ...
```

---

### 7. Singleton Pattern Bug

**File**: `src/powermonitor/database.py:270-285`

**Problem**: Global singleton `_default_db` doesn't respect different `db_path` arguments after first call.

**Current Code**:
```python
_default_db: Database | None = None

def get_database(db_path: Path | str = DB_PATH) -> Database:
    global _default_db
    if _default_db is None:
        _default_db = Database(db_path)
    return _default_db  # Always returns first instance, ignoring new db_path
```

**Bug Example**:
```python
# First call creates database at path1
db1 = get_database("/path1/db.sqlite")

# Second call IGNORES path2 and returns db1!
db2 = get_database("/path2/db.sqlite")

assert db1 is db2  # True (bug!)
assert db2.db_path == Path("/path1/db.sqlite")  # True (unexpected!)
```

**Recommendation**: Use path-aware caching:

```python
_db_instances: dict[Path, Database] = {}

def get_database(db_path: Path | str = DB_PATH) -> Database:
    """Get database instance for the specified path.

    Uses caching to return the same instance for the same path.

    Args:
        db_path: Path to database file

    Returns:
        Database instance for the specified path
    """
    path = Path(db_path).resolve()  # Resolve to absolute path

    if path not in _db_instances:
        _db_instances[path] = Database(path)

    return _db_instances[path]
```

**Benefits**:
- Correctly handles multiple database paths
- Still provides singleton behavior per path
- Thread-safe caching by path

---

## Minor Issues

### 8. Missing TUI Tests

**Problem**: No tests for TUI components (app.py, widgets.py), making UI regressions hard to detect.

**Recommendation**: Add Textual unit tests using `textual.pilot`:

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

### 9. Inconsistent Error Handling in IOKit

**File**: `src/powermonitor/collector/iokit/connection.py:60-62`

**Problem**: Some IOKit calls check return codes, others don't. Missing NULL check for `IOServiceMatching` result.

**Current Code**:
```python
# Get AppleSMC service
matching = IOServiceMatching(b"AppleSMC\0")
# No NULL check - what if it returns NULL?
kr = IOServiceGetMatchingServices(master_port.value, matching, ctypes.byref(iterator))
```

**Recommendation**: Add NULL/error checks for all IOKit calls:

```python
def _open(self) -> None:
    """Open IOKit connection to AppleSMC."""
    # Get master port
    master_port = ctypes.c_uint32(0)
    kr = IOMasterPort(0, ctypes.byref(master_port))
    if kr != KERN_SUCCESS:
        raise SMCError(f"IOMasterPort failed with error code: {kr}")

    # Find AppleSMC service
    matching = IOServiceMatching(b"AppleSMC\0")
    if not matching:
        raise SMCError("IOServiceMatching returned NULL (out of memory?)")

    # Get matching services
    iterator = ctypes.c_uint32(0)
    kr = IOServiceGetMatchingServices(
        master_port.value,
        matching,
        ctypes.byref(iterator)
    )
    if kr != KERN_SUCCESS:
        raise SMCError(f"IOServiceGetMatchingServices failed: {kr}")

    # ... rest of function ...
```

---

### 10. No Configuration File Support

**Problem**: Only environment variable for DB path. No way to configure collection interval, chart limits, etc., without CLI arguments or code changes.

**Recommendation**: Add TOML configuration file support.

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

### 11. Redundant Pass Statements

**File**: `src/powermonitor/models.py:62, 68, 88`

**Problem**: Exception classes with docstrings don't need `pass` statements.

**Current Code**:
```python
class PowerCollectorError(Exception):
    """Base exception for power collection errors."""
    pass  # Unnecessary - docstring makes class non-empty
```

**Recommendation**: Remove `pass` from all exception classes with docstrings:

```python
class PowerCollectorError(Exception):
    """Base exception for power collection errors."""


class CommandFailedError(PowerCollectorError):
    """ioreg command execution failed."""


class ParseError(PowerCollectorError):
    """Plist/data parsing failed."""
```

---

### 12. Potential Data Loss on Quit

**File**: `src/powermonitor/tui/app.py:188-190`

**Problem**: App exits immediately without ensuring final data is saved or collection task completes gracefully.

**Current Code**:
```python
async def action_quit(self) -> None:
    """Handle quit action (Q or ESC)."""
    self.exit()  # Immediate exit, might lose in-flight data
```

**Recommendation**: Graceful shutdown with data preservation:

```python
async def action_quit(self) -> None:
    """Handle quit action (Q or ESC).

    Ensures background collection task is cancelled cleanly
    and any in-flight data is saved before exiting.
    """
    # Show shutting down notification
    self.notify("Shutting down...", timeout=1)

    # Cancel collection task and wait for completion
    if self._collector_task and not self._collector_task.done():
        self._collector_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._collector_task

    # Give any pending database writes a moment to complete
    # (if using threaded executor for database operations)
    await asyncio.sleep(0.1)

    # Now safe to exit
    self.exit()
```

**Alternative**: Add shutdown hook in `on_unmount`:
```python
async def on_unmount(self) -> None:
    """Clean up when app unmounts.

    This is called automatically on exit and ensures clean shutdown.
    """
    # Cancel collection task
    if self._collector_task and not self._collector_task.done():
        self._collector_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._collector_task

    # Close database connection if we implement persistent connection
    if hasattr(self.database, 'close'):
        self.database.close()
```

---

## Enhancement Ideas

### 13. Add Export Functionality

Allow users to export collected data to CSV or JSON for external analysis.

**File**: `src/powermonitor/database.py`

```python
def export_to_csv(self, output_path: Path | str, limit: int | None = None) -> int:
    """Export power readings to CSV file.

    Args:
        output_path: Path to output CSV file
        limit: Maximum number of readings to export (None = all)

    Returns:
        Number of readings exported
    """
    import csv

    readings = self.query_history(limit=limit or 999999)

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'timestamp', 'watts_actual', 'watts_negotiated',
            'voltage', 'amperage', 'current_capacity', 'max_capacity',
            'battery_percent', 'is_charging', 'external_connected',
            'charger_name', 'charger_manufacturer'
        ])

        # Data
        for r in readings:
            writer.writerow([
                r.timestamp.isoformat(),
                r.watts_actual,
                r.watts_negotiated,
                r.voltage,
                r.amperage,
                r.current_capacity,
                r.max_capacity,
                r.battery_percent,
                r.is_charging,
                r.external_connected,
                r.charger_name or '',
                r.charger_manufacturer or '',
            ])

    return len(readings)
```

### 14. Add Data Retention Policy

Automatically clean up old data to prevent database from growing indefinitely.

**File**: `src/powermonitor/database.py`

```python
def cleanup_old_data(self, days_to_keep: int = 30) -> int:
    """Delete readings older than specified days.

    Args:
        days_to_keep: Number of days of data to retain

    Returns:
        Number of rows deleted
    """
    cutoff = datetime.now(UTC) - timedelta(days=days_to_keep)

    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM power_readings WHERE timestamp < ?",
        (cutoff.isoformat(),)
    )

    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return rows_deleted
```

**Trigger**: Add periodic cleanup in TUI app:

```python
async def _periodic_cleanup(self) -> None:
    """Run periodic database cleanup."""
    while True:
        await asyncio.sleep(3600)  # Every hour

        # Cleanup data older than 30 days
        try:
            deleted = await asyncio.get_event_loop().run_in_executor(
                None,
                self.database.cleanup_old_data,
                30
            )
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old readings")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
```

### 15. Add Battery Health Metrics

Track battery degradation over time by monitoring max capacity changes.

**File**: `src/powermonitor/database.py`

```python
def get_battery_health_trend(self, days: int = 30) -> dict:
    """Calculate battery health trend over time.

    Args:
        days: Number of days to analyze

    Returns:
        Dictionary with health metrics
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            DATE(timestamp) as date,
            AVG(max_capacity) as avg_max_capacity,
            MIN(max_capacity) as min_max_capacity,
            MAX(max_capacity) as max_max_capacity
        FROM power_readings
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    """, (cutoff.isoformat(),))

    results = cursor.fetchall()
    conn.close()

    if not results:
        return {"trend": "unknown", "data": []}

    # Calculate trend
    first_capacity = results[0][1]
    last_capacity = results[-1][1]
    change_percent = ((last_capacity - first_capacity) / first_capacity) * 100

    return {
        "days_analyzed": days,
        "first_avg_capacity": first_capacity,
        "last_avg_capacity": last_capacity,
        "change_percent": change_percent,
        "trend": "degrading" if change_percent < -1 else "stable",
        "daily_data": [
            {
                "date": row[0],
                "avg_capacity": row[1],
                "min_capacity": row[2],
                "max_capacity": row[3],
            }
            for row in results
        ],
    }
```

---

## Implementation Priority

### Phase 1 (Critical - Do First) ✅ COMPLETED
1. ✅ Fix database connection management (#1)
2. ✅ Add resource cleanup (#2)
3. ✅ Add database write error handling (#3)

### Phase 2 (Important - Do Soon)
4. Replace magic numbers with constants (#4)
5. Add input validation (#5)
6. Configure logging properly (#6)
7. Fix singleton pattern bug (#7)

### Phase 3 (Nice to Have - When Time Permits)
8. Add TUI tests (#8)
9. Improve IOKit error handling (#9)
10. Add configuration file support (#10)
11. Remove redundant pass statements (#11)
12. Improve shutdown sequence (#12)

### Phase 4 (Enhancements - Future Features)
13. Add data export functionality
14. Add data retention policy
15. Add battery health tracking

---

## Testing Strategy

After implementing improvements:

1. **Unit Tests**: Ensure all modules have >80% coverage
2. **Integration Tests**: Test end-to-end data flow
3. **Error Injection**: Test error paths (database failures, IOKit errors)
4. **Performance Tests**: Verify no regressions in memory/CPU usage
5. **Manual Tests**: Run TUI for extended periods to check stability

## Documentation Updates

After implementing improvements:

1. Update CLAUDE.md with new configuration options
2. Update README.md with new CLI flags
3. Add troubleshooting section for common issues
4. Document configuration file format
5. Add examples for export/health tracking features

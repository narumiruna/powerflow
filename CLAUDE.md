# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

powermonitor is a macOS power monitoring tool with an auto-updating TUI (Text User Interface) and comprehensive CLI commands. Built with Python 3.13+, it provides real-time battery power monitoring with historical data visualization, data export, and SQLite-based persistence.

**Current Status**: Full-featured CLI tool with:
- Auto-updating TUI with configurable display
- Data export (CSV/JSON)
- Database management (stats, cleanup)
- History viewing
- Battery health tracking

## Essential Commands

### Running powermonitor

```bash
# Launch the auto-updating TUI (default command)
powermonitor

# Customize TUI settings
powermonitor --interval 1.0 --stats-limit 100 --chart-limit 60 --debug

# Or using uv:
uv run powermonitor
```

### Configuration File

powermonitor supports an optional configuration file at `~/.powermonitor/config.toml`:

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

**Configuration Priority**: CLI arguments > Config file > Defaults

If no config file exists, powermonitor uses sensible defaults. CLI arguments always override config file values.

### CLI Commands

powermonitor provides comprehensive data management commands:

```bash
# Export data to CSV or JSON
powermonitor export data.csv --limit 1000
powermonitor export data.json

# View database statistics
powermonitor stats

# View recent readings
powermonitor history --limit 50

# Clean up old data
powermonitor cleanup --days 30
powermonitor cleanup --all  # Requires confirmation

# Analyze battery health
powermonitor health --days 60
```

### Development

```bash
# Install dependencies
uv sync

# Run with verbose collector info (debug mode)
uv run python -c "from powermonitor.collector import default_collector; default_collector(verbose=True).collect()"

# Run tests (when available)
uv run pytest

# Type checking
uv run ty check .

# Linting and formatting
uv run ruff check src/
uv run ruff format src/
```

## Project Structure

```
powermonitor/
├── pyproject.toml              # uv project configuration
├── uv.lock                     # Dependency lock file
├── src/
│   └── powermonitor/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point with multiple commands
│       ├── models.py           # PowerReading dataclass (12 fields)
│       ├── database.py         # SQLite operations
│       ├── config.py           # PowerMonitorConfig dataclass (extended with all settings)
│       ├── config_loader.py    # TOML configuration file loader
│       ├── logger.py           # Logging configuration
│       ├── collector/
│       │   ├── __init__.py
│       │   ├── base.py         # PowerCollector protocol
│       │   ├── ioreg.py        # Subprocess-based collector (fallback)
│       │   ├── factory.py      # default_collector() with auto-fallback
│       │   └── iokit/          # Direct IOKit/SMC access
│       │       ├── __init__.py
│       │       ├── bindings.py # ctypes IOKit framework bindings
│       │       ├── structures.py # SMC data structures
│       │       ├── parser.py   # Binary data parsing (13 SMC types)
│       │       ├── connection.py # SMCConnection class
│       │       └── collector.py # IOKitCollector
│       └── tui/
│           ├── __init__.py
│           ├── app.py          # Textual TUI application
│           └── widgets.py      # LiveDataPanel, StatsPanel, ChartWidget
└── tests/
    └── fixtures/
        └── real_mac.txt        # Sample ioreg output for testing

Database location: ~/.powermonitor/powermonitor.db (auto-created, configurable via config.toml)
```

## Architecture Overview

### TUI Application

powermonitor uses **Textual** for the TUI with a 3-panel auto-updating layout:

1. **LiveDataPanel** (green border): Real-time power metrics
   - Status indicator: ⚡ Charging / 🔌 AC Power / 🔋 On Battery
   - Current power (W), battery %, voltage, amperage
   - Charger information if available
   - Updates every 1 second

2. **StatsPanel** (cyan border): Historical statistics
   - Time range (earliest/latest readings)
   - Average/min/max power (W)
   - Average battery percentage
   - Based on last 100 readings

3. **ChartWidget** (blue border): Power over time visualization
   - Line chart using textual-plotext
   - Shows last 60 readings
   - Two lines: actual power (red) + max negotiated power (blue)

**Key bindings:**
- `q` / `ESC`: Quit application
- `r`: Force refresh data
- `c`: Clear history (with confirmation)

### Data Collection Strategy

powermonitor uses the **Strategy Pattern** via the `PowerCollector` protocol:

```python
class PowerCollector(Protocol):
    def collect(self) -> PowerReading: ...
```

**Available collectors:**

1. **IOKitCollector** (preferred): Direct IOKit/SMC API access via ctypes
   - Reads 7 SMC sensors: PPBR, PDTR, PSTR, PHPC, PDBR, TB0T, CHCC
   - Uses PDTR (Power Delivery/Input Rate) for most accurate watts_actual
   - Falls back to IORegCollector on error
   - Location: `src/powermonitor/collector/iokit/collector.py`

2. **IORegCollector** (fallback): Parses `ioreg -rw0 -c AppleSmartBattery -a` output
   - No special permissions required
   - Uses plistlib to parse XML output
   - Location: `src/powermonitor/collector/ioreg.py`

The `default_collector()` function tries IOKitCollector first, automatically falling back to IORegCollector if SMC sensors are unavailable.

### Data Models

Core data structure is `PowerReading` (defined in `src/powermonitor/models.py`):

```python
@dataclass
class PowerReading:
    timestamp: datetime           # UTC timestamp

    # Power metrics
    watts_actual: float          # Actual power (W): + = charging, - = discharging
    watts_negotiated: int        # PD negotiated max power (W)

    # Electrical details
    voltage: float               # Voltage (V)
    amperage: float              # Current (A)

    # Battery state
    current_capacity: int        # Current capacity (mAh)
    max_capacity: int            # Max capacity (mAh)
    battery_percent: int         # Battery percentage (0-100)

    # Status
    is_charging: bool
    external_connected: bool
    charger_name: str | None
    charger_manufacturer: str | None
```

### Database Schema

All power readings are automatically saved to SQLite at `~/.powermonitor/powermonitor.db` (configurable via `[database].path` in config.toml):

```sql
CREATE TABLE IF NOT EXISTS power_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    watts_actual REAL NOT NULL,
    watts_negotiated INTEGER NOT NULL,
    voltage REAL NOT NULL,
    amperage REAL NOT NULL,
    current_capacity INTEGER NOT NULL,
    max_capacity INTEGER NOT NULL,
    battery_percent INTEGER NOT NULL,
    is_charging INTEGER NOT NULL,
    external_connected INTEGER NOT NULL,
    charger_name TEXT,
    charger_manufacturer TEXT
);
CREATE INDEX idx_timestamp ON power_readings(timestamp DESC);
```

**Database operations** (`src/powermonitor/database.py`):
- `insert_reading()`: Save PowerReading to database
- `query_history(limit=60)`: Retrieve last N readings
- `get_statistics(limit=100)`: Calculate avg/min/max stats
- `clear_history()`: Delete all readings
- `close()`: Close database resources (currently no-op, API compatibility)

**Resource Management**:
- Uses `_get_connection()` context manager for write operations (combines `closing()` + transaction management)
- Uses `closing()` context manager for read-only operations
- All connections properly closed to prevent ResourceWarnings
- TUI calls `database.close()` on shutdown for proper cleanup

### CLI Commands

powermonitor provides multiple commands via `typer`:

**Main Command** (`src/powermonitor/cli.py:main`):
- Launches TUI with configurable options
- Loads config from `~/.powermonitor/config.toml` (if exists)
- CLI options override config values: `--interval`, `--stats-limit`, `--chart-limit`, `--debug`
- Configuration priority: CLI args > Config file > Defaults
- Configuration validation via `PowerMonitorConfig.__post_init__()`

**Data Export** (`powermonitor export`):
- Exports readings to CSV or JSON format
- Auto-detects format from file extension
- Supports `--limit` and `--format` options
- Uses `Database.query_history()` and helper functions `_export_csv()`, `_export_json()`

**Database Statistics** (`powermonitor stats`):
- Shows total readings, date range, database size
- Uses `Database.get_statistics()` and file system stats
- Rich table formatting for professional output

**History Viewing** (`powermonitor history`):
- Displays recent readings in formatted table
- Shows time, power, battery %, voltage, current, status
- Status icons: ⚡ Charging / 🔌 AC Power / 🔋 Battery
- Configurable limit (default: 20)

**Data Cleanup** (`powermonitor cleanup`):
- Delete readings by age: `--days N`
- Delete all readings: `--all` (requires confirmation)
- Direct SQL execution for age-based deletion
- Uses `Database.clear_history()` for full deletion

**Battery Health** (`powermonitor health`):
- Analyzes battery degradation over time
- Calculates daily average `max_capacity`
- Shows change in mAh and percentage
- Status indicators: Stable / Degrading (normal) / Degrading (significant)
- Daily trend table for last 7 days

### Configuration System

powermonitor uses a flexible configuration system with three layers:

**Configuration Layers** (in priority order):
1. **CLI Arguments** - Highest priority, overrides everything
2. **Config File** - `~/.powermonitor/config.toml` (optional)
3. **Defaults** - Hardcoded defaults in `PowerMonitorConfig`

**Implementation** (`src/powermonitor/config_loader.py`):
- `load_config() -> PowerMonitorConfig`: Loads TOML file and returns config object
- `get_config_path() -> Path`: Returns path to config file
- Graceful fallback: Missing or invalid config files use defaults with warning
- All config values validated via `PowerMonitorConfig.__post_init__()`

**PowerMonitorConfig Fields** (`src/powermonitor/config.py`):
- `collection_interval: float = 1.0` - Data collection interval in seconds
- `stats_history_limit: int = 100` - Number of readings for statistics
- `chart_history_limit: int = 60` - Number of readings to display in chart
- `database_path: Path` - Database file location (default: `~/.powermonitor/powermonitor.db`)
- `default_history_limit: int = 20` - Default limit for history command
- `default_export_limit: int = 1000` - Default limit for export command
- `log_level: str = "INFO"` - Logging level (DEBUG, INFO, WARNING, ERROR)

**Usage Pattern in CLI Commands**:
```python
from .config_loader import load_config

def some_command(limit: int | None = None):
    # Load config (file or defaults)
    config = load_config()

    # CLI arg overrides config
    if limit is None:
        limit = config.default_history_limit

    # Use config for database path
    db = Database(config.database_path)
```

**Breaking Change**: The `POWERMONITOR_DB_PATH` environment variable is no longer supported. Use `[database].path` in config.toml instead.

### IOKit/SMC FFI Implementation

powermonitor uses **ctypes** for direct macOS IOKit/SMC access:

**Bindings** (`src/powermonitor/collector/iokit/bindings.py`):
- 9 IOKit functions: IOMasterPort, IOServiceMatching, IOConnectCallStructMethod, etc.
- Handles mach_task_self() as a global variable (not function)

**Structures** (`src/powermonitor/collector/iokit/structures.py`):
- SMCKeyData, KeyInfo, SMCVersion, SMCPLimitData (all packed structs)
- Helper functions: str_to_key(), key_to_str(), type_to_str()

**Parser** (`src/powermonitor/collector/iokit/parser.py`):
- `bytes_to_float()` supporting 13 SMC data types:
  - Signed fixed-point: sp78, sp87, sp96, spa5, spb4, spf0 (divide by 256)
  - Unsigned fixed-point: fp88, fp79, fp6a, fp4c (divide by 256)
  - IEEE 754 float: flt
  - Integers: ui8, ui16, ui32

**SMC Sensor Keys:**
- **PDTR**: Power Delivery/Input Rate (W) - Most accurate for watts_actual
- **PPBR**: Battery Power Rate (W)
- **PSTR**: System Total Power Consumption (W)
- **PHPC**: Heatpipe/Cooling Power (W)
- **PDBR**: Display Brightness Power (W)
- **TB0T**: Battery Temperature (°C)
- **CHCC**: Charging Status

### Background Data Collection

The TUI uses **asyncio** for background data collection:

```python
async def _collection_loop(self) -> None:
    while True:
        await asyncio.sleep(self.config.collection_interval)  # Default: 1.0s
        await self._collect_and_update()

async def _collect_and_update(self) -> None:
    # Run blocking collector in executor (avoid blocking UI)
    loop = asyncio.get_event_loop()
    reading = await loop.run_in_executor(None, self.collector.collect)

    # Save to database
    await loop.run_in_executor(None, self.database.insert_reading, reading)

    # Update all widgets reactively
    self.call_from_thread(self._update_all_widgets, reading)
```

## Development Guidelines

### Code Quality

**Best Practices:**
- Use type hints for all function signatures
- Follow PEP 8 style guide (enforced by ruff)
- Keep functions focused and testable
- Use dataclasses for structured data
- Prefer composition over inheritance

**Type Checking:**
```bash
uv run ty check .
```

**Linting:**
```bash
uv run ruff check src/
uv run ruff format src/
```

**Known Issues and Improvements:**
See `IMPROVEMENTS.md` for a detailed roadmap. All critical phases are complete:
- ✅ Phase 1: Critical issues (database, error handling)
- ✅ Phase 2: Configuration and validation
- ✅ Phase 3: Code quality (IOKit errors, shutdown)
- ✅ Phase 4: Essential CLI features (export, cleanup, health)
- ✅ Resource management improvements (SQLite connection cleanup, ResourceWarning fixes)
- Phase 5: Optional enhancements (TUI tests, additional features)

The improvement roadmap is organized by priority to guide systematic refactoring.

**Recent Improvements:**
- **Resource Management**: Proper SQLite connection cleanup using `closing()` and `_get_connection()` context managers
- **Code Quality**: Removed unnecessary complexity suppressions and pytest warning filters
- **Test Infrastructure**: Updated test fixtures to properly yield and cleanup database connections

### Adding New Features

**To add a new data field to PowerReading:**

1. Update `PowerReading` dataclass in `src/powermonitor/models.py`
2. Update `IORegBattery` dataclass if parsing from ioreg
3. Modify conversion in `IORegCollector._parse_battery_data()`
4. Update database schema in `src/powermonitor/database.py`
5. Update display in `src/powermonitor/tui/widgets.py`
6. Run type checking and linting

**To add a new SMC sensor:**

1. Add sensor key to `SMC_SENSORS` dict in `src/powermonitor/collector/iokit/collector.py`
2. Add field to `SMCPowerData` dataclass
3. Update `_read_smc_sensors()` to read the new sensor
4. Use the value in `_collect_with_smc()` if needed

**To add a new TUI widget:**

1. Create widget class in `src/powermonitor/tui/widgets.py`
2. Add to layout in `PowerMonitorApp.compose()` in `src/powermonitor/tui/app.py`
3. Update widget in `_update_all_widgets()`
4. Add CSS styling to `PowerMonitorApp.CSS`

### Testing

- Test fixtures available in `tests/fixtures/real_mac.txt`
- Use `uv run pytest` when tests are added
- Manual testing: `uv run powermonitor`

### macOS Power Data Sources

**ioreg key mappings** (from `AppleSmartBattery` IORegistry entry):

```
CurrentCapacity          → current_capacity (mAh)
MaxCapacity              → max_capacity (mAh)
IsCharging               → is_charging (bool)
ExternalConnected        → external_connected (bool)
Voltage                  → voltage (mV → V conversion)
Amperage                 → amperage (mA → A conversion, negative = discharging)
AppleRawAdapterDetails   → charger info array
  [0].Watts              → watts_negotiated
  [0].Name               → charger_name
  [0].Manufacturer       → charger_manufacturer
  [0].Voltage            → charger voltage (mV)
  [0].Current            → charger current (mA)
```

**Actual wattage calculation**: `voltage (V) × amperage (A) = watts (W)`

## Platform Support

- **Required**: macOS 12.0+ (Monterey or later)
- **Python**: 3.13+ (uses modern type hints: `str | None`, etc.)
- **Dependencies**: textual, rich, textual-plotext (managed by uv)
- **macOS-only**: Uses IOKit framework and ioreg command

## Important Files

- `pyproject.toml`: Project configuration, dependencies, and scripts
- `uv.lock`: Locked dependency versions
- `~/.powermonitor/powermonitor.db`: SQLite database (auto-created in user's home directory)
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff, ty, typos)
- `tests/fixtures/real_mac.txt`: Sample ioreg output for testing
- `IMPROVEMENTS.md`: Detailed improvement roadmap with prioritized issues and enhancement ideas

## Performance Targets

- Memory usage: <50MB RAM
- CPU usage: <1% when idle
- Collection interval: 1 second (configurable)
- Database queries: Indexed by timestamp for fast retrieval

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PowerFlow is a macOS power monitoring tool with an auto-updating TUI (Text User Interface). Built with Python 3.12+, it provides real-time battery power monitoring with historical data visualization and SQLite-based persistence.

**Current Status**: Fully migrated from Rust to Python. Single-command TUI with auto-updating display, background data collection, and SQLite history tracking.

## Essential Commands

### Running PowerFlow

```bash
# Launch the auto-updating TUI
powerflow

# Or using uv:
uv run powerflow
```

### Development

```bash
# Install dependencies
uv sync

# Run with verbose collector info (debug mode)
uv run python -c "from powerflow.collector import default_collector; default_collector(verbose=True).collect()"

# Run tests (when available)
uv run pytest

# Type checking
uv run mypy src/

# Linting and formatting
uv run ruff check src/
uv run ruff format src/
```

## Project Structure

```
powerflow/
├── pyproject.toml              # uv project configuration
├── uv.lock                     # Dependency lock file
├── src/
│   └── powerflow/
│       ├── __init__.py
│       ├── cli.py              # Entry point (launches TUI)
│       ├── models.py           # PowerReading dataclass (12 fields)
│       ├── database.py         # SQLite operations
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
├── tests/
│   └── fixtures/
│       └── real_mac.txt        # Sample ioreg output for testing
└── powerflow.db                # SQLite database (auto-created)
```

## Architecture Overview

### TUI Application

PowerFlow uses **Textual** for the TUI with a 3-panel auto-updating layout:

1. **LiveDataPanel** (green border): Real-time power metrics
   - Status indicator: ⚡ Charging / 🔌 AC Power / 🔋 On Battery
   - Current power (W), battery %, voltage, amperage
   - Charger information if available
   - Updates every 2 seconds

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

PowerFlow uses the **Strategy Pattern** via the `PowerCollector` protocol:

```python
class PowerCollector(Protocol):
    def collect(self) -> PowerReading: ...
```

**Available collectors:**

1. **IOKitCollector** (preferred): Direct IOKit/SMC API access via ctypes
   - Reads 7 SMC sensors: PPBR, PDTR, PSTR, PHPC, PDBR, TB0T, CHCC
   - Uses PDTR (Power Delivery/Input Rate) for most accurate watts_actual
   - Falls back to IORegCollector on error
   - Location: `src/powerflow/collector/iokit/collector.py`

2. **IORegCollector** (fallback): Parses `ioreg -rw0 -c AppleSmartBattery -a` output
   - No special permissions required
   - Uses plistlib to parse XML output
   - Location: `src/powerflow/collector/ioreg.py`

The `default_collector()` function tries IOKitCollector first, automatically falling back to IORegCollector if SMC sensors are unavailable.

### Data Models

Core data structure is `PowerReading` (defined in `src/powerflow/models.py`):

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

All power readings are automatically saved to SQLite (`powerflow.db`):

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

**Database operations** (`src/powerflow/database.py`):
- `insert_reading()`: Save PowerReading to database
- `query_history(limit=60)`: Retrieve last N readings
- `get_statistics(limit=100)`: Calculate avg/min/max stats
- `clear_history()`: Delete all readings

### IOKit/SMC FFI Implementation

PowerFlow uses **ctypes** for direct macOS IOKit/SMC access:

**Bindings** (`src/powerflow/collector/iokit/bindings.py`):
- 9 IOKit functions: IOMasterPort, IOServiceMatching, IOConnectCallStructMethod, etc.
- Handles mach_task_self() as a global variable (not function)

**Structures** (`src/powerflow/collector/iokit/structures.py`):
- SMCKeyData, KeyInfo, SMCVersion, SMCPLimitData (all packed structs)
- Helper functions: str_to_key(), key_to_str(), type_to_str()

**Parser** (`src/powerflow/collector/iokit/parser.py`):
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
        await asyncio.sleep(self.collection_interval)  # Default: 2.0s
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
uv run mypy src/
```

**Linting:**
```bash
uv run ruff check src/
uv run ruff format src/
```

### Adding New Features

**To add a new data field to PowerReading:**

1. Update `PowerReading` dataclass in `src/powerflow/models.py`
2. Update `IORegBattery` dataclass if parsing from ioreg
3. Modify conversion in `IORegCollector._parse_battery_data()`
4. Update database schema in `src/powerflow/database.py`
5. Update display in `src/powerflow/tui/widgets.py`
6. Run type checking and linting

**To add a new SMC sensor:**

1. Add sensor key to `SMC_SENSORS` dict in `src/powerflow/collector/iokit/collector.py`
2. Add field to `SMCPowerData` dataclass
3. Update `_read_smc_sensors()` to read the new sensor
4. Use the value in `_collect_with_smc()` if needed

**To add a new TUI widget:**

1. Create widget class in `src/powerflow/tui/widgets.py`
2. Add to layout in `PowerFlowApp.compose()` in `src/powerflow/tui/app.py`
3. Update widget in `_update_all_widgets()`
4. Add CSS styling to `PowerFlowApp.CSS`

### Testing

- Test fixtures available in `tests/fixtures/real_mac.txt`
- Use `uv run pytest` when tests are added
- Manual testing: `uv run powerflow`

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
- **Python**: 3.12+ (uses modern type hints: `str | None`, etc.)
- **Dependencies**: textual, rich, textual-plotext (managed by uv)
- **macOS-only**: Uses IOKit framework and ioreg command

## Important Files

- `pyproject.toml`: Project configuration, dependencies, and scripts
- `uv.lock`: Locked dependency versions
- `powerflow.db`: SQLite database (auto-created, not in version control)
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff, mypy, typos)
- `tests/fixtures/real_mac.txt`: Sample ioreg output for testing

## Performance Targets

- Memory usage: <50MB RAM
- CPU usage: <1% when idle
- Collection interval: 2 seconds (configurable)
- Database queries: Indexed by timestamp for fast retrieval

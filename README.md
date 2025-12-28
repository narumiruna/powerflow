# PowerFlow

macOS power monitoring tool with auto-updating TUI for real-time battery and charging status.

## Status

**Fully Migrated to Python**: Complete TUI implementation with auto-updating display, IOKit/SMC FFI, and SQLite history tracking.

## Features

- 🖥️ **Auto-updating TUI** with 3-panel layout (Textual framework)
- ⚡ **Real-time monitoring** - Updates every 2 seconds automatically
- 📊 **Live power metrics** - Voltage, amperage, wattage, battery %
- 📈 **Historical visualization** - Power chart and statistics
- 🔋 **Battery tracking** - Capacity, charging status, charger info
- 💾 **SQLite persistence** - Automatic background data logging
- 🎯 **IOKit/SMC access** - Direct macOS API integration via ctypes
- 🔄 **Auto-fallback** - Graceful fallback to subprocess-based collection

## Installation

### Install with uv (recommended)

```bash
# Clone the repository
git clone <repo-url>
cd powerflow

# Install dependencies
uv sync

# Run PowerFlow
uv run powerflow
```

### Install as a package

```bash
# Install from source
cd powerflow
uv pip install -e .

# Run from anywhere
powerflow
```

## Usage

### Launch the TUI

```bash
# Single command launches auto-updating TUI
powerflow
```

The TUI displays:

```
┌─ PowerFlow ──────────────────────────────┐
│ Real-Time Power                           │
│ ⚡ 45.2W / 67W    🔋 72%    ⚡ Charging   │
│ 20.0V × 2.26A                             │
├───────────────────────────────────────────┤
│ Statistics (Last 100 readings)            │
│ Avg: 42.3W  Max: 55.1W  Min: 12.4W       │
├───────────────────────────────────────────┤
│ Power Chart (Last 60 readings)            │
│     55W ┤      ╭──╮                       │
│     45W ┤  ╭───╯  ╰──╮                    │
│     35W ┤──╯         ╰─                   │
│         └───────────────────               │
│ [q] Quit  [r] Refresh  [c] Clear History │
└───────────────────────────────────────────┘
```

### Keyboard Controls

- `q` or `ESC` - Quit application
- `r` - Force refresh data
- `c` - Clear history (with confirmation)

### Development Mode

```bash
# Run with verbose collector info
uv run python -c "from powerflow.collector import default_collector; collector = default_collector(verbose=True); print(collector.collect())"

# Test data collection
uv run python -c "from powerflow.collector import default_collector; print(default_collector().collect())"
```

## Requirements

- **macOS**: 12.0+ (Monterey or later)
- **Python**: 3.12+ (uses modern type hints)
- **Dependencies**: textual, rich, textual-plotext (auto-installed by uv)

## Architecture

### TUI Layout (3 Panels)

1. **LiveDataPanel** (green) - Real-time power data
   - Status: ⚡ Charging / 🔌 AC Power / 🔋 On Battery
   - Power: watts_actual / watts_negotiated
   - Battery: percentage, capacity (mAh)
   - Electrical: voltage, amperage
   - Charger info (if available)

2. **StatsPanel** (cyan) - Historical statistics
   - Time range (earliest/latest)
   - Average/min/max power
   - Average battery percentage
   - Based on last 100 readings

3. **ChartWidget** (blue) - Power over time
   - Line chart with 60 data points
   - Shows actual power and max negotiated power
   - Auto-scales based on data

### Data Collection

PowerFlow uses two collectors with automatic fallback:

1. **IOKitCollector** (preferred) - Direct IOKit/SMC API via ctypes
   - Reads 7 SMC sensors: PPBR, PDTR, PSTR, PHPC, PDBR, TB0T, CHCC
   - Most accurate power readings (PDTR sensor)
   - Zero overhead (no subprocess)

2. **IORegCollector** (fallback) - Subprocess-based
   - Executes `ioreg -rw0 -c AppleSmartBattery -a`
   - Parses plist output using Python's plistlib
   - Works on all Macs without special permissions

### Database

All readings automatically saved to SQLite (`powerflow.db`):

```sql
CREATE TABLE power_readings (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    watts_actual REAL,
    watts_negotiated INTEGER,
    voltage REAL,
    amperage REAL,
    current_capacity INTEGER,
    max_capacity INTEGER,
    battery_percent INTEGER,
    is_charging INTEGER,
    external_connected INTEGER,
    charger_name TEXT,
    charger_manufacturer TEXT
);
```

## Project Structure

```
powerflow/
├── pyproject.toml              # uv project config
├── uv.lock                     # Dependency lock file
├── src/
│   └── powerflow/
│       ├── cli.py              # Entry point
│       ├── models.py           # PowerReading dataclass
│       ├── database.py         # SQLite operations
│       ├── collector/          # Data collection
│       │   ├── base.py         # PowerCollector protocol
│       │   ├── ioreg.py        # Subprocess collector
│       │   ├── factory.py      # Auto-fallback logic
│       │   └── iokit/          # IOKit/SMC FFI
│       │       ├── bindings.py # ctypes bindings
│       │       ├── structures.py # SMC data structures
│       │       ├── parser.py   # Binary parsing
│       │       ├── connection.py # SMCConnection
│       │       └── collector.py # IOKitCollector
│       └── tui/                # Textual TUI
│           ├── app.py          # PowerFlowApp
│           └── widgets.py      # Custom widgets
└── tests/
    └── fixtures/               # Test data
```

## Development

### Code Quality

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Auto-formatting
uv run ruff format src/

# Run all checks
uv run mypy src/ && uv run ruff check src/ && uv run ruff format src/
```

### Testing

```bash
# Run tests (when available)
uv run pytest

# Manual testing
uv run powerflow
```

## Performance

- **Memory**: <50MB RAM
- **CPU**: <1% when idle
- **Update interval**: 2 seconds (configurable)
- **Database**: Indexed for fast queries

## Migration Notes

This project was fully migrated from Rust to Python (December 2025):

- **From**: Rust CLI with separate `status`, `watch`, `history` commands
- **To**: Python TUI with unified auto-updating interface
- **Reason**: Better rapid development, easier maintenance, similar performance for 2s intervals
- **Preserved**: All data collection logic, database schema, SMC sensor access (via ctypes)

## License

MIT

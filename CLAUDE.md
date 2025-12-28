# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PowerFlow is a macOS command-line tool that monitors real-time battery power and charging status. Built with Rust, it provides both human-readable and JSON output formats for power metrics, with SQLite-based history tracking.

**Current Status**: CLI-first implementation (Phase 1-3 complete). The original Tauri GUI has been removed; focus is on the CLI tool.

## Essential Commands

### Building and Running

```bash
# Build the CLI (debug mode)
cargo build

# Build release binary
cargo build --release

# Run the CLI
cargo run
# Or after building:
./target/release/powerflow

# Run with specific features
cargo build --release --features iokit
```

### Code Quality

```bash
# Run linter (REQUIRED after every Rust file modification)
cargo clippy

# Format code (REQUIRED after every Rust file modification)
cargo fmt

# Run all tests
cargo test

# Run tests for specific crate
cargo test -p powerflow-core
```

### CLI Usage Examples

```bash
# Show current power status
powerflow
# or: powerflow status

# Continuous monitoring (watch mode, updates every 2 seconds)
powerflow watch --interval 2

# JSON output
powerflow --json

# Query charging history (TUI with statistics, table, and chart)
powerflow history

# Query history with custom limit
powerflow history --limit 50

# Export history as JSON
powerflow history --json

# Export history as PNG chart
powerflow history --plot --output my-chart.png
```

## Workspace Structure

This is a Cargo workspace with three crates:

```
powerflow/
├── Cargo.toml                 # Workspace manifest
├── crates/
│   ├── powerflow-core/        # Core library: data collection and models
│   │   ├── src/
│   │   │   ├── lib.rs         # Public API
│   │   │   ├── models.rs      # PowerReading, IORegBattery data structures
│   │   │   ├── error.rs       # Error types
│   │   │   └── collector/     # Data collection strategies
│   │   │       ├── mod.rs     # PowerCollector trait
│   │   │       ├── ioreg.rs   # Parse `ioreg` command output (default)
│   │   │       ├── iokit.rs   # Direct IOKit API (requires iokit feature)
│   │   │       └── smc/       # System Management Controller access
│   │   └── Cargo.toml
│   ├── powerflow-cli/         # CLI application
│   │   ├── src/
│   │   │   ├── main.rs        # Entry point
│   │   │   ├── cli.rs         # Clap CLI definition and execution logic
│   │   │   ├── database.rs    # SQLite operations for history
│   │   │   └── display/       # Output formatting
│   │   │       ├── mod.rs
│   │   │       ├── human.rs   # Human-readable colored output
│   │   │       └── json.rs    # JSON output
│   │   └── Cargo.toml
│   └── powerflow-app/         # Legacy Tauri app (removed UI, structure kept)
└── powerflow.db               # SQLite database (auto-created at runtime)
```

## Architecture Overview

### Data Collection Strategy Pattern

PowerFlow uses the **Strategy Pattern** for data collection via the `PowerCollector` trait (`powerflow-core/src/collector/mod.rs`):

```rust
pub trait PowerCollector {
    fn collect(&self) -> PowerResult<PowerReading>;
}
```

**Available collectors:**

1. **IORegCollector** (default): Parses `ioreg -rw0 -c AppleSmartBattery` output
   - No special permissions required
   - Uses plist parsing to extract battery info
   - Location: `powerflow-core/src/collector/ioreg.rs`

2. **IOKitCollector** (requires `iokit` feature): Direct IOKit/SMC API access
   - More efficient (no subprocess spawning)
   - Provides additional SMC sensor data
   - Location: `powerflow-core/src/collector/iokit.rs`
   - SMC implementation: `powerflow-core/src/collector/smc/`

The `default_collector()` function returns the appropriate collector based on features:
- If `iokit` feature is enabled → `IOKitCollector`
- Otherwise → `IORegCollector`

### Data Models

Core data structure is `PowerReading` (defined in `powerflow-core/src/models.rs`):

```rust
pub struct PowerReading {
    pub timestamp: DateTime<Utc>,

    // Power metrics
    pub watts_actual: f64,        // Actual power flow (W): + = charging, - = discharging
    pub watts_negotiated: i32,    // PD negotiated max power (W)

    // Electrical details
    pub voltage: f64,             // Voltage (V)
    pub amperage: f64,            // Current (A)

    // Battery state
    pub current_capacity: i32,    // Current capacity (mAh)
    pub max_capacity: i32,        // Max capacity (mAh)
    pub battery_percent: i32,     // Battery percentage (0-100)

    // Status
    pub is_charging: bool,
    pub external_connected: bool,
    pub charger_name: Option<String>,
    pub charger_manufacturer: Option<String>,
}
```

`IORegBattery` is the raw deserialization target for ioreg plist output, which gets converted into `PowerReading`.

### CLI Architecture

The CLI uses **clap** with derive macros (`powerflow-cli/src/cli.rs`):

- **Commands**: `status` (or default), `watch`, `history`
- **Global flags**: `--json`
- **Execution flow**: `main.rs` → `Cli::parse()` → `Cli::execute()`

Each command:
1. Initializes SQLite database (`database.rs`)
2. Collects power data via `powerflow_core::collect()`
3. Saves reading to database
4. Displays output (human or JSON format)

### History Tracking

All power readings from `status` and `watch` commands are automatically saved to SQLite (`powerflow.db`).

**Database schema** (`powerflow-cli/src/database.rs`):

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
)
```

**History display modes** (via `powerflow history`):

1. **TUI mode** (default): Three-panel ratatouille interface
   - Statistics block: time range, avg/max/min power, avg battery %
   - Table block: Latest 10 records with all fields
   - Chart block: Line chart of power vs. max power (press 'q' to exit)

2. **JSON mode** (`--json`): Array of PowerReading objects

3. **PNG export** (`--plot --output <file>`): Plotters-generated chart image

### Watch Mode Implementation

Watch mode (`powerflow watch`) uses `crossterm` for terminal control:
- Clears screen on each update
- Moves cursor to (0,0) for in-place updates
- Sleeps for specified interval between readings
- Each reading is saved to database
- Press Ctrl+C to exit

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

## Development Guidelines

### Code Quality Requirements

**CRITICAL**: After modifying ANY Rust file:
1. Run `cargo clippy` to check for lints
2. Run `cargo fmt` to format code
3. Ensure both pass before committing

This ensures code quality, consistent style, and correctness.

### Testing

- Unit tests are located in the same files as implementation (using `#[cfg(test)]` modules)
- Test fixtures for ioreg parsing may be in `tests/fixtures/` directories
- Always run `cargo test` before pushing changes

### Adding New Features

**To add a new data field to PowerReading:**

1. Update `PowerReading` struct in `powerflow-core/src/models.rs`
2. Update `IORegBattery` struct if parsing from ioreg
3. Modify `From<IORegBattery> for PowerReading` conversion
4. Update database schema in `powerflow-cli/src/database.rs`
5. Update display formatters in `powerflow-cli/src/display/`
6. Run `cargo clippy` and `cargo fmt`
7. Add tests for the new field

**To add a new CLI command:**

1. Add variant to `Commands` enum in `powerflow-cli/src/cli.rs`
2. Implement execution logic in `Cli::execute()` match arm
3. Add display logic in `powerflow-cli/src/display/` if needed
4. Update this file's CLI usage examples

### Performance Considerations

- Target resource usage: <30MB RAM, <0.5% CPU idle
- Default watch interval: 2 seconds (balance between responsiveness and overhead)
- Database uses SQLite with bundled feature for portability

## Platform Support

- **Required**: macOS 12.0+ (Monterey or later)
- **Build requirements**: Rust 1.75+
- **macOS-only**: Uses IOKit framework and ioreg command (not cross-platform)

## Important Files

- `POWERFLOW.md`: Detailed technical documentation (legacy Tauri architecture, mostly outdated for current CLI focus)
- `README.md`: User-facing documentation with usage examples
- `Cargo.toml`: Workspace configuration with shared dependencies
- `powerflow.db`: SQLite database (auto-created, not in version control)

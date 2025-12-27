# PowerFlow

macOS menu bar app for monitoring charging power and battery status.

## Status

**Phase 1 Complete**: CLI-first implementation with ioreg parser

## Features

- 📊 Real-time power monitoring (voltage, amperage, wattage)
- 🔋 Battery status and capacity tracking
- ⚡ Charger detection and power negotiation info
- 💻 Beautiful terminal output with colors
- 📄 JSON output for scripting
- 🔄 Watch mode for continuous monitoring

## Installation

### Build from source

```bash
# Clone the repository
git clone <repo-url>
cd powerflow

# Build release binary
cargo build --release

# Binary will be at ./target/release/powerflow
./target/release/powerflow
```

## Usage

### Show current power status

```bash
powerflow
```

Output:
```
🔌 On AC Power (Not Charging)
   Power: 0.0W / 70W max
   Battery: 82% (3878 mAh / 4745 mAh)
   Electrical: 12.71V × 0.00A
   Charger: pd charger
   Time: 2025-12-27 18:37:19
```

### JSON output

```bash
powerflow --json
```

### Continuous monitoring (watch mode)

```bash
powerflow watch --interval 2
```

Updates every 2 seconds (default). Press Ctrl+C to exit.

## Requirements

- macOS 12.0+ (Monterey or later)
- Rust 1.75+ (for building from source)

## Project Structure

```
powerflow/
├── crates/
│   ├── powerflow-core/    # Core library (ioreg parser, data models)
│   └── powerflow-cli/     # CLI application
└── tests/
    └── fixtures/          # Real ioreg output for testing
```

## Development

```bash
# Run tests
cargo test

# Run with debug output
cargo run

# Build release
cargo build --release
```

## Roadmap

- [x] Phase 1: CLI with ioreg parsing
- [ ] Phase 2: Watch mode & IOKit/SMC integration
- [ ] Phase 3: SQLite history recording
- [ ] Phase 4: Tauri GUI with menu bar icon

## License

MIT
# Powerflow Code Guide

## Recent Changes (2025-12-28)
- Removed unused import (`PowerError`) from `crates/powerflow-core/src/collector/iokit.rs`
- Updated CLI and SMC modules
- Added new file: `crates/powerflow-cli/src/database.rs`
- Modified: `CLAUDE.md`, `crates/powerflow-cli/Cargo.toml`, `crates/powerflow-cli/src/cli.rs`, `crates/powerflow-cli/src/display/json.rs`, `crates/powerflow-cli/src/main.rs`, `crates/powerflow-core/src/collector/smc/ffi.rs`, `crates/powerflow-core/src/collector/smc/mod.rs`

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Powerflow is a macOS application that monitors power usage and charging status of Mac and iOS devices. It's built with:
- **Frontend**: Vue 3 + TypeScript + Vite + Tailwind CSS
- **Backend**: Tauri v2 (Rust)
- **Custom Crate**: `tpower` - Low-level power monitoring via macOS IOKit and SMC (System Management Controller)

## Common Commands

### Frontend Development
```bash
pnpm dev           # Start Vite dev server
pnpm build         # Type-check with vue-tsc, optimize, and build
pnpm preview       # Preview production build
```

### Tauri Development
```bash
pnpm tauri dev     # Run Tauri app in development mode
pnpm tauri build   # Build production app (.dmg for macOS)
```

### Code Quality
```bash
npx eslint .       # Run ESLint (uses @antfu/eslint-config)
cargo clippy       # Run Rust linter (workspace has pedantic, nursery, cargo lints enabled)
cargo fmt          # Format Rust code
```

### Database
```bash
# SQLx is used with offline mode (.sqlx/ directory contains query metadata)
# Migrations are in src-tauri/migrations/
sqlx migrate run   # Apply migrations (if developing new migrations)
```

### Testing
```bash
cargo test         # Run Rust tests
cargo test -p tpower  # Test specific crate
```

---

## Technical Implementation Details

This section provides detailed technical information about how Powerflow works, intended for developers who want to understand the implementation or port it to other languages/platforms.

### 1. Mac Power Monitoring via SMC (System Management Controller)

**Location**: `crates/tpower/src/ffi/smc.rs`

The SMC is a low-level chip in Macs that manages power, thermal, and other hardware functions. Powerflow reads power data directly from SMC using IOKit.

#### SMC Access Flow

1. **Open SMC connection** (`SMCConnection::new`):
   - Get IOKit master port via `IOMasterPort()`
   - Find "AppleSMC" service via `IOServiceMatching()` and `IOServiceGetMatchingServices()`
   - Open connection with `IOServiceOpen(device, mach_task_self(), 0, &conn)`

2. **Read SMC keys** (`read_key`):
   - Convert 4-character key (e.g., "PPBR") to u32 via big-endian encoding
   - First query key metadata via `CMD_READ_KEYINFO` (returns data type and size)
   - Then read actual value via `CMD_READ_BYTES`
   - Both use `IOConnectCallStructMethod(conn, KERNEL_INDEX_SMC, input, ...)` with index=2

3. **Key data structures**:
   - `SMCKeyData`: Input/output structure (80 bytes) containing key, command, and data buffer
   - `KeyInfo`: Metadata about key (data_size, data_type, attributes)
   - `SMCVal`: Parsed value with key, type, and byte array

4. **Data type conversion**:
   - SMC returns fixed-point numbers (e.g., "fp88", "sp78") stored as 16-bit integers
   - Convert to float: `value = raw_bytes / divisor`
   - Example: "fp88" means divide by 256.0, "sp78" is signed and divides by 256.0
   - Also supports: `flt` (IEEE 754 float), `ui8/ui16/ui32` (unsigned integers)

#### Critical SMC Sensor Keys

Located in `SMC_SENSORS` array (`smc.rs:20-22`):

- **PPBR**: Battery power rate (W) - positive when discharging
- **PDTR**: Power delivery/input rate (W) - from adapter or battery
- **PSTR**: System total power consumption (W)
- **PHPC**: Heatpipe/cooling power (W)
- **PDBR**: Display brightness power (W)
- **B0FC**: Battery full charge capacity (mAh)
- **SBAR**: Battery current capacity (mAh)
- **CHCC**: Charging status (0=not charging, >0=charging)
- **B0TE**: Time to empty (minutes)
- **B0TF**: Time to full (minutes)
- **TB0T**: Battery temperature (°C)

All power values are in watts (float32). Polling interval: 2000ms default (configurable 500-10000ms).

### 2. IORegistry Battery Information

**Location**: `crates/tpower/src/provider/mod.rs` (`get_mac_ioreg`)

IORegistry is macOS's device tree database. Battery info lives under "AppleSmartBattery" service.

#### Access Flow

1. Get master port via `IOMasterPort()`
2. Create matching dictionary for "AppleSmartBattery" via `IOServiceMatching()`
3. Get service via `IOServiceGetMatchingService()`
4. Read properties via `IORegistryEntryCreateCFProperties()` (returns CFDictionary)
5. Parse dictionary into `IORegistry` struct (see `crates/tpower/src/de.rs`)

#### Key IORegistry Properties

- **AdapterDetails**: Adapter voltage (mV), watts, current (mA), name, wireless status
- **PowerTelemetryData**: High-precision power metrics
  - `SystemPowerIn`: Total input power (mW)
  - `SystemLoad`: System power consumption (mW)
  - `BatteryPower`: Battery charge/discharge power (mW)
  - `AdapterEfficiencyLoss`: Power lost in conversion (mW)
- **AppleRawCurrentCapacity / AppleRawMaxCapacity**: Actual battery mAh values
- **CurrentCapacity / MaxCapacity**: Percentage-based capacity
- **CycleCount**: Number of charge cycles
- **Temperature**: Battery temperature (centidegrees Celsius, divide by 100)
- **IsCharging**: Boolean charging state
- **TimeRemaining**: Minutes until empty/full

### 3. iOS Device Monitoring via MobileDevice Framework

**Location**: `crates/tpower/src/ffi/mod.rs`, `src/ffi/wrapper.rs`

MobileDevice.framework is a private Apple framework (ships with Xcode) for communicating with iOS devices over USB/WiFi.

#### FFI Declarations

Key functions linked from `MobileDevice.framework`:

- `AMDeviceNotificationSubscribe(callback, 0, 0, context, &notification)`: Subscribe to device attach/detach events
- `AMDeviceCopyDeviceIdentifier(device)`: Get UDID
- `AMDeviceCopyValue(device, domain, key)`: Read device properties (e.g., "DeviceName")
- `AMDeviceGetInterfaceType(device)`: Returns USB(1) or WiFi(2)
- `AMDeviceConnect(device)`: Connect to device
- `AMDeviceIsPaired(device)` / `AMDevicePair(device)`: Pairing management
- `AMDeviceValidatePairing(device)`: Verify existing pairing
- `AMDeviceStartSession(device)` / `AMDeviceStopSession(device)`: Session management
- `AMDeviceSecureStartService(device, service_name, options, &connection)`: Start service

#### Device Connection Flow

1. **Subscribe to notifications** (`src-tauri/src/device.rs:42-79`):
   - Call `AMDeviceNotificationSubscribe` with C callback
   - Callback runs on CoreFoundation RunLoop (must call `CFRunLoopRun()` in separate thread)
   - Callback receives `AMDeviceNotificationCallbackInfo` with device reference and action (Attached=1, Detached=2)

2. **Prepare device** when attached (`wrapper.rs:181-189`):
   - `AMDeviceConnect()` - Establish connection
   - `AMDeviceIsPaired()` - Check if paired
   - `AMDevicePair()` - Pair if needed (user must unlock device and tap "Trust")
   - `AMDeviceValidatePairing()` - Verify pairing
   - `AMDeviceStartSession()` - Start secure session

3. **Start diagnostics service**:
   - Call `AMDeviceSecureStartService(device, "com.apple.mobile.diagnostics_relay", NULL, &connection)`
   - Returns `AMDServiceConnection` with socket and SSL context

4. **Query IORegistry data** (`crates/tpower/src/provider/remote.rs`):
   - Send message via `AMDServiceConnectionSendMessage(conn, dict, kCFPropertyListXMLFormat_v1_0)`
   - Message format (CFDictionary):
     ```
     {
       "Request": "IORegistry",
       "EntryClass": "IOPMPowerSource"
     }
     ```
   - Receive response via `AMDServiceConnectionReceiveMessage(conn, &response, ...)`
   - Response structure: `{Diagnostics: {IORegistry: {...}}}`
   - Parse into same `IORegistry` struct as Mac (iOS has same battery properties)

5. **Polling loop** (`src-tauri/src/device.rs:81-137`):
   - Every 2 seconds, iterate over connected devices
   - Query each device's IORegistry and emit `DevicePowerTickEvent`
   - Handle device detach by removing from HashMap

### 4. Data Normalization

**Location**: `crates/tpower/src/provider/mod.rs`

Both Mac and iOS data are normalized into `NormalizedResource` struct:

```rust
pub struct NormalizedResource {
    is_local: bool,              // true for Mac, false for iOS
    is_charging: bool,
    time_remain: Duration,
    adapter_name: Option<String>,
    cycle_count: i32,
    current_capacity: i32,       // mAh
    max_capacity: i32,           // mAh
    design_capacity: i32,        // mAh
    data: NormalizedData {
        system_in: f32,          // Input power (W)
        system_load: f32,        // System consumption (W)
        battery_power: f32,      // Battery charge/discharge (W)
        adapter_power: f32,      // Adapter output (W)
        efficiency_loss: f32,    // Conversion loss (W)
        brightness_power: f32,   // Display power (W, Mac only)
        heatpipe_power: f32,     // Cooling power (W, Mac only)
        battery_level: i32,      // Percentage (0-100)
        absolute_battery_level: f32,  // Based on actual mAh
        temperature: f32,        // Celsius
        adapter_watts: f32,      // Adapter rating (W)
        adapter_voltage: f32,    // Adapter voltage (V)
        adapter_amperage: f32,   // Adapter current (A)
    }
}
```

**Mac conversion** (`From<(&IORegistry, &SMCPowerData)>`):
- `system_in` = SMC.PDTR (delivery rate)
- `system_load` = SMC.PSTR (system total)
- `battery_power` = max(SMC.PPBR, delivery - system_total)
- `brightness_power` = SMC.PDBR
- `heatpipe_power` = SMC.PHPC
- `temperature` = SMC.TB0T

**iOS conversion** (`From<&IORegistry>`):
- Uses PowerTelemetryData if available
- `system_in` = SystemPowerIn / 1000 (mW → W)
- `system_load` = SystemLoad / 1000
- `battery_power` = BatteryPower / 1000
- `efficiency_loss` = AdapterEfficiencyLoss / 1000
- No brightness/heatpipe data (set to 0)

### 5. Charging History Recording

**Location**: `src-tauri/src/history.rs`

The history recorder listens to power events and detects charging sessions.

#### Recording Logic

1. **Event listeners**:
   - Listen to `PowerTickEvent` (Mac) and `DevicePowerTickEvent` (iOS)
   - Both send data to mpsc channel with device identifier

2. **Staging** (`spawn_history_recorder`):
   - Maintain HashMap of `DeviceType → Vec<ChargingHistoryStage>`
   - Each stage contains: `NormalizedResource` data + JSON raw string

3. **Stage collection criteria**:
   - Start collecting when `is_charging == true` and battery < 100%
   - Append stage only if `last_update` timestamp changed (avoid duplicates)
   - Log stage count on each append

4. **Session end detection**:
   - **Condition 1**: Previous stage was charging AND current is not charging (user unplugged)
   - **Condition 2**: Battery reached 100% (fully charged)
   - Filter out sessions with ≤2 samples (too short, likely noise)

5. **Summary calculation** (`summrize_history`):
   - **from_level**: Battery % at first sample
   - **end_level**: Battery % at last sample
   - **timestamp**: Unix timestamp of first sample
   - **duration**: Seconds between first and last sample
   - **adapter_name**: From last sample's adapter details
   - **avg**: Average of all `NormalizedData` fields across samples
   - **peak**: Maximum of each field across samples
   - **curve**: Array of all `NormalizedResource` samples
   - **raw**: Array of JSON-serialized raw data

6. **Storage**:
   - Save to SQLite via `save_charging_history()`
   - Emit `HistoryRecordedEvent` to frontend

### 6. Database Schema

**Location**: `src-tauri/migrations/`

```sql
-- 20241231010325_create_initial_tables.sql
CREATE TABLE charging_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_level INTEGER NOT NULL,
    end_level INTEGER NOT NULL,
    charging_time INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    detail BLOB NOT NULL  -- JSON serialized ChargingHistoryDetail
);

-- 20250104055910_add_name_with_udid.sql
ALTER TABLE charging_histories ADD COLUMN name TEXT NOT NULL DEFAULT '';
ALTER TABLE charging_histories ADD COLUMN udid TEXT NOT NULL DEFAULT '';
ALTER TABLE charging_histories ADD COLUMN is_remote INTEGER NOT NULL DEFAULT 0;

-- 20250106111532_add_adapter_info.sql
ALTER TABLE charging_histories ADD COLUMN adapter_name TEXT NOT NULL DEFAULT 'Unknown';
```

The `detail` BLOB contains `bincode` (or `serde_json`) serialized `ChargingHistoryDetail`:
- `avg`: Average power metrics
- `peak`: Peak power metrics
- `curve`: Full time-series data (array of samples)
- `raw`: Raw JSON strings for debugging

### 7. Frontend Data Flow

1. **Initialization** (`src/main.ts`, `src/lib/setup.ts`):
   - Create Vue app with router and i18n
   - Listen to Tauri events via `tauri-specta` event system

2. **Power updates** (`PowerTickEvent`, `DevicePowerTickEvent`):
   - Frontend receives events with `NormalizedResource` data
   - Update reactive stores (Pinia)
   - Render charts using `@unovis/vue` (Unovis visualization library)

3. **Status bar** (`PowerUpdatedEvent`):
   - Backend sends formatted string (e.g., "12.3 w")
   - Updates tray icon text via macOS APIs

4. **History view**:
   - Fetch list via `get_all_charging_history()` command
   - Click item to fetch detail via `get_detail_by_id(id)`
   - Render detailed charts and statistics

---

## Architecture Summary

### Workspace Structure
```
powerflow/
├── src/              # Vue frontend
├── src-tauri/        # Tauri Rust backend (main app)
└── crates/
    └── tpower/       # Low-level power monitoring library
```

This is a Cargo workspace with two main components:
1. **src-tauri** (powerflow crate): Tauri application layer
2. **crates/tpower**: Core power monitoring via macOS APIs

### Frontend Architecture

**Auto-imports**: Vue composables, components, and stores are auto-imported via `unplugin-auto-import` and `unplugin-vue-components`. Check `.auto-imports/` for generated type definitions.

**Multi-window setup**: The app has three HTML entry points:
- `index.html` → Main window (shows power usage charts and details)
- `popover.html` → Tray popover (quick status view)
- `settings.html` → Settings window

**Routing**: Vue Router with three main routes:
- `/` → MainContent (live power monitoring)
- `/history` → Historical charging data list
- `/history/:id` → Individual charging session detail

**State management**: Pinia stores with `tauri-plugin-pinia` for persistence. Store files in `src/stores/`.

**Type safety**: TypeScript bindings are auto-generated from Rust types via `tauri-specta` into `src/bindings.ts` (excluded from linting).

### Backend Architecture

**Tauri commands** (`src-tauri/src/lib.rs`): All commands use `#[tauri::command]` and `#[specta::specta]` for type generation. Main commands handle:
- Window management (`open_app`, `open_settings`)
- Device queries (`get_device_name`, `get_mac_name`)
- Theme switching (`switch_theme`)
- Database operations (`get_all_charging_history`, `get_detail_by_id`, `delete_history_by_id`)

**Event system** (`src-tauri/src/event.rs`): Tauri events are defined with `tauri_specta::Event` and emitted to frontend:
- `DeviceEvent` - iOS device connection/disconnection
- `DevicePowerTickEvent` - Power data from iOS devices
- `PowerTickEvent` - Power data from Mac
- `PowerUpdatedEvent` - Status bar text updates
- `HistoryRecordedEvent` - New charging history recorded

**Data flow**:
1. **Local Mac monitoring** (`src-tauri/src/local.rs`): Uses `tpower` to read SMC sensors, emits `PowerTickEvent`
2. **iOS device monitoring** (`src-tauri/src/device.rs`):
   - Subscribes to AMDevice notifications via `AMDeviceNotificationSubscribe`
   - Polls connected devices for IORegistry power data
   - Emits `DeviceEvent` and `DevicePowerTickEvent`
3. **History recording** (`src-tauri/src/history.rs`): Listens for power events, detects charging sessions, stores in SQLite
4. **Database** (`src-tauri/src/database.rs`): SQLx with SQLite for charging history

### tpower Crate

The `tpower` crate provides low-level power monitoring:
- **SMC (System Management Controller)**: Read power sensors via `IOKit` (`src/ffi/smc.rs`)
- **IORegistry parsing**: Read power information from IOKit registry (`src/provider/`)
- **AMDevice FFI**: Interact with connected iOS devices via MobileDevice framework (`src/ffi/mod.rs`, `src/ffi/wrapper.rs`)
- **Data structures**: `NormalizedResource` type provides unified power data from Mac and iOS devices

When adding features that require new sensor data, check `tpower::ffi::smc` for available SMC keys.

---

## Development Notes

**Type generation**: When adding Tauri commands or events, run the app in debug mode to regenerate `src/bindings.ts` automatically (see `lib.rs:147-154`).

**macOS APIs**: The app uses private macOS frameworks:
- MobileDevice.framework for iOS device communication (ships with Xcode at `/System/Library/PrivateFrameworks/MobileDevice.framework`)
- IOKit for SMC access (public framework)
- AppKit for native window appearance

**Window behavior**:
- Main window close is prevented (hides instead, see `lib.rs:214-231`)
- App runs as menu bar utility (ActivationPolicy::Accessory when hidden)
- Uses `tauri-plugin-positioner` for tray-relative positioning

**Styling**: TailwindCSS with custom UI components in `src/components/ui/` (based on radix-vue). Uses `class-variance-authority` for component variants.

**i18n**: Vue i18n configured via `@intlify/unplugin-vue-i18n`, locale files in `locales/`.

---

## Porting to Other Languages/Platforms

If you want to reimplement Powerflow in another language or for another platform:

### For macOS (other languages)

1. **SMC Access**: Use IOKit framework
   - Open "AppleSMC" service via `IOServiceOpen`
   - Call `IOConnectCallStructMethod` with index=2, commands 5 (read) and 9 (key info)
   - Parse fixed-point numbers according to data type string
   - Reference: Apple's IOKit documentation, or reverse-engineer from this codebase

2. **IORegistry**: Use `IORegistryEntryCreateCFProperties` on "AppleSmartBattery"
   - Returns CFDictionary with all properties
   - Parse into your data structures

3. **MobileDevice**: Link private framework (requires Xcode installed)
   - Subscribe to notifications for device events
   - Use diagnostics_relay service to query IORegistry from iOS devices
   - Handle pairing/session management

### For Other Platforms

- **Windows**: Use WMI (`Win32_Battery` class) or Battery Status API
  - No equivalent to SMC - power data is less detailed
  - Android devices: ADB protocol + `dumpsys battery`

- **Linux**: Read `/sys/class/power_supply/BAT*/` files
  - Properties: `energy_now`, `power_now`, `current_now`, etc.
  - Android devices: ADB or libmobiledevice (open-source MobileDevice alternative)

- **Cross-platform**: Battery API standardization is poor
  - Consider using Electron with native modules for each platform
  - Or Tauri with platform-specific Rust code (like this project)

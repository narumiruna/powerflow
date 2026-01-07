# powermonitor - Improvement Roadmap

This document outlines remaining improvements for the powermonitor project.

## Completed Issues

### 8. Missing TUI Tests ✅ COMPLETED

**Status**: Implemented in `tests/test_tui.py` with 5 comprehensive tests.

**Results**:
- TUI App coverage: 77% (was 0%)
- TUI Widgets coverage: 99% (was 0%)

**Tests Added**:
- `test_live_data_panel_update` - Verifies panel updates with power readings
- `test_stats_panel_empty` - Tests empty statistics display
- `test_stats_panel_with_data` - Tests populated statistics display
- `test_app_launches` - Validates app initialization and layout
- `test_app_refresh_action` - Tests refresh action functionality

### 9. Missing Logger Tests ✅ COMPLETED

**Status**: Implemented in `tests/test_logger.py` with 5 comprehensive tests.

**Results**:
- Logger coverage: 100% (was 0%)

**Tests Added**:
- `test_setup_logger_with_defaults` - Tests default configuration
- `test_setup_logger_debug_level` - Verifies DEBUG level logging
- `test_setup_logger_without_file` - Tests console-only mode
- `test_setup_logger_different_levels` - Tests all log levels
- `test_setup_logger_creates_directory` - Validates directory creation

### Summary

**Overall Project Coverage**: 86% ⬆️ (up from 83%)

**Major Improvements**:
- CLI commands: 80% (was 0%)
- Logger: 100% (was 0%)
- Config Loader: 93% (was 12%)
- Database: 92% (was 88%)
- IOKit Parser: 81% (was 19%)
- IORegCollector: 78% (was 70%)
- TUI App: 77% (was 0%)
- Factory: 75% (was 62%)
- TUI Widgets: 99% (was 0%)
- **IOKit Collector: 100% ⬆️ (was 57%)**
- **IOKit Bindings: 100%**
- **IOKit Structures: 100%**

**Benefits Achieved**:
- Catches regressions early across all major components
- Documents expected behavior
- Enables confident refactoring
- Professional-grade test coverage for production use

---

## Remaining Issues

None at this time. All critical and recommended improvements have been completed.

---

## Implementation Reference

**Previous Recommendation**: Add Textual unit tests using `textual.pilot` (if developing on macOS):

See `tests/test_tui.py` for the implemented test suite.

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

**Overall**: 86% coverage ⬆️ (significantly improved from 83%)

**Excellent coverage** (≥90%):
- ✅ **IOKit Collector: 100% ⬆️ (was 57%)**
- ✅ Logger: 100% ⬆️ (was 0%)
- ✅ Config: 100%
- ✅ IOKit Bindings: 100%
- ✅ IOKit Structures: 100%
- ✅ TUI Widgets: 99%
- ✅ Models: 94%
- ✅ Config Loader: 93% ⬆️ (was 12%)
- ✅ Database: 92% ⬆️ (was 88%)

**Good coverage** (70-89%):
- ✅ CLI: 80% ⬆️ (was 0%)
- ✅ IOKit Parser: 81% ⬆️ (was 19%)
- ✅ IORegCollector: 78% ⬆️ (was 70%)
- ✅ TUI App: 77%
- ✅ Factory: 75% ⬆️ (was 62%)
- ✅ Config: 89%

**Acceptable coverage** (50-69%):
- ✅ IOKit Connection: 70% ⬆️ (was 69%)

**Note**: IOKit Connection requires macOS hardware with SMC access for full coverage of actual IOKit API calls and cannot be fully tested in CI/CD environments. Additional tests have been added for:

**IOKit Connection Tests**:
- Error code name mapping (`_get_kern_return_name`)
- SMCError exception handling
- Input validation (invalid key lengths)

**IOKit Collector Tests** (NEW - 8 comprehensive tests):
- Fallback to IORegCollector on SMC errors
- Fallback on general exceptions
- Verbose mode logging during fallback
- `_collect_with_smc` method with power input enhancement
- `_collect_with_smc` method without power input
- Verbose logging of sensor data
- `_read_smc_sensors` with mocked SMC connection
- Handling missing/unavailable sensors gracefully
- IOKitCollector initialization and configuration
- SMCPowerData dataclass

Core SMC/IOKit interaction paths (connection opening, sensor reading) require physical macOS hardware and appropriate permissions. Current coverage levels are acceptable given these hardware constraints.

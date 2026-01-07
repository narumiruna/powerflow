# powermonitor - Improvement Roadmap

This document outlines remaining improvements for the powermonitor project.

## Completed Issues

### 8. Missing TUI Tests ✅ COMPLETED

**Status**: Implemented in `tests/test_tui.py` with 5 comprehensive tests.

**Results**:
- TUI App coverage: 77% (was 0%)
- TUI Widgets coverage: 99% (was 0%)
- Overall project coverage: 52% (was 19%)

**Tests Added**:
- `test_live_data_panel_update` - Verifies panel updates with power readings
- `test_stats_panel_empty` - Tests empty statistics display
- `test_stats_panel_with_data` - Tests populated statistics display
- `test_app_launches` - Validates app initialization and layout
- `test_app_refresh_action` - Tests refresh action functionality

**Benefits Achieved**:
- Catches UI regressions early
- Documents expected widget behavior
- Enables refactoring with confidence

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

**Overall**: 52% coverage (significantly improved from 19%)

**Excellent coverage** (>80%):
- ✅ Database: 88%
- ✅ Config: 100%
- ✅ Models: 94%
- ✅ TUI Widgets: 99%
- ✅ IOKit Structures: 91%

**Good coverage** (>70%):
- ✅ TUI App: 77%
- ✅ Config: 73%
- ✅ IORegCollector: 70%
- ✅ IOKit Connection: 69%

**Needs improvement** (<50%):
- ⚠️ CLI: 0% (210 lines) - Can test commands
- ⚠️ Logger: 0% (12 lines) - Easy to test
- ⚠️ IOKit Collector: 57%
- ⚠️ Config Loader: 12%
- ⚠️ IOKit Parser: 19%

**Note**: Many IOKit components require macOS hardware and cannot be tested in CI/CD. Focus should be on testing CLI commands and logger utilities.

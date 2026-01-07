# powermonitor - Improvement Roadmap

This document outlines potential improvements for the powermonitor project.

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

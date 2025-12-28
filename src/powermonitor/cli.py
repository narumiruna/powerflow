"""powermonitor CLI entry point - launches TUI by default."""

import sys

import typer
from loguru import logger

from .tui.app import PowerMonitorApp


def main() -> None:
    """Main entry point for powermonitor CLI.

    Directly launches the Textual TUI (no subcommands needed).
    """
    # Check platform
    if sys.platform != "darwin":
        logger.error("powermonitor only supports macOS")
        sys.exit(1)

    # Launch TUI
    try:
        PowerMonitorApp().run()
    except KeyboardInterrupt:
        logger.info("Exiting powermonitor...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    typer.run(main)

"""powermonitor CLI entry point - launches TUI by default."""

import sys
from typing import Annotated

import typer
from loguru import logger

from .tui.app import PowerMonitorApp

app = typer.Typer()


@app.command()
def main(
    interval: Annotated[
        float,
        typer.Option(
            "-i",
            "--interval",
            help="Data collection interval in seconds",
            show_default=True,
        ),
    ] = 1.0,
) -> None:
    """Main entry point for powermonitor CLI.

    Directly launches the Textual TUI (no subcommands needed).
    """
    # Check platform
    if sys.platform != "darwin":
        logger.error("powermonitor only supports macOS")
        sys.exit(1)

    # Launch TUI
    try:
        logger.info("Starting powermonitor TUI...")
        PowerMonitorApp(collection_interval=interval).run()
    except KeyboardInterrupt:
        logger.info("Exiting powermonitor...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

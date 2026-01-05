"""powermonitor CLI entry point - launches TUI by default."""

import sys
from typing import Annotated

import typer
from loguru import logger

from .config import PowerMonitorConfig
from .logger import setup_logger
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
    stats_limit: Annotated[
        int,
        typer.Option(
            "--stats-limit",
            help="Number of readings to include in statistics",
            show_default=True,
        ),
    ] = 100,
    chart_limit: Annotated[
        int,
        typer.Option(
            "--chart-limit",
            help="Number of readings to display in chart",
            show_default=True,
        ),
    ] = 60,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug logging",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Main entry point for powermonitor CLI.

    Directly launches the Textual TUI (no subcommands needed).
    """
    # Setup logging
    if debug:
        setup_logger(level="DEBUG")
    else:
        setup_logger(level="INFO")

    # Check platform
    if sys.platform != "darwin":
        logger.error("powermonitor only supports macOS")
        sys.exit(1)

    # Create configuration with validation
    try:
        config = PowerMonitorConfig(
            collection_interval=interval,
            stats_history_limit=stats_limit,
            chart_history_limit=chart_limit,
        )
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    # Launch TUI
    try:
        logger.info("Starting powermonitor TUI...")
        PowerMonitorApp(config=config).run()
    except KeyboardInterrupt:
        logger.info("Exiting powermonitor...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

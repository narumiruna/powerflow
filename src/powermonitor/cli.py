"""powermonitor CLI entry point - launches TUI by default."""

import csv
import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from .config import PowerMonitorConfig
from .config_loader import load_config
from .database import Database
from .logger import setup_logger
from .tui.app import PowerMonitorApp

app = typer.Typer(
    help="macOS power monitoring tool with TUI and data export",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    interval: Annotated[
        float | None,
        typer.Option(
            "-i",
            "--interval",
            help="Data collection interval in seconds (overrides config file)",
        ),
    ] = None,
    stats_limit: Annotated[
        int | None,
        typer.Option(
            "--stats-limit",
            help="Number of readings to include in statistics (overrides config file)",
        ),
    ] = None,
    chart_limit: Annotated[
        int | None,
        typer.Option(
            "--chart-limit",
            help="Number of readings to display in chart (overrides config file)",
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug logging (overrides config file)",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Main entry point for powermonitor CLI.

    Directly launches the Textual TUI when no subcommand is provided.

    Configuration priority: CLI arguments > Config file (~/.powermonitor/config.toml) > Defaults
    """
    # If a subcommand was invoked, do not run the TUI here.
    if ctx.invoked_subcommand is not None:
        return

    # Load configuration from file (or use defaults)
    base_config = load_config()

    # Build merged config with CLI overrides
    # Create new instance to avoid mutating the loaded config
    try:
        config = PowerMonitorConfig(
            collection_interval=interval if interval is not None else base_config.collection_interval,
            stats_history_limit=stats_limit if stats_limit is not None else base_config.stats_history_limit,
            chart_history_limit=chart_limit if chart_limit is not None else base_config.chart_history_limit,
            database_path=base_config.database_path,
            default_history_limit=base_config.default_history_limit,
            default_export_limit=base_config.default_export_limit,
            log_level="DEBUG" if debug else base_config.log_level,
        )
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    # Setup logging with config level
    setup_logger(level=config.log_level)

    # Check platform
    if sys.platform != "darwin":
        logger.error("powermonitor only supports macOS")
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


@app.command()
def export(
    output: Annotated[
        Path,
        typer.Argument(help="Output file path (CSV or JSON based on extension)"),
    ],
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Maximum number of readings to export (None = all)"),
    ] = None,
    format_type: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help="Output format: csv or json (auto-detected from extension if not specified)",
        ),
    ] = None,
) -> None:
    """Export power readings to CSV or JSON file.

    Uses config file for database path and default export limit.

    Examples:
        powermonitor export data.csv
        powermonitor export data.json --limit 1000
        powermonitor export backup.csv --format csv
    """
    # Load config for database path and defaults
    config = load_config()
    setup_logger(level=config.log_level)

    # Detect format from extension if not specified
    if format_type is None:
        ext = output.suffix.lower()
        if ext == ".csv":
            format_type = "csv"
        elif ext == ".json":
            format_type = "json"
        else:
            console.print(
                f"[red]Error: Cannot detect format from extension '{ext}'. Use --format csv or --format json[/red]"
            )
            sys.exit(1)

    # Validate format
    if format_type not in ["csv", "json"]:
        console.print(f"[red]Error: Invalid format '{format_type}'. Must be 'csv' or 'json'[/red]")
        sys.exit(1)

    try:
        # Get database using config path
        with Database(config.database_path) as db:
            # Determine effective limit: CLI overrides config default
            if limit is None:
                limit = config.default_export_limit
            # Query readings
            console.print("[cyan]Querying database...[/cyan]")
            readings = db.query_history(limit=limit)

            if not readings:
                console.print("[yellow]No readings found in database[/yellow]")
                sys.exit(0)

            # Export based on format
            if format_type == "csv":
                _export_csv(output, readings)
            else:
                _export_json(output, readings)

            console.print(f"[green]✓ Exported {len(readings)} readings to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Export failed")
        sys.exit(1)


def _export_csv(output_path: Path, readings: list) -> None:
    """Export readings to CSV file."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(
            [
                "timestamp",
                "watts_actual",
                "watts_negotiated",
                "voltage",
                "amperage",
                "current_capacity",
                "max_capacity",
                "battery_percent",
                "is_charging",
                "external_connected",
                "charger_name",
                "charger_manufacturer",
            ]
        )

        # Data
        for r in readings:
            writer.writerow(
                [
                    r.timestamp.isoformat(),
                    r.watts_actual,
                    r.watts_negotiated,
                    r.voltage,
                    r.amperage,
                    r.current_capacity,
                    r.max_capacity,
                    r.battery_percent,
                    r.is_charging,
                    r.external_connected,
                    r.charger_name or "",
                    r.charger_manufacturer or "",
                ]
            )


def _export_json(output_path: Path, readings: list) -> None:
    """Export readings to JSON file."""
    data = [
        {
            "timestamp": r.timestamp.isoformat(),
            "watts_actual": r.watts_actual,
            "watts_negotiated": r.watts_negotiated,
            "voltage": r.voltage,
            "amperage": r.amperage,
            "current_capacity": r.current_capacity,
            "max_capacity": r.max_capacity,
            "battery_percent": r.battery_percent,
            "is_charging": r.is_charging,
            "external_connected": r.external_connected,
            "charger_name": r.charger_name,
            "charger_manufacturer": r.charger_manufacturer,
        }
        for r in readings
    ]

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


@app.command()
def stats() -> None:
    """Show database statistics.

    Uses config file for database path.

    Displays information about stored readings including:
    - Total number of readings
    - Date range (earliest to latest)
    - Database file size

    Examples:
        powermonitor stats
    """
    # Load config for database path
    config = load_config()
    setup_logger(level=config.log_level)

    try:
        db_path = Path(config.database_path)

        # Get database file size
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
        else:
            console.print("[yellow]Database file does not exist yet[/yellow]")
            sys.exit(0)

        with Database(db_path) as db:
            # Get statistics
            stat_data = db.get_statistics(limit=None)  # Get all readings for stats

            if stat_data["count"] == 0:
                console.print("[yellow]No readings in database[/yellow]")
                sys.exit(0)

            # Display statistics
            table = Table(title="Database Statistics", show_header=False)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Total readings", f"{stat_data['count']:,}")
            table.add_row("Earliest reading", stat_data["earliest"] or "N/A")
            table.add_row("Latest reading", stat_data["latest"] or "N/A")
            table.add_row("Database size", f"{size_mb:.2f} MB")
            table.add_row("Database path", str(db_path))

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Stats command failed")
        sys.exit(1)


@app.command()
def cleanup(
    days: Annotated[
        int | None,
        typer.Option("--days", "-d", help="Delete readings older than N days"),
    ] = None,
    all_data: Annotated[
        bool,
        typer.Option("--all", help="Delete ALL readings (requires confirmation)"),
    ] = False,
) -> None:
    """Clean up old power readings from database.

    Uses config file for database path.

    Examples:
        powermonitor cleanup --days 30
        powermonitor cleanup --all
    """
    # Load config for database path
    config = load_config()
    setup_logger(level=config.log_level)

    if not days and not all_data:
        console.print("[red]Error: Must specify either --days N or --all[/red]")
        console.print("Use --help for usage information")
        sys.exit(1)

    try:
        with Database(config.database_path) as db:
            if all_data:
                # Confirm deletion of all data
                console.print("[yellow]⚠️  WARNING: This will delete ALL readings![/yellow]")
                confirm = typer.confirm("Are you sure you want to continue?")
                if not confirm:
                    console.print("[cyan]Operation cancelled[/cyan]")
                    sys.exit(0)

                deleted = db.clear_history()
                console.print(f"[green]✓ Deleted all {deleted} readings[/green]")

            else:
                # Delete old data
                assert days is not None, "days must be specified"  # Type checker hint
                console.print(f"[cyan]Deleting readings older than {days} days...[/cyan]")

                deleted = db.cleanup_old_data(days=days)
                console.print(f"[green]✓ Deleted {deleted} old readings[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Cleanup failed")
        sys.exit(1)


@app.command()
def history(
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Number of recent readings to show (uses config default if not specified)"),
    ] = None,
) -> None:
    """Show recent power readings from database.

    Uses config file for database path and default limit.

    Examples:
        powermonitor history
        powermonitor history --limit 50
    """
    # Load config for database path and defaults
    config = load_config()
    setup_logger(level=config.log_level)

    # Use config default if limit not specified
    if limit is None:
        limit = config.default_history_limit

    try:
        with Database(config.database_path) as db:
            readings = db.query_history(limit=limit)

            if not readings:
                console.print("[yellow]No readings in database[/yellow]")
                sys.exit(0)

            # Create table
            table = Table(title=f"Recent Power Readings (Last {len(readings)})")
            table.add_column("Time", style="cyan")
            table.add_column("Power", style="green", justify="right")
            table.add_column("Battery", style="yellow", justify="right")
            table.add_column("Voltage", style="blue", justify="right")
            table.add_column("Current", style="magenta", justify="right")
            table.add_column("Status", style="white")

            # Reverse to show oldest first
            for r in reversed(readings):
                # Format status
                if r.is_charging:
                    status = "⚡ Charging"
                elif r.external_connected:
                    status = "🔌 AC Power"
                else:
                    status = "🔋 Battery"

                # Format time (show only time if today, otherwise date + time)
                time_str = r.timestamp.strftime("%H:%M:%S")

                table.add_row(
                    time_str,
                    f"{r.watts_actual:+.1f}W",
                    f"{r.battery_percent}%",
                    f"{r.voltage:.1f}V",
                    f"{r.amperage:+.2f}A",
                    status,
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("History command failed")
        sys.exit(1)


@app.command()
def health(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to analyze"),
    ] = 30,
) -> None:
    """Show battery health trend over time.

    Uses config file for database path.

    Analyzes max_capacity changes to detect battery degradation.

    Examples:
        powermonitor health
        powermonitor health --days 60
    """
    # Load config for database path
    config = load_config()
    setup_logger(level=config.log_level)

    try:
        with Database(config.database_path) as db:
            results = db.get_battery_health_trend(days=days)

            if not results:
                console.print(f"[yellow]No readings found in the last {days} days[/yellow]")
                sys.exit(0)

            # Calculate trend
            first_capacity = results[0][1]
            last_capacity = results[-1][1]
            change_mah = last_capacity - first_capacity
            change_percent = (change_mah / first_capacity) * 100

            # Determine status
            if change_percent < -2:
                status = "[red]⚠️  Degrading (significant)[/red]"
            elif change_percent < -0.5:
                status = "[yellow]⚠️  Degrading (normal wear)[/yellow]"
            else:
                status = "[green]✓ Stable[/green]"

            # Display summary
            console.print(f"\n[bold]Battery Health Analysis ({days} days)[/bold]\n")

            summary_table = Table(show_header=False, box=None)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="white")

            summary_table.add_row("First reading", results[0][0])
            summary_table.add_row("First avg capacity", f"{first_capacity:.0f} mAh")
            summary_table.add_row("Last reading", results[-1][0])
            summary_table.add_row("Last avg capacity", f"{last_capacity:.0f} mAh")
            summary_table.add_row("Change", f"{change_mah:+.0f} mAh ({change_percent:+.2f}%)")
            summary_table.add_row("Status", status)
            summary_table.add_row("Days analyzed", str(len(results)))

            console.print(summary_table)

            # Show daily trend if more than 3 data points
            if len(results) > 3:
                console.print(f"\n[bold]Daily Trend (Last {min(7, len(results))} days)[/bold]\n")

                trend_table = Table()
                trend_table.add_column("Date", style="cyan")
                trend_table.add_column("Avg Capacity", style="green", justify="right")
                trend_table.add_column("Readings", style="yellow", justify="right")

                # Show last 7 days
                for row in results[-7:]:
                    trend_table.add_row(row[0], f"{row[1]:.0f} mAh", str(row[2]))

                console.print(trend_table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Health command failed")
        sys.exit(1)

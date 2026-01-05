"""Reactive widgets for powermonitor TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual_plotext import PlotextPlot

from ..models import PowerReading


class LiveDataPanel(Static):
    """Real-time power data display panel.

    Shows current power, voltage, amperage, battery %, and charging status.
    Updates reactively when new PowerReading is received.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_reading: PowerReading | None = None

    def update_reading(self, reading: PowerReading) -> None:
        """Update panel with new power reading.

        Args:
            reading: Latest PowerReading
        """
        self.current_reading = reading
        self.update(self._render_reading())

    def _render_reading(self) -> str:
        """Render current reading as formatted text.

        Returns:
            Formatted string with power data
        """
        if self.current_reading is None:
            return "[dim]Waiting for data...[/dim]"

        r = self.current_reading

        # Status emoji and color
        if r.is_charging:
            status = "[green]⚡ Charging[/green]"
        elif r.external_connected:
            status = "[yellow]🔌 On AC Power (Not Charging)[/yellow]"
        else:
            status = "[red]🔋 On Battery[/red]"

        # Format power display
        if r.watts_negotiated > 0:
            power_display = f"{r.watts_actual:.1f}W / {r.watts_negotiated}W max"
        else:
            power_display = f"{r.watts_actual:.1f}W"

        # Build output
        lines = [
            f"{status}",
            f"   Power: {power_display}",
            f"   Battery: {r.battery_percent}% ({r.current_capacity} mAh / {r.max_capacity} mAh)",
            f"   Electrical: {r.voltage:.2f}V × {r.amperage:.2f}A",
        ]

        # Optional charger info
        if r.charger_name:
            charger_display = r.charger_name
            if r.charger_manufacturer:
                charger_display += f" ({r.charger_manufacturer})"
            lines.append(f"   Charger: {charger_display}")

        # Timestamp
        lines.append(f"   Time: {r.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def on_mount(self) -> None:
        """Initialize panel on mount."""
        self.update(self._render_reading())


class StatsPanel(Static):
    """Historical statistics panel.

    Displays avg/min/max power and battery statistics from recent readings.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stats: dict | None = None

    def update_stats(self, stats: dict) -> None:
        """Update panel with new statistics.

        Args:
            stats: Statistics dictionary from database.get_statistics()
        """
        self.stats = stats
        self.update(self._render_stats())

    def _render_stats(self) -> str:
        """Render statistics as formatted text.

        Returns:
            Formatted string with statistics
        """
        if self.stats is None or self.stats.get("count", 0) == 0:
            return "[dim]No historical data available[/dim]"

        s = self.stats

        lines = [
            f"[bold cyan]Statistics (Last {s['count']} readings)[/bold cyan]",
            f"   Latest: {s['latest'][:16] if s['latest'] else 'N/A'}",
            f"   Earliest: {s['earliest'][:16] if s['earliest'] else 'N/A'}",
            f"   Avg Power: {s['avg_watts']:.1f}W",
            f"   Max Power: {s['max_watts']:.1f}W",
            f"   Min Power: {s['min_watts']:.1f}W",
            f"   Avg Battery: {s['avg_battery']:.1f}%",
        ]

        return "\n".join(lines)

    def on_mount(self) -> None:
        """Initialize panel on mount."""
        self.update(self._render_stats())


class ChartWidget(Container):
    """Power chart widget using textual-plotext.

    Displays a line chart of power over time (last N readings).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.readings: list[PowerReading] = []

    def compose(self) -> ComposeResult:
        """Compose the chart widget."""
        yield PlotextPlot()

    def update_chart(self, readings: list[PowerReading]) -> None:
        """Update chart with new readings.

        Args:
            readings: List of PowerReading objects (newest first)
        """
        self.readings = readings
        self._render_chart()

    def _render_chart(self) -> None:
        """Render the power chart using plotext."""
        if len(self.readings) == 0:
            return

        plot = self.query_one(PlotextPlot)
        plot.plt.clear_data()
        plot.plt.clear_figure()

        # Prepare data (reverse to show oldest→newest)
        readings_reversed = list(reversed(self.readings))
        x = list(range(len(readings_reversed)))
        watts = [r.watts_actual for r in readings_reversed]
        max_watts = [float(r.watts_negotiated) for r in readings_reversed]

        # Plot lines
        plot.plt.plot(x, watts, label="Power (W)", color="red")
        plot.plt.plot(x, max_watts, label="Max Power (W)", color="blue")

        # Configure chart with dynamic title based on actual readings count
        reading_count = len(self.readings)
        plot.plt.title(f"Power Over Time (Last {reading_count} readings)")
        plot.plt.xlabel("Time (Oldest → Newest)")
        plot.plt.ylabel("Power (W)")

        # Show legend if there's data
        if len(x) > 0:
            plot.plt.theme("pro")

        plot.refresh()

    def on_mount(self) -> None:
        """Initialize chart on mount."""
        self._render_chart()

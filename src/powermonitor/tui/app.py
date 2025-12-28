"""powermonitor Textual TUI Application - auto-updating power monitoring interface."""

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Header, Footer

from ..collector import default_collector
from ..database import Database, DB_PATH
from ..models import PowerReading
from .widgets import LiveDataPanel, StatsPanel, ChartWidget


class powermonitorApp(App):
    """powermonitor TUI application with auto-updating power data.

    Features:
    - Real-time power monitoring (updates every 2s)
    - Historical statistics and trends
    - Interactive chart showing power over time
    - Automatic data persistence to SQLite
    """

    CSS = """
    Screen {
        background: $surface;
    }

    #live-data {
        height: 8;
        border: solid green;
        padding: 1;
        margin: 1;
    }

    #stats {
        height: 10;
        border: solid cyan;
        padding: 1;
        margin: 1;
    }

    #chart {
        height: 20;
        border: solid blue;
        padding: 1;
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="Q"),
        Binding("r", "refresh", "Refresh", key_display="R"),
        Binding("escape", "quit", "Quit", show=False),
        Binding("c", "clear_history", "Clear History", key_display="C"),
    ]

    TITLE = "powermonitor - macOS Power Monitoring"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collector = default_collector()
        self.database = Database(DB_PATH)
        self.collection_interval = 2.0  # seconds
        self._collector_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """Compose the TUI layout.

        3-panel layout:
        - LiveDataPanel: Real-time power data
        - StatsPanel: Historical statistics
        - ChartWidget: Power over time chart
        """
        yield Header()
        yield Vertical(
            LiveDataPanel(id="live-data"),
            StatsPanel(id="stats"),
            ChartWidget(id="chart"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Start background data collection when app mounts."""
        # Start periodic data collection
        self._collector_task = asyncio.create_task(self._collection_loop())

        # Initial data load
        self.refresh_all_data()

    async def on_unmount(self) -> None:
        """Clean up when app unmounts."""
        if self._collector_task:
            self._collector_task.cancel()
            try:
                await self._collector_task
            except asyncio.CancelledError:
                pass

    async def _collection_loop(self) -> None:
        """Background loop for periodic power data collection.

        Runs every collection_interval seconds, collecting data and updating UI.
        """
        while True:
            try:
                await asyncio.sleep(self.collection_interval)
                await self._collect_and_update()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.notify(f"Collection error: {e}", severity="error", timeout=5)

    async def _collect_and_update(self) -> None:
        """Collect power data and update all widgets.

        Runs in executor to avoid blocking the UI thread.
        """
        try:
            # Run blocking collector in executor
            loop = asyncio.get_event_loop()
            reading = await loop.run_in_executor(None, self.collector.collect)

            # Save to database (also blocking, run in executor)
            await loop.run_in_executor(None, self.database.insert_reading, reading)

            # Update all widgets (already on main thread after await)
            self._update_all_widgets(reading)

        except Exception as e:
            self.notify(f"Failed to collect data: {e}", severity="error", timeout=5)

    def _update_all_widgets(self, reading: PowerReading) -> None:
        """Update all widgets with new data.

        Args:
            reading: Latest PowerReading
        """
        # Update live data panel
        live_panel = self.query_one("#live-data", LiveDataPanel)
        live_panel.update_reading(reading)

        # Update statistics panel
        stats = self.database.get_statistics(limit=100)
        stats_panel = self.query_one("#stats", StatsPanel)
        stats_panel.update_stats(stats)

        # Update chart with last 60 readings
        history = self.database.query_history(limit=60)
        chart = self.query_one("#chart", ChartWidget)
        chart.update_chart(history)

    def refresh_all_data(self) -> None:
        """Force refresh all data (for 'r' key binding)."""
        try:
            reading = self.collector.collect()
            self.database.insert_reading(reading)
            self._update_all_widgets(reading)
            self.notify("Data refreshed", timeout=2)
        except Exception as e:
            self.notify(f"Refresh failed: {e}", severity="error", timeout=5)

    def action_refresh(self) -> None:
        """Handle refresh key binding (R)."""
        self.run_worker(self._async_refresh, exclusive=True)

    async def _async_refresh(self) -> None:
        """Async refresh worker."""
        await self._collect_and_update()
        self.notify("Data refreshed", timeout=2)

    def action_clear_history(self) -> None:
        """Handle clear history key binding (C).

        Clears all historical readings from database.
        """
        rows_deleted = self.database.clear_history()
        self.notify(f"Cleared {rows_deleted} historical readings", timeout=3)
        # Refresh display
        self.refresh_all_data()

    async def action_quit(self) -> None:
        """Handle quit action (Q or ESC)."""
        self.exit()


def run_app() -> None:
    """Run the powermonitor TUI app."""
    app = powermonitorApp()
    app.run()


if __name__ == "__main__":
    run_app()

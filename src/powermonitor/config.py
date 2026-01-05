from dataclasses import dataclass


@dataclass
class PowerMonitorConfig:
    collection_interval: float = 1.0  # seconds
    stats_history_limit: int = 100  # number of readings for statistics
    chart_history_limit: int = 60  # number of readings to display in chart

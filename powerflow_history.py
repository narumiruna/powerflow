import sqlite3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import sys
import os

DB_PATH = "./powerflow.db"
LIMIT = 20

def fetch_history(limit=LIMIT):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, watts_actual, watts_negotiated, voltage, amperage, battery_percent, is_charging, external_connected
        FROM power_readings
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def stats_block(rows):
    if not rows:
        return "No history data available."
    times = [r[0] for r in rows]
    watts = [r[1] for r in rows]
    battery = [r[5] for r in rows]
    min_time = min(times)
    max_time = max(times)
    avg_watt = sum(watts) / len(watts)
    min_watt = min(watts)
    max_watt = max(watts)
    avg_percent = sum(battery) / len(battery)
    return f"""[bold cyan]
最新: {max_time}
最舊: {min_time}
平均功率: {avg_watt:.1f}W
最大功率: {max_watt:.1f}W
最小功率: {min_watt:.1f}W
平均電池: {avg_percent:.1f}%
[/bold cyan]"""

def table_block(rows):
    table = Table(title="最近記錄", box=box.SIMPLE)
    table.add_column("時間", style="yellow")
    table.add_column("功率")
    table.add_column("協商功率")
    table.add_column("電壓")
    table.add_column("電流")
    table.add_column("電池")
    table.add_column("狀態")
    for r in rows[:10]:
        status = "充電" if r[6] else ("外接" if r[7] else "電池")
        table.add_row(
            r[0][:16],
            f"{r[1]:.1f}",
            str(r[2]),
            f"{r[3]:.2f}",
            f"{r[4]:.2f}",
            f"{r[5]}%",
            status
        )
    return table

# chart_block removed (no chart output)

def main():
    limit = LIMIT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])
    rows = fetch_history(limit)
    console = Console()
    console.print(Panel(stats_block(rows), title="統計資訊", border_style="cyan"))
    console.print(table_block(rows))
    # chart_block removed

if __name__ == "__main__":
    main()

from rich.table import Table
from rich import box


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
            status,
        )
    return table

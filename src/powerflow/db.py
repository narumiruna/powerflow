import sqlite3

DB_PATH = "./powerflow.db"

def fetch_history(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, watts_actual, watts_negotiated, voltage, amperage, battery_percent, is_charging
        FROM power_readings
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

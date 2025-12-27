use rusqlite::{Connection, params, Result};
use chrono::{DateTime, Utc};
use powerflow_core::PowerReading;

pub fn init_db(db_path: &str) -> Result<Connection> {
    let conn = Connection::open(db_path)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS power_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            watts_actual REAL NOT NULL,
            watts_negotiated INTEGER NOT NULL,
            voltage REAL NOT NULL,
            amperage REAL NOT NULL,
            battery_percent INTEGER NOT NULL,
            is_charging INTEGER NOT NULL,
            charger_name TEXT
        )",
        [],
    )?;
    Ok(conn)
}

pub fn insert_reading(conn: &Connection, reading: &PowerReading) -> Result<()> {
    conn.execute(
        "INSERT INTO power_readings (
            timestamp, watts_actual, watts_negotiated, voltage, amperage,
            battery_percent, is_charging, charger_name
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            reading.timestamp.to_rfc3339(),
            reading.watts_actual,
            reading.watts_negotiated,
            reading.voltage,
            reading.amperage,
            reading.battery_percent,
            reading.is_charging as i32,
            reading.charger_name.clone()
        ],
    )?;
    Ok(())
}

pub fn query_history(conn: &Connection, limit: usize) -> Result<Vec<PowerReading>> {
    let mut stmt = conn.prepare(
        "SELECT timestamp, watts_actual, watts_negotiated, voltage, amperage, battery_percent, is_charging, charger_name
         FROM power_readings
         ORDER BY timestamp DESC
         LIMIT ?1"
    )?;
    let rows = stmt.query_map(params![limit as i64], |row| {
        Ok(PowerReading {
            timestamp: DateTime::parse_from_rfc3339(row.get::<_, String>(0)?.as_str())
                .map(|dt| dt.with_timezone(&Utc)).unwrap(),
            watts_actual: row.get(1)?,
            watts_negotiated: row.get(2)?,
            voltage: row.get(3)?,
            amperage: row.get(4)?,
            current_capacity: 0,
            max_capacity: 0,
            battery_percent: row.get(5)?,
            is_charging: row.get::<_, i32>(6)? != 0,
            external_connected: false,
            charger_name: row.get(7)?,
            charger_manufacturer: None,
        })
    })?;
    let mut readings = Vec::new();
    for reading in rows {
        readings.push(reading?);
    }
    Ok(readings)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use powerflow_core::PowerReading;
    use chrono::Utc;

    fn sample_reading() -> PowerReading {
        PowerReading {
            timestamp: Utc::now(),
            watts_actual: 45.2,
            watts_negotiated: 67,
            voltage: 20.0,
            amperage: 2.26,
            current_capacity: 0,
            max_capacity: 0,
            battery_percent: 72,
            is_charging: true,
            external_connected: true,
            charger_name: Some("Apple 67W USB-C Power Adapter".to_string()),
            charger_manufacturer: None,
        }
    }

    #[test]
    fn test_db_insert_and_query() {
        let tmpfile = NamedTempFile::new().unwrap();
        let db_path = tmpfile.path().to_str().unwrap();
        let conn = init_db(db_path).unwrap();

        let reading = sample_reading();
        insert_reading(&conn, &reading).unwrap();

        let results = query_history(&conn, 10).unwrap();
        assert!(!results.is_empty());
        let r = &results[0];
        assert_eq!(r.watts_actual, 45.2);
        assert_eq!(r.watts_negotiated, 67);
        assert_eq!(r.battery_percent, 72);
        assert_eq!(r.charger_name.as_deref(), Some("Apple 67W USB-C Power Adapter"));
    }
}

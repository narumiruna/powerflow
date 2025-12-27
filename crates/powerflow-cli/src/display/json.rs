use anyhow::Result;
use powerflow_core::PowerReading;

/// Print reading as pretty JSON
pub fn print_reading(reading: &PowerReading) -> Result<()> {
    let json = serde_json::to_string_pretty(reading)?;
    println!("{}", json);
    Ok(())
}

/// Print multiple readings as pretty JSON array
pub fn print_readings(readings: &[PowerReading]) -> Result<()> {
    let json = serde_json::to_string_pretty(readings)?;
    println!("{}", json);
    Ok(())
}

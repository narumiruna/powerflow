use anyhow::Result;
use powerflow_core::PowerReading;

/// Print reading as pretty JSON
pub fn print_reading(reading: &PowerReading) -> Result<()> {
    let json = serde_json::to_string_pretty(reading)?;
    println!("{}", json);
    Ok(())
}

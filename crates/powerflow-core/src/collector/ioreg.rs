use crate::{
    collector::PowerCollector, models::IORegBattery, PowerError, PowerReading, PowerResult,
};
use chrono::Utc;
use std::process::Command;

/// Power collector that parses ioreg command output
pub struct IORegCollector;

impl IORegCollector {
    /// Execute ioreg command and return output
    fn execute_ioreg() -> PowerResult<String> {
        let output = Command::new("ioreg")
            .args(["-rw0", "-c", "AppleSmartBattery", "-a"])
            .output()
            .map_err(|e| PowerError::CommandFailed(format!("ioreg execution failed: {}", e)))?;

        if !output.status.success() {
            return Err(PowerError::CommandFailed(
                "ioreg exited with non-zero status".to_string(),
            ));
        }

        String::from_utf8(output.stdout)
            .map_err(|e| PowerError::ParseError(format!("Invalid UTF-8 in ioreg output: {}", e)))
    }

    /// Parse ioreg plist output into PowerReading
    pub fn parse_output(plist_data: &str) -> PowerResult<PowerReading> {
        // Parse the plist XML
        let value: plist::Value = plist::from_bytes(plist_data.as_bytes())?;

        // ioreg returns an array with one dict containing battery info
        let array = value
            .as_array()
            .ok_or_else(|| PowerError::ParseError("Expected array at root".to_string()))?;

        let battery_dict = array
            .first()
            .ok_or_else(|| PowerError::ParseError("Empty array from ioreg".to_string()))?
            .as_dictionary()
            .ok_or_else(|| PowerError::ParseError("Expected dictionary in array".to_string()))?;

        // Convert to Value then deserialize to our struct
        let battery_value = plist::Value::Dictionary(battery_dict.clone());
        let battery: IORegBattery = plist::from_value(&battery_value)?;

        // Convert to PowerReading
        Self::convert_to_reading(battery)
    }

    /// Convert IORegBattery to PowerReading
    fn convert_to_reading(battery: IORegBattery) -> PowerResult<PowerReading> {
        // Extract voltage and amperage, convert from mV/mA to V/A
        let voltage_mv = battery
            .voltage
            .ok_or(PowerError::MissingField("Voltage"))?;
        let amperage_ma = battery
            .amperage
            .ok_or(PowerError::MissingField("Amperage"))?;

        let voltage = voltage_mv as f64 / 1000.0; // mV to V
        let amperage = amperage_ma as f64 / 1000.0; // mA to A

        // Calculate actual wattage (V * A)
        let watts_actual = voltage * amperage;

        // Get negotiated wattage from adapter details
        let (watts_negotiated, charger_name, charger_manufacturer) =
            if let Some(ref details) = battery.adapter_details {
                if let Some(adapter) = details.first() {
                    // Prefer Name over Description
                    let name = adapter
                        .name
                        .clone()
                        .or_else(|| adapter.description.clone());
                    (
                        adapter.watts.unwrap_or(0),
                        name,
                        adapter.manufacturer.clone(),
                    )
                } else {
                    (0, None, None)
                }
            } else {
                (0, None, None)
            };

        // Get battery capacities - prefer raw values (mAh) over percentage-based ones
        let current_capacity = battery
            .raw_current_capacity
            .or(battery.current_capacity)
            .ok_or(PowerError::MissingField("CurrentCapacity"))?;

        let max_capacity = battery
            .raw_max_capacity
            .or(battery.max_capacity)
            .ok_or(PowerError::MissingField("MaxCapacity"))?;

        // Calculate battery percentage
        let battery_percent = if max_capacity > 0 {
            ((current_capacity as f64 / max_capacity as f64) * 100.0).round() as i32
        } else {
            0
        };

        // Get charging status
        let is_charging = battery.is_charging.unwrap_or(false);
        let external_connected = battery.external_connected.unwrap_or(false);

        Ok(PowerReading {
            timestamp: Utc::now(),
            watts_actual,
            watts_negotiated,
            voltage,
            amperage,
            current_capacity,
            max_capacity,
            battery_percent,
            is_charging,
            external_connected,
            charger_name,
            charger_manufacturer,
        })
    }
}

impl PowerCollector for IORegCollector {
    fn collect(&self) -> PowerResult<PowerReading> {
        let output = Self::execute_ioreg()?;
        Self::parse_output(&output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_real_mac_output() {
        let fixture = include_str!("../../../../tests/fixtures/real_mac.txt");
        let reading = IORegCollector::parse_output(fixture).unwrap();

        // Verify the data makes sense
        assert!(reading.battery_percent >= 0 && reading.battery_percent <= 100);
        assert!(reading.voltage > 0.0);
        assert!(reading.current_capacity > 0);
        assert!(reading.max_capacity > 0);

        println!("Parsed reading: {:#?}", reading);
    }

    #[test]
    fn test_calculate_watts() {
        let voltage = 20.0; // V
        let amperage = 2.5; // A
        let watts = PowerReading::calculate_watts(voltage, amperage);
        assert_eq!(watts, 50.0); // 20V * 2.5A = 50W
    }
}

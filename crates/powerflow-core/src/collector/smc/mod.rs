//! SMC (System Management Controller) access for Mac power sensors
//!
//! This module provides low-level access to Mac SMC sensors for accurate
//! power, temperature, and battery readings.

use crate::PowerResult;

#[cfg(feature = "iokit")]
mod connection;
#[cfg(feature = "iokit")]
mod ffi;
#[cfg(feature = "iokit")]
pub use connection::SMCConnection;

#[cfg(feature = "iokit")]
/// SMC sensor keys for power monitoring
pub const SMC_SENSORS: &[&str] = &[
    "PPBR", // Battery power rate (W) - positive when discharging
    "PDTR", // Power delivery/input rate (W)
    "PSTR", // System total power consumption (W)
    "PHPC", // Heatpipe/cooling power (W)
    "PDBR", // Display brightness power (W)
    "TB0T", // Battery temperature (°C)
    "CHCC", // Charging status
];

#[cfg(feature = "iokit")]
/// SMC power sensor data
#[derive(Debug, Clone, Default)]
pub struct SMCPowerData {
    /// Battery power rate (W) - positive when discharging
    pub battery_power: Option<f32>,
    /// Power delivery/input rate (W)
    pub power_input: Option<f32>,
    /// System total power consumption (W)
    pub system_power: Option<f32>,
    /// Heatpipe/cooling power (W)
    pub heatpipe_power: Option<f32>,
    /// Display brightness power (W)
    pub display_power: Option<f32>,
    /// Battery temperature (°C)
    pub battery_temp: Option<f32>,
    /// Charging status (0 = not charging)
    pub charging_status: Option<f32>,
}

#[cfg(feature = "iokit")]
impl SMCPowerData {
    /// Read all power sensors from SMC
    pub fn read() -> PowerResult<Self> {
        let mut conn = SMCConnection::new()?;
        // Try to read each sensor, but don't fail if some are missing
        Ok(SMCPowerData {
            battery_power: conn.read_key("PPBR").ok(),
            power_input: conn.read_key("PDTR").ok(),
            system_power: conn.read_key("PSTR").ok(),
            heatpipe_power: conn.read_key("PHPC").ok(),
            display_power: conn.read_key("PDBR").ok(),
            battery_temp: conn.read_key("TB0T").ok(),
            charging_status: conn.read_key("CHCC").ok(),
        })
    }
}

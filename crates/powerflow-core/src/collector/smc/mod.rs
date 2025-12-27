 //! SMC (System Management Controller) access for Mac power sensors
//!
//! This module provides low-level access to Mac SMC sensors for accurate
//! power, temperature, and battery readings.

use crate::PowerResult;

#[cfg(feature = "iokit")]
mod ffi;

#[cfg(feature = "iokit")]
mod connection;

#[cfg(feature = "iokit")]
pub use connection::SMCConnection;

#[cfg(feature = "iokit")]

/// SMC sensor keys for power monitoring
#[cfg(feature = "iokit")]
pub const SMC_SENSORS: &[&str] = &[
    "PPBR", // Battery power rate (W) - positive when discharging
    "PDTR", // Power delivery/input rate (W)
    "PSTR", // System total power consumption (W)
    "PHPC", // Heatpipe/cooling power (W)
    "PDBR", // Display brightness power (W)
    "TB0T", // Battery temperature (°C)
    "CHCC", // Charging status
];

/// SMC power sensor data
#[cfg(feature = "iokit")]
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
        let mut data = SMCPowerData::default();

        // Try to read each sensor, but don't fail if some are missing
        data.battery_power = conn.read_key("PPBR").ok();
        data.power_input = conn.read_key("PDTR").ok();
        data.system_power = conn.read_key("PSTR").ok();
        data.heatpipe_power = conn.read_key("PHPC").ok();
        data.display_power = conn.read_key("PDBR").ok();
        data.battery_temp = conn.read_key("TB0T").ok();
        data.charging_status = conn.read_key("CHCC").ok();

        Ok(data)
    }
}

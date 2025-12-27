//! IOKit-based power collector using SMC sensors and IORegistry
//!
//! This collector provides more accurate power readings than parsing ioreg command output.

use crate::{
    collector::{ioreg::IORegCollector, PowerCollector},
    models::PowerReading,
    PowerError, PowerResult,
};
use chrono::Utc;

#[cfg(feature = "iokit")]
use super::smc::SMCPowerData;

/// Power collector using IOKit/SMC
pub struct IOKitCollector;

impl IOKitCollector {
    /// Collect power data from both SMC sensors and IORegistry
    #[cfg(feature = "iokit")]
    fn collect_with_smc() -> PowerResult<PowerReading> {
        // Get SMC sensor data
        let smc_data = SMCPowerData::read()?;

        // Get battery info from IORegistry (reuse ioreg parser for now)
        // In production, this would use direct IORegistry API calls
        let mut reading = IORegCollector.collect()?;

        // Enhance reading with SMC data
        if let Some(power_input) = smc_data.power_input {
            // PDTR is more accurate than calculated V*A
            reading.watts_actual = power_input as f64;
        }

        // Add debug info about SMC sensors (could be added to PowerReading struct)
        if cfg!(debug_assertions) {
            eprintln!("SMC Data:");
            eprintln!("  PPBR (Battery Power): {:?}W", smc_data.battery_power);
            eprintln!("  PDTR (Power Input): {:?}W", smc_data.power_input);
            eprintln!("  PSTR (System Power): {:?}W", smc_data.system_power);
            eprintln!("  PHPC (Heatpipe): {:?}W", smc_data.heatpipe_power);
            eprintln!("  PDBR (Display): {:?}W", smc_data.display_power);
            eprintln!("  TB0T (Battery Temp): {:?}°C", smc_data.battery_temp);
            eprintln!("  CHCC (Charging): {:?}", smc_data.charging_status);
        }

        Ok(reading)
    }

    /// Fallback to ioreg if SMC access fails
    #[cfg(feature = "iokit")]
    fn collect_fallback() -> PowerResult<PowerReading> {
        eprintln!("Warning: SMC access failed, falling back to ioreg");
        IORegCollector.collect()
    }
}

impl PowerCollector for IOKitCollector {
    #[cfg(feature = "iokit")]
    fn collect(&self) -> PowerResult<PowerReading> {
        // Try SMC first, fall back to ioreg if it fails
        Self::collect_with_smc().or_else(|e| {
            eprintln!("SMC error: {}", e);
            Self::collect_fallback()
        })
    }

    #[cfg(not(feature = "iokit"))]
    fn collect(&self) -> PowerResult<PowerReading> {
        Err(PowerError::UnsupportedPlatform)
    }
}

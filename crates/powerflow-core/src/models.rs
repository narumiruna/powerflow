use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Real-time power reading snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerReading {
    /// Timestamp when reading was taken
    pub timestamp: DateTime<Utc>,

    // Power metrics
    /// Actual power flow: positive = charging, negative = discharging (W)
    pub watts_actual: f64,
    /// PD negotiated maximum power (W)
    pub watts_negotiated: i32,

    // Electrical details
    /// Voltage (V)
    pub voltage: f64,
    /// Current (A)
    pub amperage: f64,

    // Battery state
    /// Current battery capacity (mAh)
    pub current_capacity: i32,
    /// Maximum battery capacity (mAh)
    pub max_capacity: i32,
    /// Battery percentage (0-100)
    pub battery_percent: i32,

    // Status
    /// Is battery currently charging
    pub is_charging: bool,
    /// Is external power connected
    pub external_connected: bool,
    /// Charger/adapter name
    pub charger_name: Option<String>,
    /// Charger manufacturer
    pub charger_manufacturer: Option<String>,
}

impl PowerReading {
    /// Calculate actual wattage from voltage and amperage
    /// Voltage is in V, Amperage is in A, returns W
    pub fn calculate_watts(voltage: f64, amperage: f64) -> f64 {
        voltage * amperage
    }
}

/// Raw adapter details from ioreg
#[derive(Debug, Clone, Deserialize)]
pub struct AdapterDetail {
    #[serde(rename = "Watts")]
    pub watts: Option<i32>,

    #[serde(rename = "Name")]
    pub name: Option<String>,

    #[serde(rename = "Description")]
    pub description: Option<String>,

    #[serde(rename = "Manufacturer")]
    pub manufacturer: Option<String>,

    #[serde(rename = "Voltage")]
    pub voltage: Option<i32>, // mV

    #[serde(rename = "Current")]
    pub current: Option<i32>, // mA
}

/// Raw data from ioreg (for parsing)
#[derive(Debug, Clone, Deserialize)]
pub struct IORegBattery {
    #[serde(rename = "CurrentCapacity")]
    pub current_capacity: Option<i32>,

    #[serde(rename = "MaxCapacity")]
    pub max_capacity: Option<i32>,

    #[serde(rename = "IsCharging")]
    pub is_charging: Option<bool>,

    #[serde(rename = "ExternalConnected")]
    pub external_connected: Option<bool>,

    #[serde(rename = "Voltage")]
    pub voltage: Option<i32>, // mV

    #[serde(rename = "Amperage")]
    pub amperage: Option<i32>, // mA (negative = discharging)

    #[serde(rename = "AppleRawCurrentCapacity")]
    pub raw_current_capacity: Option<i32>, // mAh

    #[serde(rename = "AppleRawMaxCapacity")]
    pub raw_max_capacity: Option<i32>, // mAh

    #[serde(rename = "AppleRawAdapterDetails")]
    pub adapter_details: Option<Vec<AdapterDetail>>,
}

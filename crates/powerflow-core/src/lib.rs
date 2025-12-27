pub mod collector;
pub mod error;
pub mod models;

// Re-export commonly used types
pub use collector::{default_collector, PowerCollector};
pub use error::{PowerError, PowerResult};
pub use models::{AdapterDetail, IORegBattery, PowerReading};

/// Collect current power reading using the default collector
pub fn collect() -> PowerResult<PowerReading> {
    let collector = default_collector();
    collector.collect()
}

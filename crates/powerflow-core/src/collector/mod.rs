pub mod ioreg;

#[cfg(feature = "iokit")]
pub mod iokit;

#[cfg(feature = "iokit")]
pub mod smc;

use crate::{PowerReading, PowerResult};

/// Trait for power data collectors
pub trait PowerCollector {
    fn collect(&self) -> PowerResult<PowerReading>;
}

/// Get the default power collector for this platform
#[cfg(target_os = "macos")]
pub fn default_collector() -> Box<dyn PowerCollector> {
    #[cfg(feature = "iokit")]
    {
        Box::new(iokit::IOKitCollector)
    }

    #[cfg(not(feature = "iokit"))]
    {
        Box::new(ioreg::IORegCollector)
    }
}

#[cfg(not(target_os = "macos"))]
pub fn default_collector() -> Box<dyn PowerCollector> {
    compile_error!("PowerFlow only supports macOS")
}

use colored::*;
use powerflow_core::PowerReading;

/// Print reading in human-readable format with colors
pub fn print_reading(reading: &PowerReading) {
    // Status line
    if reading.is_charging {
        println!("{}", "⚡ Charging".green().bold());
    } else if reading.external_connected {
        println!("{}", "🔌 On AC Power (Not Charging)".yellow().bold());
    } else {
        println!("{}", "🔋 On Battery".red().bold());
    }

    // Power info
    if reading.watts_negotiated > 0 {
        println!(
            "   Power: {:.1}W / {}W max",
            reading.watts_actual.abs(),
            reading.watts_negotiated
        );
    } else {
        println!("   Power: {:.1}W", reading.watts_actual.abs());
    }

    // Battery info
    println!(
        "   Battery: {}% ({} mAh / {} mAh)",
        reading.battery_percent, reading.current_capacity, reading.max_capacity
    );

    // Electrical details
    println!(
        "   Electrical: {:.2}V × {:.2}A",
        reading.voltage,
        reading.amperage.abs()
    );

    // Charger info
    if let Some(ref name) = reading.charger_name {
        print!("   Charger: {}", name);
        if let Some(ref manufacturer) = reading.charger_manufacturer {
            println!(" ({})", manufacturer);
        } else {
            println!();
        }
    }

    // Timestamp
    println!("   Time: {}", reading.timestamp.format("%Y-%m-%d %H:%M:%S"));
}

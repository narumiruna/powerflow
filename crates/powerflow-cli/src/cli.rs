use crate::display;
use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "powerflow")]
#[command(version)]
#[command(about = "Mac power monitoring tool", long_about = None)]
pub struct Cli {
    /// Output as JSON
    #[arg(long, global = true)]
    json: bool,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    /// Display current power stats (default)
    Status,

    /// Continuous monitoring
    Watch {
        /// Update interval in seconds
        #[arg(short, long, default_value = "2")]
        interval: u64,
    },
}

impl Cli {
    pub fn execute(&self) -> Result<()> {
        match &self.command {
            Some(Commands::Status) | None => {
                // Default: show current status
                self.show_status()
            }
            Some(Commands::Watch { interval }) => {
                self.watch_mode(*interval)
            }
        }
    }

    fn show_status(&self) -> Result<()> {
        let reading = powerflow_core::collect()?;

        if self.json {
            display::json::print_reading(&reading)?;
        } else {
            display::human::print_reading(&reading);
        }

        Ok(())
    }

    fn watch_mode(&self, interval: u64) -> Result<()> {
        use std::io;
        use std::time::Duration;
        use crossterm::{cursor, execute, terminal};

        let duration = Duration::from_secs(interval);

        loop {
            if !self.json {
                // Clear screen for human output
                execute!(io::stdout(), terminal::Clear(terminal::ClearType::All))?;
                execute!(io::stdout(), cursor::MoveTo(0, 0))?;
            }

            match powerflow_core::collect() {
                Ok(reading) => {
                    if self.json {
                        display::json::print_reading(&reading)?;
                    } else {
                        display::human::print_reading(&reading);
                    }
                }
                Err(e) => eprintln!("Error: {}", e),
            }

            std::thread::sleep(duration);
        }
    }
}

mod cli;
mod database;
mod display;

use anyhow::Result;
use clap::Parser;

fn main() -> Result<()> {
    let args = cli::Cli::parse();
    args.execute()
}

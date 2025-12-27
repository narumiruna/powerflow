mod cli;
mod display;
mod database;

use anyhow::Result;
use clap::Parser;

fn main() -> Result<()> {
    let args = cli::Cli::parse();
    args.execute()
}

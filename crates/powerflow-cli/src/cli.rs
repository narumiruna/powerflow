use super::database;
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
    /// 顯示目前電源資訊
    Status,

    /// 持續監控模式
    Watch {
        /// 更新間隔（秒）
        #[arg(short, long, default_value = "2")]
        interval: u64,
    },

    /// 查詢歷史資料
    History {
        /// 查詢筆數（預設 20）
        #[arg(long, default_value = "20")]
        limit: usize,

        /// 以 JSON 格式輸出
        #[arg(long)]
        json: bool,

        /// 輸出圖表 PNG 檔案（預設 powerflow-history.png）
        #[arg(long)]
        plot: bool,

        /// 圖表檔案名稱
        #[arg(long, default_value = "powerflow-history.png")]
        output: String,
    },
}

fn tui_history_chart(readings: &[powerflow_core::PowerReading]) -> anyhow::Result<()> {
    use crossterm::{
        event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
        execute,
        terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
    };
    use ratatui::{
        backend::CrosstermBackend,
        layout::{Constraint, Direction, Layout},
        style::{Color, Modifier, Style},
        widgets::{Axis, Block, Borders, Cell, Chart, Dataset, Paragraph, Row, Table},
        Terminal,
    };
    use std::io::{self};

    if readings.is_empty() {
        println!("沒有可用的歷史資料，無法繪製圖表。");
        return Ok(());
    }

    // Prepare data for plotting
    let watts: Vec<_> = readings.iter().map(|r| r.watts_actual).collect();
    let max_watts: Vec<_> = readings.iter().map(|r| r.watts_negotiated as f64).collect();

    // Normalize x axis to indices (since time labels are hard in TUI)
    let x: Vec<f64> = (0..readings.len()).map(|i| i as f64).collect();
    let data_watt: Vec<(f64, f64)> = x.iter().cloned().zip(watts.iter().cloned()).collect();
    let data_max: Vec<(f64, f64)> = x.iter().cloned().zip(max_watts.iter().cloned()).collect();

    // Find y range
    let min_power = watts
        .iter()
        .cloned()
        .fold(f64::INFINITY, f64::min)
        .min(max_watts.iter().cloned().fold(f64::INFINITY, f64::min));
    let max_power = watts
        .iter()
        .cloned()
        .fold(f64::NEG_INFINITY, f64::max)
        .max(max_watts.iter().cloned().fold(f64::NEG_INFINITY, f64::max));

    // Statistics block
    let latest = readings.first().unwrap();
    let oldest = readings.last().unwrap();
    let avg_watt = watts.iter().sum::<f64>() / watts.len() as f64;
    let min_watt = watts.iter().cloned().fold(f64::INFINITY, f64::min);
    let max_watt = watts.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let avg_percent =
        readings.iter().map(|r| r.battery_percent).sum::<i32>() as f64 / readings.len() as f64;

    let stats = format!(
        "最新: {}\n最舊: {}\n平均功率: {:.1}W\n最大功率: {:.1}W\n最小功率: {:.1}W\n平均電池: {:.1}%",
        latest.timestamp.format("%Y-%m-%d %H:%M:%S"),
        oldest.timestamp.format("%Y-%m-%d %H:%M:%S"),
        avg_watt,
        max_watt,
        min_watt,
        avg_percent
    );

    // Table block (show up to 10 latest, newest first)
    let table_rows: Vec<Row> = readings
        .iter()
        .rev()
        .take(10)
        .map(|r| {
            Row::new(vec![
                Cell::from(r.timestamp.format("%m-%d %H:%M").to_string()),
                Cell::from(format!("{:.1}", r.watts_actual)),
                Cell::from(format!("{}", r.watts_negotiated)),
                Cell::from(format!("{:.2}", r.voltage)),
                Cell::from(format!("{:.2}", r.amperage)),
                Cell::from(format!("{}%", r.battery_percent)),
                Cell::from(if r.is_charging {
                    "充電"
                } else if r.external_connected {
                    "外接"
                } else {
                    "電池"
                }),
            ])
        })
        .collect();

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let result = (|| {
        loop {
            terminal.draw(|f| {
                let size = f.size();
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .margin(1)
                    .constraints(
                        [
                            Constraint::Length(6),
                            Constraint::Length(12),
                            Constraint::Min(10),
                        ]
                        .as_ref(),
                    )
                    .split(size);

                // Statistics
                let stats_block = Paragraph::new(stats.clone())
                    .block(Block::default().title("統計資訊").borders(Borders::ALL))
                    .style(
                        Style::default()
                            .fg(Color::Cyan)
                            .add_modifier(Modifier::BOLD),
                    );
                f.render_widget(stats_block, chunks[0]);

                // Table
                let table = Table::new(
                    table_rows.clone(),
                    [
                        Constraint::Length(12),
                        Constraint::Length(8),
                        Constraint::Length(10),
                        Constraint::Length(8),
                        Constraint::Length(8),
                        Constraint::Length(8),
                        Constraint::Length(8),
                    ],
                )
                .header(
                    Row::new(vec![
                        "時間",
                        "功率",
                        "協商功率",
                        "電壓",
                        "電流",
                        "電池",
                        "狀態",
                    ])
                    .style(
                        Style::default()
                            .fg(Color::Yellow)
                            .add_modifier(Modifier::BOLD),
                    ),
                )
                .block(Block::default().title("最近記錄").borders(Borders::ALL));
                f.render_widget(table, chunks[1]);

                // Chart
                let chart = Chart::new(vec![
                    Dataset::default()
                        .name("Power Watt")
                        .graph_type(ratatui::widgets::GraphType::Line)
                        .style(Style::default().fg(Color::Red))
                        .data(&data_watt),
                    Dataset::default()
                        .name("Max Power (Watt)")
                        .graph_type(ratatui::widgets::GraphType::Line)
                        .style(Style::default().fg(Color::Blue))
                        .data(&data_max),
                ])
                .block(
                    Block::default()
                        .title("PowerFlow 歷史功率 (q 離開)")
                        .borders(Borders::ALL),
                )
                .x_axis(
                    Axis::default()
                        .title("時間 (最新→最舊)")
                        .style(Style::default().fg(Color::Gray))
                        .bounds([0.0, x.len().max(1) as f64 - 1.0])
                        .labels(vec![
                            "最新".into(),
                            format!("{}", x.len().max(1) / 2).into(),
                            "最舊".into(),
                        ]),
                )
                .y_axis(
                    Axis::default()
                        .title("功率 (Watt)")
                        .style(Style::default().fg(Color::Gray))
                        .bounds([min_power, max_power])
                        .labels(vec![
                            format!("{:.1}", min_power).into(),
                            format!("{:.1}", (min_power + max_power) / 2.0).into(),
                            format!("{:.1}", max_power).into(),
                        ]),
                );
                f.render_widget(chart, chunks[2]);
            })?;

            if event::poll(std::time::Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.code == KeyCode::Char('q') || key.code == KeyCode::Esc {
                        break;
                    }
                }
            }
        }
        Ok(())
    })();

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    result
}

fn plot_history_chart(
    readings: &[powerflow_core::PowerReading],
    output: &str,
) -> anyhow::Result<()> {
    use chrono::Local;
    use plotters::prelude::*;

    if readings.is_empty() {
        println!("沒有可用的歷史資料，無法繪製圖表。");
        return Ok(());
    }

    let root = BitMapBackend::new(output, (900, 480)).into_drawing_area();
    root.fill(&WHITE)?;

    let times: Vec<_> = readings
        .iter()
        .map(|r| r.timestamp.with_timezone(&Local))
        .collect();
    let watts: Vec<_> = readings.iter().map(|r| r.watts_actual).collect();
    let max_watts: Vec<_> = readings.iter().map(|r| r.watts_negotiated as f64).collect();

    let min_time = *times.first().unwrap();
    let max_time = *times.last().unwrap();
    let min_power = watts
        .iter()
        .cloned()
        .fold(f64::INFINITY, f64::min)
        .min(max_watts.iter().cloned().fold(f64::INFINITY, f64::min));
    let max_power = watts
        .iter()
        .cloned()
        .fold(f64::NEG_INFINITY, f64::max)
        .max(max_watts.iter().cloned().fold(f64::NEG_INFINITY, f64::max));

    let mut chart = ChartBuilder::on(&root)
        .caption("PowerFlow 歷史功率", ("sans-serif", 30))
        .margin(20)
        .x_label_area_size(40)
        .y_label_area_size(60)
        .build_cartesian_2d(min_time..max_time, min_power..max_power)?;

    chart
        .configure_mesh()
        .x_desc("時間")
        .y_desc("功率 (Watt)")
        .label_style(("sans-serif", 18))
        .draw()?;

    chart
        .draw_series(LineSeries::new(
            times.iter().zip(watts.iter()).map(|(t, w)| (*t, *w)),
            RED,
        ))?
        .label("Power Watt")
        .legend(|(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], RED));

    chart
        .draw_series(LineSeries::new(
            times.iter().zip(max_watts.iter()).map(|(t, w)| (*t, *w)),
            BLUE,
        ))?
        .label("Max Power (Watt)")
        .legend(|(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], BLUE));

    chart
        .configure_series_labels()
        .background_style(WHITE.mix(0.8))
        .border_style(BLACK)
        .label_font(("sans-serif", 18))
        .draw()?;

    Ok(())
}

impl Cli {
    pub fn execute(&self) -> Result<()> {
        // Initialize database connection
        let db_path = "./powerflow.db";
        let conn = database::init_db(db_path)?;

        match &self.command {
            Some(Commands::Status) | None => {
                // 顯示目前電源資訊
                let reading = powerflow_core::collect()?;
                // Save to history
                database::insert_reading(&conn, &reading)?;
                if self.json {
                    display::json::print_reading(&reading)?;
                } else {
                    display::human::print_reading(&reading);
                }
                Ok(())
            }
            Some(Commands::Watch { interval }) => {
                // 持續監控模式
                use crossterm::{cursor, execute, terminal};
                use std::io;
                use std::time::Duration;

                let duration = Duration::from_secs(*interval);

                loop {
                    if !self.json {
                        // Clear screen for human output
                        execute!(io::stdout(), terminal::Clear(terminal::ClearType::All))?;
                        execute!(io::stdout(), cursor::MoveTo(0, 0))?;
                    }

                    match powerflow_core::collect() {
                        Ok(reading) => {
                            // Save to history
                            database::insert_reading(&conn, &reading)?;
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
            Some(Commands::History {
                limit,
                json,
                plot,
                output,
            }) => {
                // 查詢歷史資料
                let readings = database::query_history(&conn, *limit)?;
                if *json {
                    display::json::print_readings(&readings)?;
                } else if *plot {
                    plot_history_chart(&readings, output)?;
                    println!("已輸出圖表至 {}", output);
                } else {
                    tui_history_chart(&readings)?;
                }
                Ok(())
            }
        }
    }
}

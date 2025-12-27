// Prevents additional console window on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use powerflow_core::collect;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager, State,
};
use tokio::sync::Mutex;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct PowerData {
    watts_actual: f64,
    watts_negotiated: i32,
    battery_percent: i32,
    is_charging: bool,
    voltage: f64,
    amperage: f64,
    charger_name: Option<String>,
}

struct AppState {
    power_data: Arc<Mutex<Option<PowerData>>>,
}

#[tauri::command]
async fn get_power_data(state: State<'_, AppState>) -> Result<PowerData, String> {
    let data = state.power_data.lock().await;
    data.clone()
        .ok_or_else(|| "No power data available".to_string())
}

fn update_tray_title(app: &tauri::AppHandle, watts: f64, max_watts: i32) {
    if let Some(tray) = app.tray_by_id("main-tray") {
        let title = if watts > 0.0 {
            format!("⚡ {:.1}W / {}W", watts, max_watts)
        } else {
            format!("🔋 {:.1}W", watts.abs())
        };
        let _ = tray.set_title(Some(&title));
    }
}

async fn collect_power_data(app: tauri::AppHandle, state: Arc<Mutex<Option<PowerData>>>) {
    let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));

    loop {
        interval.tick().await;

        match collect() {
            Ok(reading) => {
                let power_data = PowerData {
                    watts_actual: reading.watts_actual,
                    watts_negotiated: reading.watts_negotiated,
                    battery_percent: reading.battery_percent,
                    is_charging: reading.is_charging,
                    voltage: reading.voltage,
                    amperage: reading.amperage,
                    charger_name: reading.charger_name.clone(),
                };

                // Debug output
                println!(
                    "📊 Power Data: {:.1}W / {}W, Battery: {}%, Charger: {:?}",
                    power_data.watts_actual,
                    power_data.watts_negotiated,
                    power_data.battery_percent,
                    power_data.charger_name
                );

                // Update tray icon title
                update_tray_title(&app, power_data.watts_actual, power_data.watts_negotiated);

                // Store the data
                let mut data = state.lock().await;
                *data = Some(power_data.clone());

                // Emit event to frontend
                let _ = app.emit("power-update", power_data);
            }
            Err(e) => {
                eprintln!("Failed to collect power data: {}", e);
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
fn main() {
    let power_data = Arc::new(Mutex::new(None));
    let power_data_clone = power_data.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            // Create menu items
            let show_item = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            // Create tray icon
            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .icon(app.default_window_icon().unwrap().clone())
                .title("PowerFlow")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            // Start background task to collect power data
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                collect_power_data(app_handle, power_data_clone).await;
            });

            Ok(())
        })
        .manage(AppState { power_data })
        .invoke_handler(tauri::generate_handler![get_power_data])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

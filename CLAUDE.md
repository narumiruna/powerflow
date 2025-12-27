# PowerFlow

macOS menu bar app，顯示充電器即時瓦數與歷史紀錄。

## 專案目標

- 在 menu bar 顯示即時充電瓦數（如 `⚡ 45W / 67W`）
- 點擊展開視窗，顯示即時圖表與歷史資料
- 背景記錄充電資料到 SQLite
- 低資源占用（目標 <30MB RAM, <0.5% CPU idle）

## 技術棧

- **語言**: Rust 1.75+
- **GUI**: Tauri v2 (menu bar + webview)
- **前端**: HTML + Chart.js（輕量，不用 React）
- **資料庫**: SQLite (rusqlite)
- **電源資訊**: 解析 `ioreg` 指令輸出
- **最低支援**: macOS 12.0 (Monterey)

## 專案結構

```
powerflow/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.rs              # Tauri entry point
│   │   ├── lib.rs               # 模組匯出
│   │   ├── power_collector.rs   # 讀取電源資訊 (ioreg)
│   │   ├── models.rs            # 資料結構
│   │   ├── database.rs          # SQLite 存取
│   │   ├── tray.rs              # System tray 邏輯
│   │   └── commands.rs          # Tauri IPC commands
│   └── icons/
├── src/                         # 前端
│   ├── index.html
│   ├── main.js
│   ├── chart.js                 # 圖表邏輯
│   └── style.css
├── CLAUDE.md
├── README.md
└── Makefile
```

## 資料模型

```rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerReading {
    pub id: i64,
    pub timestamp: DateTime<Utc>,
    
    // 功率資訊
    pub watts_actual: f64,        // 即時瓦數（正=充電，負=放電）
    pub watts_negotiated: i32,    // PD 協商上限
    
    // 細節
    pub voltage: f64,             // 電壓 (V)
    pub amperage: f64,            // 電流 (A)
    
    // 狀態
    pub battery_percent: i32,     // 電池百分比
    pub is_charging: bool,        // 是否充電中
    pub charger_name: Option<String>, // 充電器名稱
}
```

## 電源資訊讀取

透過 `ioreg` 指令取得電源資訊：

```rust
use std::process::Command;

// 取得電池資訊
fn get_battery_info() -> String {
    let output = Command::new("ioreg")
        .args(["-rw0", "-c", "AppleSmartBattery"])
        .output()
        .expect("Failed to execute ioreg");
    String::from_utf8_lossy(&output.stdout).to_string()
}

// 取得充電器資訊 (備用)
fn get_charger_info() -> String {
    let output = Command::new("system_profiler")
        .args(["SPPowerDataType"])
        .output()
        .expect("Failed to execute system_profiler");
    String::from_utf8_lossy(&output.stdout).to_string()
}
```

### 要解析的 ioreg key

```
AppleSmartBattery:
├── "CurrentCapacity"     # 電池當前容量 (mAh)
├── "MaxCapacity"         # 電池最大容量 (mAh)
├── "IsCharging"          # 是否充電中 (bool)
├── "Voltage"             # 電壓 (mV)
├── "Amperage"            # 電流 (mA, 負數=放電)
├── "ExternalConnected"   # 是否接電源
└── "AppleRawAdapterDetails" # 充電器資訊 array
    └── [0]
        ├── "Watts"       # 協商瓦數
        ├── "Name"        # 充電器名稱
        ├── "Manufacturer"# 製造商
        ├── "Voltage"     # 充電電壓 (mV)
        └── "Current"     # 充電電流 (mA)
```

## Tauri 設定重點

```json
// tauri.conf.json
{
  "app": {
    "withGlobalTauri": true,
    "trayIcon": {
      "iconPath": "icons/icon.png",
      "iconAsTemplate": true
    }
  },
  "bundle": {
    "identifier": "com.powerflow.app",
    "macOS": {
      "minimumSystemVersion": "12.0"
    }
  }
}
```

## 開發指令

```bash
# 安裝 Rust (如果還沒裝)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 安裝 Tauri CLI
cargo install tauri-cli

# 初始化專案
cargo tauri init

# 開發模式 (hot reload)
cargo tauri dev

# 建置 release
cargo tauri build

# 單獨測試 Rust 邏輯
cargo test

# 只編譯 Rust 部分
cargo build --release
```

## 依賴 (Cargo.toml)

```toml
[package]
name = "powerflow"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
rusqlite = { version = "0.31", features = ["bundled"] }
chrono = { version = "0.4", features = ["serde"] }
regex = "1"
tokio = { version = "1", features = ["full"] }
```

## TODO

### Phase 1: 核心功能
- [ ] 專案初始化 (cargo tauri init)
- [ ] power_collector: 解析 ioreg 輸出
- [ ] CLI 驗證資料正確性
- [ ] 單元測試

### Phase 2: Tray + 基本 UI
- [ ] System tray 顯示瓦數文字
- [ ] 基本 popup 視窗
- [ ] 前端 HTML/CSS

### Phase 3: 資料記錄
- [ ] SQLite 整合
- [ ] 背景定時採集 (每 5 秒)
- [ ] 資料保留策略 (預設 7 天)

### Phase 4: 圖表
- [ ] Chart.js 即時圖表
- [ ] 歷史資料查詢 (1h / 24h / 7d)
- [ ] 雙線圖 (實際 vs 上限)

### Phase 5: 完善
- [ ] 設定頁面
- [ ] 開機自動啟動 (LaunchAgent)
- [ ] App 簽署與公證
- [ ] README + 發布

## 替代方案：純 CLI 先行

如果先不做 GUI，可以純 Rust CLI 驗證核心邏輯：

```bash
$ powerflow
⚡ 充電中
   即時: 45.2W (67W max)
   電池: 72%
   電壓: 20.0V / 電流: 2.26A
   充電器: Apple 67W USB-C Power Adapter

$ powerflow --watch  # 持續監控
$ powerflow --json   # JSON 輸出
$ powerflow history  # 查看歷史
```

純 CLI 結構更簡單：

```
powerflow/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── power_collector.rs
│   ├── models.rs
│   └── database.rs
└── CLAUDE.md
```

## 參考資源

- [Tauri v2 文件](https://v2.tauri.app/)
- [Tauri System Tray](https://v2.tauri.app/learn/system-tray/)
- [rusqlite](https://github.com/rusqlite/rusqlite)
- [Chart.js](https://www.chartjs.org/)
- [WhatWatt 原始碼](https://github.com/SomeInterestingUserName/WhatWatt) - 參考 ioreg 解析
- [Powerflow](POWERFLOW.md) - POWERFLOW.md 文件

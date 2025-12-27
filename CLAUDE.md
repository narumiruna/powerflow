# PowerFlow CLI

本專案現已專注於 macOS 電源資訊的命令列工具（CLI），原 GUI 應用程式部分已移除。

## 專案目標

- 以 CLI 方式顯示即時充電瓦數（如 `⚡ 45W / 67W`）
- 持續監控模式（`--watch`），定時更新資料
- 支援 JSON 輸出
- 背景記錄充電資料到 SQLite（未來規劃）
- 低資源占用（目標 <30MB RAM, <0.5% CPU idle）

## 技術棧

- **語言**: Rust 1.75+
- **CLI**: clap, anyhow
- **資料庫**: SQLite (rusqlite, 未來規劃)
- **電源資訊**: 解析 `ioreg` 指令輸出
- **最低支援**: macOS 12.0 (Monterey)

## 專案結構

```
powerflow/
├── crates/
│   ├── powerflow-cli/         # CLI 工具主程式
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── main.rs
│   │       ├── cli.rs
│   │       ├── display/
│   │       └── ...
│   ├── powerflow-core/        # 電源資訊收集核心
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── models.rs
│   │       └── collector/
│   │           ├── iokit.rs
│   │           ├── ioreg.rs
│   │           └── smc/
│   └── powerflow-app/         # 原 GUI app（已移除 UI，僅保留結構）
├── CLAUDE.md
├── README.md
└── LICENSE
```

## CLI 功能範例

```bash
$ powerflow
⚡ 充電中
   即時: 45.2W (67W max)
   電池: 72%
   電壓: 20.0V / 電流: 2.26A
   充電器: Apple 67W USB-C Power Adapter

$ powerflow watch --interval 2  # 持續監控，每 2 秒更新
$ powerflow --json              # JSON 輸出
$ powerflow history             # 查看歷史（未來規劃）
```

## 資料模型

```rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerReading {
    pub id: i64,
    pub timestamp: DateTime<Utc>,
    pub watts_actual: f64,        // 即時瓦數（正=充電，負=放電）
    pub watts_negotiated: i32,    // PD 協商上限
    pub voltage: f64,             // 電壓 (V)
    pub amperage: f64,            // 電流 (A)
    pub battery_percent: i32,     // 電池百分比
    pub is_charging: bool,        // 是否充電中
    pub charger_name: Option<String>, // 充電器名稱
}
```

## 電源資訊讀取

透過 `ioreg` 指令取得電源資訊：

```rust
use std::process::Command;

fn get_battery_info() -> String {
    let output = Command::new("ioreg")
        .args(["-rw0", "-c", "AppleSmartBattery"])
        .output()
        .expect("Failed to execute ioreg");
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

## TODO

- [x] CLI 即時顯示充電資訊
- [x] 持續監控模式（watch）
- [x] 支援 JSON 輸出
- [ ] 歷史資料記錄與查詢（未來規劃）
- [ ] 整合 SQLite 資料庫（未來規劃）
- [ ] 單元測試

## 參考資源

- [Tauri v2 文件](https://v2.tauri.app/)（僅供歷史參考）
- [rusqlite](https://github.com/rusqlite/rusqlite)
- [WhatWatt 原始碼](https://github.com/SomeInterestingUserName/WhatWatt) - 參考 ioreg 解析
- [Powerflow](POWERFLOW.md) - POWERFLOW.md 文件

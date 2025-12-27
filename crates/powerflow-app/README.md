# PowerFlow - Tauri GUI Application

macOS menu bar 應用程式，顯示充電器即時瓦數與歷史紀錄。

## ✨ Phase 2 功能

已完成：
- ✅ System tray 顯示即時充電瓦數（如 `⚡ 45W / 67W`）
- ✅ 點擊 tray 圖示展開/隱藏視窗
- ✅ 即時顯示充電資料（電壓、電流、電池百分比）
- ✅ 每 5 秒自動更新資料
- ✅ 暗色主題 UI

## 🚀 開發與運行

### 開發模式（hot reload）

```bash
# 在專案根目錄執行
cd crates/powerflow-app
cargo tauri dev
```

### 建置 Release 版本

```bash
cd crates/powerflow-app
cargo tauri build
```

建置完成後，應用程式會在 `target/release/bundle/` 目錄中。

### 直接執行（不使用 Tauri dev）

```bash
cargo run --manifest-path crates/powerflow-app/Cargo.toml
```

## 📁 專案結構

```
crates/powerflow-app/
├── src/
│   └── main.rs              # Tauri 主程式 + System Tray 邏輯
├── ui/
│   ├── index.html           # 前端 HTML
│   ├── style.css            # 樣式
│   └── main.js              # 前端 JavaScript
├── icons/
│   └── icon.png             # App 圖示
├── tauri.conf.json          # Tauri 配置
├── Cargo.toml
└── build.rs
```

## 🎯 主要功能

### System Tray

- 即時顯示充電瓦數（正數=充電，負數=放電）
- 格式：`⚡ 45.2W / 67W` （實際瓦數 / 協商上限）
- 每 5 秒自動更新

### Popup 視窗

- **即時功率顯示**：大字顯示當前瓦數
- **進度條**：視覺化顯示功率佔比
- **電池資訊**：電池百分比、電壓、電流、充電器名稱
- **自動更新**：透過 WebSocket 即時接收後端資料

### 技術實現

- **後端** (Rust):
  - 使用 `powerflow-core` 讀取電源資訊（IOKit）
  - Tokio 非同步執行緒每 5 秒採集資料
  - Tauri IPC 傳遞資料到前端

- **前端** (HTML/CSS/JS):
  - 原生 JavaScript（無框架）
  - 使用 Tauri API 接收即時更新
  - 響應式設計，暗色主題

## 🔧 自訂與設定

### 修改更新頻率

編輯 `src/main.rs` 第 55 行：

```rust
let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));
// 改為其他秒數，例如 3 秒：from_secs(3)
```

### 自訂視窗大小

編輯 `tauri.conf.json`：

```json
"windows": [
  {
    "title": "PowerFlow",
    "width": 400,    // 修改寬度
    "height": 600,   // 修改高度
    ...
  }
]
```

### 更換圖示

1. 準備一張 1024x1024 PNG 圖片
2. 執行：
   ```bash
   cargo tauri icon path/to/your-icon.png
   ```
3. 重新建置應用程式

## 🐛 已知問題

- [ ] 圖表功能尚未實現（Phase 4）
- [ ] 尚未整合 SQLite 資料庫（Phase 3）
- [ ] 視窗關閉按鈕會完全退出應用（應該是隱藏視窗）

## 📝 下一步 (Phase 3)

- [ ] 整合 SQLite 資料庫記錄歷史資料
- [ ] 實現資料保留策略（預設 7 天）
- [ ] 查詢歷史資料 API

## 📝 下一步 (Phase 4)

- [ ] 使用 Chart.js 顯示即時圖表
- [ ] 支援查看不同時間範圍（1h / 24h / 7d）
- [ ] 雙線圖（實際 vs 上限）

## 🎨 UI 截圖

（開發中...）

## 📄 授權

MIT License

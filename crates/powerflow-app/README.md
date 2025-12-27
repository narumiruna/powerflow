# PowerFlow (App Module)

> ⚠️ 本 Tauri GUI 應用程式部分已移除，專案現僅專注於 CLI 工具開發。

本目錄原為 macOS menu bar 應用程式，顯示充電器即時瓦數與歷史紀錄。現已移除 UI 相關檔案與功能，未來開發將專注於 CLI 工具（請參見 `crates/powerflow-cli`）。

## 專案結構（已移除 UI）

```
crates/powerflow-app/
├── src/
│   └── main.rs              # Tauri 主程式 + System Tray 邏輯（暫時保留）
├── icons/
│   └── icon.png             # App 圖示
├── tauri.conf.json          # Tauri 配置（暫時保留）
├── Cargo.toml
└── build.rs
```

## 注意事項

- UI 前端（HTML/CSS/JS）已完全移除。
- 若需 CLI 工具，請使用 `crates/powerflow-cli` 目錄。
- 本目錄僅保留必要檔案以利未來可能的重構或參考。

## 授權

MIT License

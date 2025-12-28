# PowerFlow History CLI Rust → Python 遷移規劃

## 目標

- 將原本 Rust 實現的 powerflow history CLI 完整遷移為 Python 專案，確保所有功能、資料結構、終端輸出均能對齊並替換原有 Rust 版本。

## 遷移範圍

- CLI 主程式（命令分發、參數設計）
- 資料模型（PowerReading 結構）
- SQLite 資料庫 schema 與查詢邏輯
- 統計區塊、表格區塊、（可選）圖表區塊的終端美化輸出
- 進階參數（如 --json, --plot, --output）

## Rust → Python 結構映射

- Rust: crates/powerflow-cli/src/cli.rs, display/human.rs, database.rs, models.rs
- Python: src/powerflow_history.py（主程式）、models.py（資料結構，可選）、db.py（資料庫操作，可選）

### 資料模型對應

Rust:
```rust
pub struct PowerReading {
    pub timestamp: DateTime<Utc>,
    pub watts_actual: f64,
    pub watts_negotiated: i32,
    pub voltage: f64,
    pub amperage: f64,
    pub current_capacity: i32,
    pub max_capacity: i32,
    pub battery_percent: i32,
    pub is_charging: bool,
    pub external_connected: bool,
    pub charger_name: Option<String>,
    pub charger_manufacturer: Option<String>,
}
```

Python:
```python
class PowerReading:
    def __init__(self, timestamp, watts_actual, watts_negotiated, voltage, amperage,
                 current_capacity, max_capacity, battery_percent, is_charging,
                 external_connected, charger_name, charger_manufacturer):
        ...
```

### 資料庫 schema 對應

Rust:
- 使用 SQLite，資料表 power_readings，欄位如上

Python:
- 直接用 sqlite3 查詢 power_readings，欄位需完全對齊

### CLI 命令與參數映射

Rust:
- `powerflow history [--limit] [--json] [--plot] [--output]`

Python:
- `python src/powerflow_history.py history --limit [--json] [--plot] [--output]`

### 終端輸出樣式

- 統計區塊、表格區塊用 rich 對齊 Rust TUI 輸出
- （可選）圖表區塊可用 rich 或其他 Python TUI/GUI 库

## 遷移步驟建議

1. 分析 Rust 版 CLI 主流程與資料結構，整理所有命令與參數
2. 在 Python 專案中設計 Typer CLI 主程式，命令與參數對齊 Rust 版
3. 實作 PowerReading 資料模型（可選）
4. 實作 SQLite 查詢，確保 schema 與欄位完全一致
5. 實作 rich 統計區塊、表格區塊，輸出格式對齊
6. （可選）實作 JSON/圖表/匯出等進階功能
7. 測試 Python 版 CLI，確保所有功能與輸出均能替代 Rust 版
8. 更新文件，說明遷移流程與新用法

## 注意事項

- 資料庫 schema 必須完全一致，否則查詢/輸出會有落差
- CLI 參數、命令、輸出格式需與 Rust 版對齊，方便用戶無縫遷移
- 可逐步遷移，先完成主流程，再補充進階功能

# PowerFlow History Python CLI 改寫規劃

## 目標

- 以 Python 實現 powerflow 歷史查詢 CLI 工具，支援終端美化輸出（統計區塊、表格區塊）。
- 不依賴 matplotlib，僅用 rich 等終端美化庫。
- 支援 SQLite 歷史資料查詢，與現有 powerflow.db 兼容。

## 功能需求

- 查詢 powerflow.db 的歷史資料，預設顯示最近 20 筆。
- 統計區塊：顯示最新/最舊時間、平均/最大/最小功率、平均電池百分比。
- 表格區塊：顯示最近 10 筆詳細資料（時間、功率、協商功率、電壓、電流、電池、狀態）。
- CLI 參數支援自訂查詢筆數。
- 終端美化輸出，適合直接在 shell 使用。

## 技術選型

- Python 3.13
- Typer（CLI 框架）
- rich（終端美化，表格、Panel）
- sqlite3（標準庫，查詢 powerflow.db）
- ruff（程式碼 lint）
- ty（型別檢查）
- pytest（單元測試）

## Python 專案管理與 uv 用法

- `uv init`
  初始化新 Python 專案（生成 pyproject.toml）。
- `uv pip install <package>`
  安裝依賴（如 rich）。
- `uv pip install -r requirements.txt`
  從 requirements.txt 安裝依賴。
- `uv pip list`
  列出已安裝依賴。
- `uv pip uninstall <package>`
  卸載依賴包。
- `uv venv`
  建立虛擬環境。
- `uv python`
  選擇/切換 Python 版本。
- `uv run <script.py>`
  在 uv 管理的環境中執行 Python 腳本。
- `uv pip upgrade <package>`
  升級指定包。

參考：
- [uv 官方文件](https://docs.astral.sh/uv/reference/cli/)
- [uv 快速入門](https://docs.astral.sh/uv/getting-started/first-steps/)
- [uv 命令速查](https://www.reddit.com/r/Python/comments/1o2viq3/uv_cheatsheet_with_most_commonuseful_commands/)

## CLI 參數設計

- `python powerflow_history.py [limit]`
    - limit: 查詢筆數（預設 20）

## 資料來源與結構

- 資料庫：powerflow.db
- 資料表：power_readings
    - 欄位：timestamp, watts_actual, watts_negotiated, voltage, amperage, battery_percent, is_charging, external_connected

## 終端輸出樣式

- 統計區塊（Panel，cyan 邊框）
    - 最新: 2025-12-28 04:00:00
    - 最舊: 2025-12-27 20:00:00
    - 平均功率: 23.1W
    - 最大功率: 65.0W
    - 最小功率: 5.2W
    - 平均電池: 78.5%
- 表格區塊（rich Table，黃色標題）
    - 欄位：時間、功率、協商功率、電壓、電流、電池、狀態
    - 內容：最近 10 筆，最新在前

## 可擴展點

- 支援 JSON 輸出（如 `--json` 參數）
- 支援資料篩選（如時間區間、狀態）
- 支援多語系
- 支援匯出 CSV

## 實作步驟建議

1. 使用 Typer 設計 CLI 主程式結構
2. 實作 SQLite 查詢
3. 實作統計區塊輸出
4. 實作表格區塊輸出
5. 開發流程建議：
    - 使用 ruff 進行程式碼 lint
    - 使用 ty 進行型別檢查
    - 使用 pytest 撰寫與執行單元測試
6. 文檔與範例補充

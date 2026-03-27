# SPEC-003：SQLite 資料庫層 + 種子資料

> 實作 database.py、config.py 與 12 張 CREATE TABLE，並載入 OP-2024-017 完整 Demo 種子資料。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-003 |
| **關聯 ADR** | ADR-008（SQLite Schema 設計） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 建立 SQLite 連線管理（`database.py`）、環境配置（`config.py`）、12 張資料表的 Schema 初始化，以及 OP-2024-017「PHANTOM-EYE」Demo 種子資料載入器，讓後端可在啟動時自動建表並預填示範資料。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 12 張 CREATE TABLE | SQL | `data-architecture.md` Section 5 | 完全對映，含所有約束 |
| 種子資料 | 文件 | `data-architecture.md` Section 8 | 精確值（IP、callsign、health 等） |
| 環境變數 | 檔案 | `.env.example` | DATABASE_URL、CALDERA_URL 等 |
| 主鍵策略 | ADR | ADR-008 | UUID TEXT PRIMARY KEY |
| 外鍵策略 | ADR | ADR-008 | ON DELETE CASCADE |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `backend/app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///backend/data/athena.db"
    CALDERA_URL: str = "http://localhost:8888"
    CALDERA_API_KEY: str = ""
    SHANNON_URL: str = ""
    PENTESTGPT_API_URL: str = "http://localhost:8080"
    PENTESTGPT_MODEL: str = "gpt-4"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AUTOMATION_MODE: str = "semi_auto"
    RISK_THRESHOLD: str = "medium"
    LOG_LEVEL: str = "INFO"
    MOCK_LLM: bool = True              # POC 預設 mock 模式（無需 LLM API key）

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. `backend/app/database.py`

功能需求：
- 使用 `aiosqlite` 非同步連線管理
- `init_db()` 函式：執行 12 條 CREATE TABLE IF NOT EXISTS
- `get_db()` 非同步 generator 供 FastAPI Depends 使用
- 啟用 `PRAGMA foreign_keys = ON`
- 啟用 `PRAGMA journal_mode = WAL`
- 資料庫檔案路徑從 `settings.DATABASE_URL` 解析

### 3. 12 張 CREATE TABLE

嚴格複製 `data-architecture.md` Section 5 的 SQL，包含：

| 資料表 | 關鍵約束 |
|--------|---------|
| `users` | `id TEXT PRIMARY KEY` |
| `operations` | `code TEXT NOT NULL UNIQUE`, `operator_id TEXT REFERENCES users(id)` |
| `targets` | `operation_id TEXT REFERENCES operations(id)` |
| `agents` | `host_id TEXT REFERENCES targets(id)`, `operation_id TEXT REFERENCES operations(id)` |
| `techniques` | `mitre_id TEXT NOT NULL UNIQUE`（靜態目錄，無 operation_id） |
| `technique_executions` | `technique_id TEXT NOT NULL`, `operation_id TEXT REFERENCES operations(id)` |
| `facts` | `operation_id TEXT REFERENCES operations(id)` |
| `ooda_iterations` | `operation_id TEXT REFERENCES operations(id)` |
| `recommendations` | `operation_id TEXT REFERENCES operations(id)`, `options TEXT NOT NULL`（JSON） |
| `mission_steps` | `operation_id TEXT REFERENCES operations(id)`, `target_id TEXT REFERENCES targets(id)` |
| `c5isr_statuses` | `UNIQUE(operation_id, domain)` |
| `log_entries` | `operation_id TEXT`（可為 NULL） |

### 4. `backend/app/seed/demo_scenario.py`

載入 `data-architecture.md` Section 8 定義的完整種子資料：

| 實體 | 數量 | 關鍵值 |
|------|------|--------|
| User | 1 | callsign="VIPER-1", role="Commander" |
| Operation | 1 | code="OP-2024-017", codename="PHANTOM-EYE", status="active" |
| Target | 5 | DC-01, WS-PC01, WS-PC02, DB-01, FS-01 |
| Agent | 4 | AGENT-7F3A(alive), AGENT-2B1C(alive), AGENT-9E4D(pending), AGENT-5A7B(alive) |
| Technique | ≥4 | T1595.001, T1003.001, T1021.002, T1059.001 |
| MissionStep | 4 | 步驟 01-04（completed, running, queued, queued） |
| C5ISRStatus | 6 | 六域各一筆（100%, 90%, 60%, 93%, 73%, 67%） |
| PentestGPTRecommendation | 1 | T1003.001, confidence=0.87 |
| OODAIteration | ≥1 | iteration_number=1, phase=decide |
| Fact | ≥2 | credential + host 類型 |
| LogEntry | ≥3 | 不同 severity |
| TechniqueExecution | ≥1 | T1595.001 → completed |

種子資料必須：
- UUID 使用固定值（可重現，便於測試）
- 所有外鍵關係正確（operation_id、target_id、host_id）
- C5ISR 6 域 health 精確對映 Section 8
- 可透過 `python -m app.seed.demo_scenario` 獨立執行

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| 資料庫已存在 | CREATE TABLE IF NOT EXISTS（冪等） |
| 種子資料已存在 | INSERT OR IGNORE / 先清空再插入 |
| 外鍵違反 | 按依賴順序插入（users → operations → targets → agents → ...） |

---

## ⚠️ 邊界條件（Edge Cases）

- `backend/data/` 目錄可能不存在——`database.py` 需自動建立
- `techniques` 表為靜態目錄，無 `operation_id`（ADR-008 決策）
- `recommendations.options` 為 JSON TEXT——種子資料需 `json.dumps(list_of_dicts)`
- `technique.platforms` 為 JSON TEXT——種子資料需 `json.dumps(["windows"])`
- `c5isr_statuses` 的 `UNIQUE(operation_id, domain)` 約束——種子資料不可重複
- SQLite 不原生支援 BOOLEAN——使用 INTEGER（0/1）
- 所有 `TEXT DEFAULT (datetime('now'))` 時間戳為 ISO 8601 格式

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| Schema 變更導致種子資料失敗 | CREATE TABLE 欄位或約束修改時 | `demo_scenario.py` INSERT 語句、所有 router 的 SQL 查詢 | `python -m app.seed.demo_scenario` 無錯誤 |
| `init_db()` 在 FastAPI startup 執行 | 每次 backend 啟動時 | `main.py` lifespan、所有 API 端點的 DB 可用性 | `curl http://localhost:8000/api/health` 回傳 ok |
| 外鍵 CASCADE 影響資料刪除行為 | 刪除 operations 或 targets 記錄時 | 所有關聯表（agents、facts、ooda_iterations 等）的資料完整性 | 刪除 operation 後確認關聯記錄一併刪除 |
| `config.py` 環境變數影響全後端 | `.env` 檔案或環境變數變更時 | 資料庫路徑、Caldera/Shannon URL、LLM 設定 | `python -c "from app.config import settings; print(settings.DATABASE_URL)"` |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 1. 刪除 `backend/data/athena.db` 2. `git revert <commit>` 還原 database.py/config.py/seed 3. 重新執行 `init_db()` |
| **資料影響** | SQLite 資料庫檔案需刪除重建——種子資料為 Demo 資料，可完全重建 |
| **回滾驗證** | `sqlite3 backend/data/athena.db ".tables"` 顯示正確表數；seed 重新執行成功 |
| **回滾已測試** | ☑ 否（刪除 .db 檔案後重建為標準流程） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | 執行 `init_db()` 於空資料庫 | 12 張表全部建立，PRAGMA foreign_keys = ON | S1 |
| P2 | ✅ 正向 | 執行 `demo_scenario.py` 載入種子資料 | 1 operation、5 targets、4 agents、6 C5ISR 狀態等完整寫入 | S1 |
| P3 | ✅ 正向 | `settings.DATABASE_URL` 從 `.env` 讀取 | 正確解析路徑並建立連線 | S1 |
| N1 | ❌ 負向 | 外鍵參照不存在的 operation_id | INSERT 失敗，拋出 IntegrityError | S2 |
| N2 | ❌ 負向 | `backend/data/` 目錄不存在 | `database.py` 自動建立目錄後正常連線 | S2 |
| B1 | 🔶 邊界 | 資料庫已存在且表已建立 | `CREATE TABLE IF NOT EXISTS` 冪等通過 | S3 |
| B2 | 🔶 邊界 | 種子資料已存在（重複執行 seed） | `INSERT OR IGNORE` 不產生重複資料 | S3 |
| B3 | 🔶 邊界 | `recommendations.options` 為 JSON TEXT 格式 | `json.dumps(list_of_dicts)` 正確序列化並可反序列化 | S3 |

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-003 SQLite 資料庫層與種子資料
  作為 Athena 平台開發者
  我想要 自動化的資料庫初始化與 Demo 種子資料載入
  以便 後端啟動時自動建表並預填示範資料供開發與展示使用

  Background:
    Given backend/app/models/ 已實作（SPEC-002）
    And .env 或環境變數已設定 DATABASE_URL

  # --- 正向場景 ---

  Scenario: S1 - 資料庫初始化建立 12 張表並載入種子資料
    Given 資料庫檔案不存在
    When 執行 init_db() 後執行 demo_scenario
    Then sqlite3 .tables 顯示 12 張表
    And operations 表有 1 筆記錄（OP-2024-017 PHANTOM-EYE）
    And targets 表有 5 筆記錄（DC-01, WS-PC01, WS-PC02, DB-01, FS-01）
    And agents 表有 4 筆記錄，其中 3 筆 status=alive
    And c5isr_statuses 表有 6 筆記錄（六域各一）
    And PRAGMA foreign_keys 為 ON

  Scenario: S1b - Config 正確讀取環境變數
    Given .env 檔案包含 DATABASE_URL 與 CALDERA_URL
    When 匯入 settings
    Then settings.DATABASE_URL 回傳正確路徑
    And settings.MOCK_LLM 預設為 True

  # --- 負向場景 ---

  Scenario: S2 - 外鍵違反時插入失敗
    Given 資料庫已初始化
    When 插入 target 記錄且 operation_id 不存在於 operations 表
    Then 拋出外鍵約束錯誤
    And 資料未寫入 targets 表

  # --- 邊界場景 ---

  Scenario: S3 - 重複執行資料庫初始化與種子載入（冪等性）
    Given 資料庫已初始化且種子資料已載入
    When 再次執行 init_db() 與 demo_scenario
    Then 表結構不變（CREATE TABLE IF NOT EXISTS）
    And 種子資料不重複（INSERT OR IGNORE）
    And 查詢 operations 表仍為 1 筆記錄
```

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/config.py` | `backend/tests/conftest.py`（間接使用 settings） | 2026-03-26 |
| `backend/app/database/manager.py` | `backend/tests/conftest.py`（init_db 呼叫） | 2026-03-26 |
| `backend/app/database/seed.py` | `backend/tests/conftest.py`（seed 載入） | 2026-03-26 |
| `backend/app/seed/demo_scenario.py` | `backend/tests/test_spec_004_api.py`（依賴 seed 資料） | 2026-03-26 |
| `backend/app/seed/demo_runner.py` | `backend/tests/test_spec_004_api.py`（間接） | 2026-03-26 |

## 📊 可觀測性（Observability）

| 面向 | 說明 |
|------|------|
| **關鍵指標** | DB 連線池使用率、init_db 執行時間、seed 載入筆數 |
| **日誌** | `init_db()` 完成時 INFO 級別記錄表數量；seed 載入時 INFO 記錄各實體筆數；外鍵違反時 ERROR 記錄 |
| **告警** | `init_db()` 失敗時（DB 檔案無法建立）觸發 CRITICAL 告警 |
| **如何偵測故障** | `GET /api/health` 回傳 database 狀態；`sqlite3 athena.db "SELECT count(*) FROM operations"` 確認資料完整性 |

---

## ✅ 驗收標準（Done When）

- [x] `cd backend && python -c "from app.config import settings; print(settings.DATABASE_URL)"` — 成功
- [x] `cd backend && python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"` — 成功建表
- [x] `cd backend && python -m app.seed.demo_scenario` — 成功載入種子資料
- [x] `sqlite3 backend/data/athena.db ".tables"` — 顯示 12 張表
- [x] `sqlite3 backend/data/athena.db "SELECT count(*) FROM operations"` — 輸出 1
- [x] `sqlite3 backend/data/athena.db "SELECT count(*) FROM targets"` — 輸出 5
- [x] `sqlite3 backend/data/athena.db "SELECT count(*) FROM agents"` — 輸出 4
- [x] `sqlite3 backend/data/athena.db "SELECT count(*) FROM c5isr_statuses"` — 輸出 6
- [x] `sqlite3 backend/data/athena.db "SELECT domain, health_pct FROM c5isr_statuses ORDER BY domain"` — 6 筆正確值 — ⚠️ 實際值由 OODA 循環動態更新，與初始設計值不同（種子資料寫入正常，動態更新為預期行為）
- [x] `sqlite3 backend/data/athena.db "PRAGMA foreign_key_list(targets)"` — 顯示 operations 外鍵

---

## 🚫 禁止事項（Out of Scope）

- 不要使用 SQLAlchemy ORM——使用原生 SQL + aiosqlite
- 不要建立 migration 系統（Alembic 等）——POC 使用 CREATE TABLE IF NOT EXISTS
- 不要新增 `data-architecture.md` Section 5 未定義的資料表
- 不要修改 `data-architecture.md` 中的 SQL schema
- 不要實作 API 端點——那是 SPEC-004 的範圍

---

## 📎 參考資料（References）

- ADR-008：[SQLite Schema 設計](../adr/ADR-008-sqlite-data-schema-design.md)
- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 5（Schema）+ Section 8（Seed Data）
- ADR-011：[POC 不實作身份驗證](../adr/ADR-011-no-auth-for-poc.md)（User stub）
- SPEC-002：Pydantic Models + Enums（依賴——Model 結構定義）


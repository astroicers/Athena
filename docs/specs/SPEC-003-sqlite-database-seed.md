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

## ✅ 驗收標準（Done When）

- [ ] `cd backend && python -c "from app.config import settings; print(settings.DATABASE_URL)"` — 成功
- [ ] `cd backend && python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"` — 成功建表
- [ ] `cd backend && python -m app.seed.demo_scenario` — 成功載入種子資料
- [ ] `sqlite3 backend/data/athena.db ".tables"` — 顯示 12 張表
- [ ] `sqlite3 backend/data/athena.db "SELECT count(*) FROM operations"` — 輸出 1
- [ ] `sqlite3 backend/data/athena.db "SELECT count(*) FROM targets"` — 輸出 5
- [ ] `sqlite3 backend/data/athena.db "SELECT count(*) FROM agents"` — 輸出 4
- [ ] `sqlite3 backend/data/athena.db "SELECT count(*) FROM c5isr_statuses"` — 輸出 6
- [ ] `sqlite3 backend/data/athena.db "SELECT domain, health_pct FROM c5isr_statuses ORDER BY domain"` — 6 筆正確值
- [ ] `sqlite3 backend/data/athena.db "PRAGMA foreign_key_list(targets)"` — 顯示 operations 外鍵

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

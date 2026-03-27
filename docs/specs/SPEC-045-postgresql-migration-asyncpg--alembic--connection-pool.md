# SPEC-045：PostgreSQL Migration: asyncpg + Alembic + Connection Pool

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-045 |
| **關聯 ADR** | ADR-038 (Accepted) |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | minimal |

---

## Goal

將 Athena 後端從 SQLite (aiosqlite) 一刀切遷移至 PostgreSQL (asyncpg)，引入 Alembic schema migration 框架和連線池管理。影響 46 個檔案、344+ SQL 查詢。

---

## 實作範圍

### Phase A: 依賴與基礎建設

1. **pyproject.toml** 新增依賴：`asyncpg>=0.29.0`, `alembic>=1.13.0`, `sqlalchemy>=2.0.0` (Alembic env only)
2. **pyproject.toml dev** 新增：`testcontainers[postgres]>=4.0.0`
3. **docker-compose.yml** 新增 postgres service (postgres:16-alpine)
4. **config.py** DATABASE_URL 改為 PG 預設值

### Phase B: Database Package 重構

將 `backend/app/database.py` (952L) 拆分為：

```
backend/app/database/
├── __init__.py          # export get_db, db_manager, init_db
├── manager.py           # DatabaseManager class (asyncpg pool)
└── seed.py              # Seed data (PG 語法)
```

**DatabaseManager 核心**：
- `asyncpg.create_pool(min_size=5, max_size=20)`
- `connection()` async context manager
- `transaction()` async context manager (auto commit/rollback)
- `startup()` → create pool + run Alembic upgrade
- `shutdown()` → close pool

### Phase C: Alembic 設定

```
backend/alembic/
├── alembic.ini
├── env.py               # async migration runner
└── versions/
    └── 001_initial_schema.py   # 現有 22 表
```

### Phase D: SQL 語法全局替換

| SQLite | PostgreSQL | 影響 |
|--------|-----------|------|
| `?` | `$1, $2, ...` | 所有 services + routers (~344 queries) |
| `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` | ~35 處 |
| `datetime('now')` | `NOW()` | ~25 處 |
| `TEXT` JSON 欄位 | `JSONB` | schema 定義 |
| `INTEGER` booleans | `BOOLEAN` | is_compromised, is_active, enabled, exploit_available |
| `TEXT` PKs | `UUID DEFAULT gen_random_uuid()` | 所有表 |
| `TEXT` FKs | `UUID` | 所有外鍵 |
| `GROUP_CONCAT` | `STRING_AGG` | 1 處 (node_summarizer) |
| `LIKE` | `ILIKE` (where case-insensitive needed) | 審查 8 處 |
| `hex(randomblob(4))` | `gen_random_uuid()` | migration code |

### Phase E: 測試遷移

- `conftest.py`: 使用 testcontainers PostgresContainer (session scope)
- 每個 test fixture truncate all tables
- 所有 `aiosqlite.Row` 替換為 `asyncpg.Record`

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| DB driver 從 aiosqlite → asyncpg | 系統啟動 `DatabaseManager.startup()` | 所有 service/router（46 檔案、344+ 查詢） | `make test` 全數通過（PG 環境） |
| Connection model 從 per-request → pool (min=5, max=20) | FastAPI DI `get_db()` 呼叫時 | `backend/app/database/manager.py` → FastAPI 所有路由 | 壓力測試：並行 20 請求不 deadlock |
| Row 物件從 aiosqlite.Row → asyncpg.Record | 所有 `dict(row)` / `row["col"]` 存取時 | 所有 services/routers 中的 row 存取 | grep 確認無殘留 `aiosqlite.Row` 引用 |
| Schema 管理從 CREATE IF NOT EXISTS → Alembic migration | `startup()` 呼叫 `alembic upgrade head` | `backend/alembic/versions/*.py` | `alembic upgrade head` 成功建立 22 表 |
| UUID type 從 TEXT → native UUID | 所有 INSERT 語句 | 所有表 PK/FK | 查詢驗證 `pg_typeof(id)` 回傳 `uuid` |
| SQL placeholder 從 `?` → `$1, $2, ...` | 所有 SQL 查詢執行時 | 344+ 處查詢 | grep 確認無殘留 `?` placeholder |

---

## Edge Cases

- Case 1: Pool exhaustion under high concurrency → max_size=20, 超時 30s 後 raise
- Case 2: Migration 失敗 → Alembic DOWN 回退
- Case 3: Seed data 重複執行 → ON CONFLICT DO NOTHING 確保冪等

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| `git revert <commit>` — 恢復 `database.py` 單檔結構 | 開發環境需重新 seed（無生產資料） | `make test` 全數通過（SQLite 環境） | 否（待實作後驗證） |
| 移除 docker-compose postgres service | PG 容器資料遺失（開發環境無影響） | `docker-compose up` 正常啟動（不含 PG） | 否 |
| 還原 `pyproject.toml` 移除 asyncpg/alembic 依賴 | 無 | `pip install -e .` 成功 | 否 |

> **不可逆評估**：無不可逆部分。SQLite 檔案保留在 repo 中，revert 後可直接恢復使用。

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景描述 | 輸入 | 預期結果 | 對應驗收場景 |
|----|------|----------|------|----------|-------------|
| P1 | 正向 | Alembic migration — 建立所有表 | `alembic upgrade head` | 22 表全部建立成功 | Scenario: PostgreSQL migration and startup |
| P2 | 正向 | Connection pool 正常取得連線 | `get_db()` DI 注入 | 回傳 asyncpg connection 物件 | Scenario: PostgreSQL migration and startup |
| P3 | 正向 | Seed data 載入 | `make dev` 啟動 | techniques, playbooks 等 seed 資料正確載入 | Scenario: PostgreSQL migration and startup |
| P4 | 正向 | SQL placeholder 替換 — $1/$2 | 所有 service/router 查詢 | 查詢正確執行無 syntax error | Scenario: PostgreSQL migration and startup |
| P5 | 正向 | JSONB 欄位查詢 | `SELECT data->>'key' FROM ...` | 正確回傳 JSON 欄位值 | Scenario: PostgreSQL migration and startup |
| N1 | 負向 | Pool exhaustion — 超過 max_size | 21 個並行連線請求 | 第 21 個請求 30s 超時後 raise | Scenario: PostgreSQL error handling |
| N2 | 負向 | Migration 失敗 — 語法錯誤 | 損壞的 migration 檔案 | Alembic 報錯，不破壞現有表 | Scenario: PostgreSQL error handling |
| N3 | 負向 | PG 未啟動 | DATABASE_URL 指向未運行的 PG | 啟動時明確報錯，不 hang | Scenario: PostgreSQL error handling |
| B1 | 邊界 | Seed data 重複執行 — 冪等 | 連續 2 次 seed | `ON CONFLICT DO NOTHING` 確保不重複 | Scenario: PostgreSQL migration and startup |
| B2 | 邊界 | INSERT OR IGNORE → ON CONFLICT DO NOTHING | 所有 35 處替換 | 語義等價，冪等行為不變 | Scenario: PostgreSQL migration and startup |
| B3 | 邊界 | aiosqlite import 清理 | grep `aiosqlite` | 無殘留 import（除 pyproject.toml optional） | Scenario: PostgreSQL migration and startup |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: PostgreSQL Migration with asyncpg, Alembic, and Connection Pool
  SPEC-045 — 從 SQLite 一刀切遷移至 PostgreSQL。

  Background:
    Given docker-compose 中 postgres service 已啟動（postgres:16-alpine）
    And DATABASE_URL 指向本地 PG 實例

  Scenario: PostgreSQL migration and startup
    When 執行 alembic upgrade head
    Then 22 表全部建立成功（operations, targets, facts, techniques 等）
    And 所有 index 已建立
    When 執行 make dev
    Then FastAPI 成功啟動
    And seed data 正確載入（techniques, playbooks 等）
    When 再次執行 seed
    Then 不產生重複資料（ON CONFLICT DO NOTHING）
    When 執行 make test
    Then 所有現有測試通過（PG 環境）
    And 無 aiosqlite import 殘留（除 pyproject.toml optional）
    And 所有 SQL 使用 $1/$2 placeholder
    And JSONB 欄位可在 DB 層查詢

  Scenario: PostgreSQL error handling
    Given PG service 未啟動
    When 嘗試啟動 FastAPI
    Then 明確報錯（connection refused），不 hang
    Given PG service 已啟動且 pool max_size=20
    When 21 個並行連線請求發送
    Then 第 21 個請求在 30s 內超時報錯
    And 前 20 個請求正常完成
```

---

## 追溯性（Traceability）

| 項目 | 檔案路徑 | 狀態 | 備註 |
|------|----------|------|------|
| SPEC 文件 | `docs/specs/SPEC-045-postgresql-migration-asyncpg--alembic--connection-pool.md` | 已建立 | 本文件 |
| 後端實作 — DatabaseManager | `backend/app/database/manager.py` | 已存在 | asyncpg pool 管理 |
| 後端實作 — Database init | `backend/app/database/__init__.py` | （待確認） | export get_db, db_manager, init_db |
| 後端實作 — Seed | `backend/app/database/seed.py` | 已存在 | PG 語法 seed data |
| Alembic — env.py | `backend/alembic/env.py` | 已存在 | async migration runner |
| Alembic — initial schema | `backend/alembic/versions/001_initial_schema.py` | 已存在 | 現有 22 表 migration |
| Alembic — opsec/mission | `backend/alembic/versions/002_opsec_mission_tables.py` | 已存在 | OpSec/Mission 表 migration |
| Alembic — config | `backend/alembic/alembic.ini` | 已存在 | Alembic 設定檔 |
| 後端測試 — conftest | `backend/tests/conftest.py` | 已存在 | testcontainers PostgresContainer fixture |
| ADR | ADR-038 | 已接受 | PostgreSQL Migration and Alembic Schema Management |
| 前端實作 | — | N/A | 本 SPEC 不修改前端 |

> 追溯日期：2026-03-26

---

## 可觀測性（Observability）

| 項目 | 類型 | 名稱/格式 | 觸發條件 | 說明 |
|------|------|-----------|----------|------|
| Pool 建立 | log (INFO) | `DatabaseManager: pool created (min=%d, max=%d)` | `startup()` 完成 | 記錄 pool 大小 |
| Pool 關閉 | log (INFO) | `DatabaseManager: pool closed` | `shutdown()` 完成 | 記錄 pool 關閉 |
| Migration 執行 | log (INFO) | `Alembic: upgraded to %s` | `alembic upgrade head` 成功 | 記錄目標 revision |
| Migration 失敗 | log (ERROR) | `Alembic: migration failed: %s` | migration 執行異常 | 含 exception 詳情 |
| Connection 取得超時 | log (WARNING) | `Pool connection timeout after %ds` | pool 耗盡等待超時 | 記錄等待秒數 |
| Seed 完成 | log (INFO) | `Seed data loaded: %d tables` | seed 執行完成 | 記錄 seed 的表數量 |
| 前端 | N/A | — | — | 本 SPEC 不修改前端 |

---

## Done When

- [ ] `alembic upgrade head` 成功建立所有 22 表
- [ ] `make test` 全部現有測試通過（PG 環境）
- [ ] `make dev` 啟動正常（docker-compose up）
- [ ] Seed data 正確載入
- [ ] 無 aiosqlite import 殘留（除 pyproject.toml 保留為 optional）
- [ ] 所有 SQL 使用 $1/$2 placeholder
- [ ] JSONB 欄位可在 DB 層查詢

---

## Out of Scope

- 不建立 Phase 1-4 的新表（留給 SPEC-046~049）
- 不修改前端
- 不做效能基準測試

---

## References

- ADR-038: PostgreSQL Migration and Alembic Schema Management
- Plan: `/home/ubuntu/.claude/plans/logical-munching-finch.md` Phase 0



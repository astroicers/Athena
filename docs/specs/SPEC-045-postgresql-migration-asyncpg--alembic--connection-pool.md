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

## Side Effects

| 狀態變動 | 受影響功能 | 預期行為 |
|---------|-----------|---------|
| DB driver 從 aiosqlite → asyncpg | 所有 service/router | SQL 語法全部適配 PG |
| Connection model 從 per-request → pool | FastAPI DI (get_db) | 改為從 pool 取連線 |
| Row 物件從 aiosqlite.Row → asyncpg.Record | 所有 dict(row) 用法 | Record 支援 dict-like access |
| Schema 管理從 CREATE IF NOT EXISTS → Alembic | init_db() | 改為 alembic upgrade head |
| UUID type 從 TEXT → UUID | 所有 INSERT 語句 | 使用 uuid.uuid4() 或 gen_random_uuid() |

---

## Edge Cases

- Case 1: Pool exhaustion under high concurrency → max_size=20, 超時 30s 後 raise
- Case 2: Migration 失敗 → Alembic DOWN 回退
- Case 3: Seed data 重複執行 → ON CONFLICT DO NOTHING 確保冪等

### Rollback Plan

- **回退方式**：git revert + 恢復 database.py + 移除 docker-compose postgres service
- **不可逆評估**：無不可逆部分（SQLite 檔案保留）
- **資料影響**：開發環境需重新 seed，無生產資料

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

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->

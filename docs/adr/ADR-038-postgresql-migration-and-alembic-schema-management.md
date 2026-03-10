# [ADR-038]: PostgreSQL Migration and Alembic Schema Management

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-10 |
| **決策者** | 架構師 / 專案負責人 |

---

## 背景（Context）

Athena 目前使用 SQLite（aiosqlite）作為資料庫，存在以下限制：

1. **單寫入鎖**：SQLite 不支援併發寫入，多個 OODA 循環同時執行時會產生鎖競爭
2. **無 JSONB 支援**：C5ISR metrics、OPSEC events 等結構化數據只能存為 TEXT，無法在 DB 層查詢
3. **無原生 UUID**：每處手動生成 UUID 字串，無 `gen_random_uuid()` 原生支援
4. **無 Schema Migration**：現有 952 行 `database.py` 以 `CREATE TABLE IF NOT EXISTS` 管理，無版本化遷移歷史
5. **缺乏連線池**：每次請求建立新連線，無法利用 asyncpg 的高效 binary protocol
6. **SQL 方言差異**：大量使用 SQLite 專有語法（`?` placeholder、`INSERT OR IGNORE`、`json_extract()`、`datetime('now')`）

隨著 Phase 1-4（Mission Profile、C5ISR 重構、OPSEC 監控、Dashboard API）的引入，新增 5+ 張表、JSONB 欄位、時序查詢需求急增，繼續使用 SQLite 將成為系統瓶頸。

---

## 評估選項（Options Considered）

### 選項 A：漸進遷移（雙驅動共存）

- **優點**：風險低，可逐步切換
- **缺點**：需維護兩套 SQL 方言（SQLite + PG），所有查詢需抽象層；開發時需測兩個 DB
- **風險**：雙驅動維護成本高，抽象層引入額外複雜度，可能長期拖延完成遷移

### 選項 B：一刀切遷移（直接切換到 PostgreSQL）

- **優點**：
  - 只維護一套 SQL 方言，降低長期維護成本
  - 立即獲得 JSONB、UUID、連線池、併發寫入等能力
  - Alembic migration 從第一天就版本化
- **缺點**：
  - 一次性修改 ~40 個檔案的 SQL 語法
  - 開發環境需 Docker/PostgreSQL
  - 所有測試需切換到 PG（testcontainers）
- **風險**：大量同時修改可能引入回歸 bug，需全量測試驗證

---

## 決策（Decision）

我們選擇 **選項 B：一刀切遷移**，因為：

1. Athena 已有 Docker 開發環境，PG 只需加一個 service
2. 雙驅動的維護成本遠高於一次性遷移成本
3. Phase 1-4 的新功能強烈依賴 JSONB 和併發寫入，早遷移早受益
4. 現有 532+ tests 提供足夠的回歸保護

### 技術方案

- **驅動**：`asyncpg>=0.29.0`（binary protocol，不走 SQLAlchemy ORM）
- **Schema 管理**：`alembic>=1.13.0`（async runner，UP+DOWN migration）
- **連線池**：`asyncpg.create_pool(min_size=5, max_size=20)`
- **SQL 語法替換**：

| SQLite | PostgreSQL |
|--------|-----------|
| `?` | `$1, $2, ...` |
| `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` |
| `INSERT OR REPLACE` | `ON CONFLICT DO UPDATE` |
| `datetime('now')` | `NOW()` |
| `json_extract()` | `->>` / `@>` (JSONB) |
| `GROUP_CONCAT` | `STRING_AGG` |
| TEXT JSON 欄位 | `JSONB` |

- **目錄結構**：
```
backend/app/database.py (952L) → 拆分為:
backend/app/database/
├── __init__.py          # export get_db, db_manager
├── manager.py           # DatabaseManager (asyncpg pool)
└── seed.py              # Seed data (PG 語法)

backend/alembic/
├── alembic.ini
├── env.py               # async migration runner
└── versions/
    ├── 001_initial_schema.py
    └── 002_opsec_mission_tables.py
```

- **Docker**：`docker-compose.yml` 新增 `postgres:16-alpine` service，healthcheck `pg_isready`
- **測試**：`testcontainers[postgres]` session-scoped fixture，每 test truncate all tables

---

## 後果（Consequences）

**正面影響：**
- 獲得 JSONB、UUID 原生支援、併發寫入、連線池
- Schema 變更有版本化歷史（Alembic migration）
- 為 Phase 1-4 的新表和時序查詢鋪平道路

**負面影響 / 技術債：**
- ~40 個檔案需一次性修改 SQL 語法
- 開發者本地需 Docker 或 PostgreSQL 實例
- 現有 SQLite 資料無自動遷移（重新 seed）

**後續追蹤：**
- [ ] SPEC-045：完整遷移實作規格
- [ ] Alembic 001 初始 Schema（現有 20+ 表）
- [ ] Alembic 002 新增表（opsec_events、mission_objectives、credentials 等）
- [ ] CI（GitHub Actions）加 PostgreSQL service container

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 測試通過率 | 532+ tests 全部通過（PG 環境） | `make test` | 遷移完成時 |
| `alembic upgrade head` | 無錯誤完成 | CLI 執行 | 遷移完成時 |
| Seed data 載入 | demo scenario 完整載入 | `make dev` 啟動驗證 | 遷移完成時 |
| 查詢效能 | JSONB 查詢 < 50ms | Dashboard API 測試 | Phase 4 完成時 |

> 若遷移後測試通過率 < 100% 或效能明顯劣化，應重新評估是否需要查詢層抽象。

---

## 關聯（Relations）

- 取代：無（首次資料庫技術決策）
- 被取代：無
- 參考：SPEC-045（實作規格）

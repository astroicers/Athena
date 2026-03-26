# SPEC-025：Tool Registry 管理系統

> 提供集中式工具/引擎註冊中心，含 CRUD REST API + 前端管理頁面。已實作完成，補建 SPEC 以符合 ASP Pre-Implementation Gate。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-025 |
| **關聯 ADR** | 無新架構決策（向後相容，不改動現有 engine_router / recon_engine / osint_engine 核心邏輯）；未來若啟用動態路由可參照 SPEC-016（Planned） |
| **估算複雜度** | 中（1 DDL + 1 model + 1 router + 3 前端元件 + 1 hook） |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |
| **tech-debt** | 無 |

---

## 🎯 目標（Goal）

> 現有工具（nmap, subfinder, crt.sh）和執行引擎（SSH, C2, Metasploit）全部 hardcoded 於各 service 模組中，無法新增、刪除或列表管理。建立 `tool_registry` SQLite 表作為中央註冊中心，提供 REST CRUD API 與前端管理頁面，向後相容現有 hardcoded 邏輯。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `tool_id` | str | URL path / body | slug 格式（`nmap`, `ssh` 等），UNIQUE |
| `name` | str | body | 顯示名稱，必填 |
| `kind` | str | body / query | `"tool"` \| `"engine"`，預設 `"tool"` |
| `category` | str | body / query | `reconnaissance` \| `enumeration` \| `vulnerability_scanning` \| `credential_access` \| `exploitation` \| `execution` |
| `enabled` | bool | body / query | 預設 `true` |
| `risk_level` | str | body | `low` \| `medium` \| `high` \| `critical` |
| `config_json` | dict | body | JSON 物件，預設 `{}` |
| `mitre_techniques` | list[str] | body | MITRE 技術 ID 列表，預設 `[]` |
| `output_traits` | list[str] | body | 輸出 trait 類型列表，預設 `[]` |

---

## 📤 預期輸出（Expected Output）

### 後端

1. **`tool_registry` DDL** — 新 SQLite 表，含 14 欄位（id, tool_id, name, description, kind, category, version, enabled, source, config_json, mitre_techniques, risk_level, output_traits, created_at, updated_at）
2. **Seed 資料** — 10 筆預設工具/引擎（source=`seed`）：nmap, subfinder, crtsh, nvd_lookup, ssh, persistent_ssh, c2, metasploit, winrm, mock
3. **Pydantic Models** — `ToolRegistryCreate`、`ToolRegistryUpdate`、`ToolRegistryEntry`
4. **Enums** — `ToolKind`（tool/engine）、`ToolCategory`（6 類）
5. **REST API**：

| Method | Path | 功能 | 回傳 |
|--------|------|------|------|
| `GET` | `/api/tools` | 列表（可 filter: kind, category, enabled） | `ToolRegistryEntry[]` |
| `GET` | `/api/tools/{tool_id}` | 取得單一工具（by slug） | `ToolRegistryEntry` |
| `POST` | `/api/tools` | 新增工具（source=`user`，重複 tool_id → 409） | `ToolRegistryEntry` |
| `PATCH` | `/api/tools/{tool_id}` | 更新（不可改 tool_id/kind/source） | `ToolRegistryEntry` |
| `DELETE` | `/api/tools/{tool_id}` | 刪除（僅 source=`user`，seed → 403） | 204 |
| `POST` | `/api/tools/{tool_id}/check` | 健康檢查 stub | `{tool_id, available, detail}` |

### 前端

1. **`/tools` 頁面** — TabBar 切換 Recon Tools / Execution Engines
2. **ToolRegistryTable** — 顯示 Name、Category、Status（Toggle）、Risk（Badge）、MITRE 數量、Actions（CHECK/DELETE）
3. **AddToolModal** — 新增工具表單（tool_id, name, kind, category, risk_level, description）
4. **Nav 更新** — `NAV_ITEMS` 新增 `{ href: "/tools", icon: "⚙", label: "Tool Registry" }`

---

## ✅ Done When

- [x] `tool_registry` DDL 在 `init_db()` 中建立
- [x] 10 筆 seed 工具在首次啟動時寫入（`source='seed'`）
- [x] `GET /api/tools` 回傳列表，支援 kind/category/enabled filter
- [x] `POST /api/tools` 新增 user 工具，重複 tool_id → HTTP 409
- [x] `DELETE /api/tools/{tool_id}` seed 工具 → HTTP 403
- [x] `DELETE /api/tools/{tool_id}` user 工具 → HTTP 204
- [x] `PATCH /api/tools/{tool_id}` 更新成功，`updated_at` 自動更新
- [x] `POST /api/tools/{tool_id}/check` 回傳 available 狀態
- [x] Backend pytest 13/13 tests passed（`tests/test_tools_router.py`）
- [x] `/tools` 頁面顯示 Recon Tools / Execution Engines tab 切換
- [x] ToolRegistryTable Toggle enable/disable 即時更新
- [x] AddToolModal 新增工具成功、重新 fetch 列表
- [x] seed 工具 DELETE 按鈕 disabled（前端阻擋）
- [x] `tsc --noEmit` clean
- [x] `next build` clean

---

## 🔧 實作範圍（Edge Cases & Constraints）

### Seed 保護機制

- `source='seed'` 的工具只能 PATCH（enable/disable），不能 DELETE（HTTP 403）
- 前端 ToolRegistryTable 中 seed 工具的 DELETE 按鈕設為 disabled + opacity-50

### JSON 欄位處理

- `config_json`、`mitre_techniques`、`output_traits` 在 SQLite 中以 TEXT 儲存，讀取時 `json.loads()` 反序列化
- 寫入時 `json.dumps()` 序列化

### 向後相容

- 不改動 `recon_engine.py`、`osint_engine.py`、`engine_router.py` 的核心邏輯
- Tool Registry 目前為純管理用途，不影響 OODA 循環的工具選擇（未來 Phase 可整合）

---

## 📂 影響檔案

### 新增
| 檔案 | 說明 |
|------|------|
| `backend/app/models/tool_registry.py` | Pydantic CRUD models |
| `backend/app/routers/tools.py` | REST CRUD router（6 endpoints） |
| `backend/tests/test_tools_router.py` | 13 test cases |
| `frontend/src/types/tool.ts` | TypeScript 型別定義 |
| `frontend/src/hooks/useTools.ts` | 工具資料 fetch hook |
| `frontend/src/components/tools/ToolRegistryTable.tsx` | 工具列表元件 |
| `frontend/src/components/tools/AddToolModal.tsx` | 新增工具 modal |
| `frontend/src/app/tools/page.tsx` | Tools 管理頁面 |

### 修改
| 檔案 | 改動摘要 |
|------|----------|
| `backend/app/database.py` | 新增 `tool_registry` DDL + `_seed_tool_registry()` |
| `backend/app/models/enums.py` | 新增 `ToolKind`、`ToolCategory` enums |
| `backend/app/main.py` | `include_router(tools.router)` |
| `backend/app/routers/__init__.py` | import `tools` |
| `frontend/src/lib/constants.ts` | `NAV_ITEMS` 新增 Tool Registry |

---

## 🧪 測試策略

### 後端（pytest）— 13 tests

- `test_list_tools` — 回傳 seed 列表，≥10 筆
- `test_list_tools_filter_kind` — kind=engine filter
- `test_list_tools_filter_category` — category=reconnaissance filter
- `test_list_tools_filter_enabled` — enabled=true filter
- `test_get_tool` — 取得單一工具 by tool_id
- `test_get_tool_not_found` — 不存在 → 404
- `test_create_tool` — 新增 user 工具 → 201
- `test_create_tool_duplicate` — 重複 tool_id → 409
- `test_update_tool` — PATCH 更新 → 200
- `test_update_tool_not_found` — 不存在 → 404
- `test_delete_user_tool` — 刪除 user 工具 → 204
- `test_delete_seed_tool` — 刪除 seed 工具 → 403
- `test_check_tool` — 健康檢查 → 200

---

_SPEC 由 Claude Opus 4.6 於 2026-03-04 補建，對應 Tool Registry 實作。_

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->

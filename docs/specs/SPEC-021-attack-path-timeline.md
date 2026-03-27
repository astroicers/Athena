# SPEC-021: Attack Path Timeline — Navigator 頁統一攻擊路徑視圖

| 欄位 | 內容 |
|------|------|
| **SPEC-ID** | SPEC-021 |
| **標題** | Attack Path Timeline — Navigator 頁統一攻擊路徑視圖 |
| **狀態** | ✅ 完成（commit: feat: Attack Path Timeline + DirectSSHEngine） |
| **優先度** | High |
| **相關 ADR** | ADR-003（OODA 引擎）、ADR-017（DirectSSHEngine） |
| **日期** | 2026-03-02 |

---

## 動機

MITRE ATT&CK 的 Reconnaissance → Resource Development → Initial Access → ... → Impact 路徑目前分散在不同頁面，沒有統一的「攻擊路徑 + MITRE 標籤」一體視圖。指揮官需要一眼看出 kill chain 推進到哪個階段，哪些技術成功/失敗。

---

## 功能需求

| ID | 需求 | 驗收條件 |
|----|------|---------|
| F1 | 14 欄水平時序，對應 MITRE ATT&CK 14 個 tactics（TA0043→TA0040） | 欄位順序正確，標頭顯示 tactic 縮寫 + tactic_id |
| F2 | 已執行 techniques 以 pill 呈現於對應 tactic 欄（以 tactic_id 分組） | Pill 出現在正確 tactic 欄 |
| F3 | pill 顯示 status 圓點和 MITRE ID | ● 綠=success, ✗ 紅=failed, ⟳ 青=running/queued |
| F4 | hover tooltip 顯示 technique_name、engine、duration_sec、target_ip | Hover 顯示完整資訊 |
| F5 | 最遠達到欄底部有 accent 亮邊框 | `border-b-2 border-athena-accent` 在正確欄 |
| F6 | WebSocket `execution.update` 事件觸發即時刷新 | 執行後不需 refresh 頁面即更新 |
| F7 | 空欄顯示灰色虛線 | `border-dashed opacity-30` 風格 |
| F8 | loading 狀態顯示 shimmer skeleton | `animate-pulse` placeholder |

---

## API 需求

**新增 endpoint：** `GET /api/operations/{operation_id}/attack-path`

**Response schema：**
```json
{
  "operation_id": "string",
  "entries": [
    {
      "execution_id": "string",
      "mitre_id": "string",
      "technique_name": "string",
      "tactic": "string",
      "tactic_id": "string",
      "kill_chain_stage": "string",
      "risk_level": "string",
      "status": "queued|running|success|partial|failed",
      "engine": "string",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "duration_sec": "number | null",
      "result_summary": "string | null",
      "error_message": "string | null",
      "facts_collected_count": "number",
      "target_hostname": "string | null",
      "target_ip": "string | null"
    }
  ],
  "highest_tactic_idx": "number (0-13)",
  "tactic_coverage": {"TA0043": 2, "TA0001": 1}
}
```

---

## 實作位置

| 元件 | 檔案 |
|------|------|
| 後端 models | `backend/app/models/api_schemas.py` — `AttackPathEntry`, `AttackPathResponse` |
| 後端 endpoint | `backend/app/routers/techniques.py` — `GET /attack-path` |
| 前端 types | `frontend/src/types/attackPath.ts` |
| 前端 API | `frontend/src/lib/api.ts` — `getAttackPath()` |
| 前端 元件 | `frontend/src/components/mitre/AttackPathTimeline.tsx` |
| 前端 整合 | `frontend/src/app/navigator/page.tsx` |

---

## 驗證結果

- ✅ `python3 -m pytest tests/ -q` — 95 passed, 6 skipped（0 regression）
- ✅ `npx tsc --noEmit` — 0 TypeScript errors
- ✅ 14 欄正確對應 TACTIC_ORDER_IDS（TA0043→TA0040）
- ✅ WebSocket `execution.update` 觸發即時刷新

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| Navigator 頁新增 AttackPathTimeline 元件 | 載入 `/navigator` 頁面 | `frontend/src/app/navigator/page.tsx` | E2E 驗證 Navigator 頁面渲染 AttackPathTimeline |
| 新增 `GET /api/operations/{op_id}/attack-path` endpoint | 前端呼叫 `getAttackPath()` | `backend/app/routers/techniques.py` | pytest `test_techniques_router.py` 驗證回傳 schema |
| WebSocket `execution.update` 事件觸發即時刷新 | 執行技術後 status 改變 | `frontend/src/components/mitre/AttackPathTimeline.tsx` | 手動觸發 execution，確認 UI 即時更新 |

---

## ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| 1. Revert 新增 AttackPathTimeline 元件及 Navigator 頁面整合 commit | 無資料變動，純前端元件 | Navigator 頁面不顯示 AttackPath 區塊 | ✅ 可直接 revert |
| 2. Revert `GET /attack-path` endpoint 及 `AttackPathEntry`/`AttackPathResponse` models | 無 DB schema 變動，無資料遺失 | `GET /attack-path` 回傳 404 | ✅ 可直接 revert |
| 3. Revert 前端 types (`attackPath.ts`) 及 API function (`getAttackPath()`) | 無持久化資料影響 | TypeScript build clean（無 dead import） | ✅ 可直接 revert |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參考 |
|----|------|------|----------|----------|
| P1 | 正向 | 作戰含 5 個已執行 techniques，涵蓋 3 個 tactic 欄位 | 14 欄渲染，3 欄有 pill，最遠欄有 accent 邊框 | Scenario: 多 technique 正常渲染 |
| P2 | 正向 | WebSocket `execution.update` 推送新 technique 完成 | AttackPathTimeline 即時新增 pill，無需 refresh | Scenario: 即時 WebSocket 更新 |
| N1 | 負向 | 作戰無任何執行紀錄（entries 為空） | 14 欄均顯示灰色虛線，無 pill，無 accent 邊框 | Scenario: 空作戰路徑 |
| N2 | 負向 | operation_id 不存在 | API 回傳 404，前端顯示錯誤提示 | — |
| B1 | 邊界 | 同一 tactic 欄有 20+ techniques（大量 pill） | 欄位內 pill 可捲動/換行，不溢出 | Scenario: 大量 technique 堆疊 |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Attack Path Timeline 視圖
  Background:
    Given 已建立作戰 "OP-ALPHA"
    And 作戰包含 target "192.168.1.10"

  Scenario: 多 technique 正常渲染
    Given 作戰已執行 techniques T1595（TA0043）、T1078（TA0001）、T1059（TA0002）
    When 使用者進入 Navigator 頁面
    Then 14 欄水平時序正確顯示
    And TA0043 欄出現 T1595 pill 且狀態圓點為綠色
    And TA0001 欄出現 T1078 pill
    And TA0002 欄底部有 accent 亮邊框（最遠達到欄）

  Scenario: 空作戰路徑
    Given 作戰無任何已執行 technique
    When 使用者進入 Navigator 頁面
    Then 14 欄均顯示灰色虛線
    And 無任何 pill 顯示
    And 無 accent 邊框

  Scenario: 即時 WebSocket 更新
    Given 使用者已在 Navigator 頁面
    When 後端完成 T1003（TA0006）execution 並廣播 `execution.update`
    Then TA0006 欄即時新增 T1003 pill
    And pill 狀態圓點為綠色（success）
    And 使用者無需手動 refresh

  Scenario: 大量 technique 堆疊
    Given TA0002 欄已有 20 個已執行 technique
    When 使用者進入 Navigator 頁面
    Then TA0002 欄正確渲染所有 pill
    And pill 不溢出欄位邊界
```

---

## 🔍 追溯性（Traceability）

| 類型 | 檔案路徑 | 說明 |
|------|----------|------|
| 後端 Model | `backend/app/models/api_schemas.py` | `AttackPathEntry`, `AttackPathResponse` |
| 後端 Schema | `backend/app/models/schemas/attack.py` | Attack path schema 定義 |
| 後端 Router | `backend/app/routers/techniques.py` | `GET /attack-path` endpoint |
| 前端 Types | `frontend/src/types/attackPath.ts` | TypeScript 型別定義 |
| 前端 API | `frontend/src/lib/api.ts` | `getAttackPath()` 函數 |
| 前端 元件 | `frontend/src/components/mitre/AttackPathTimeline.tsx` | 時序視圖元件 |
| 前端 整合 | `frontend/src/app/navigator/page.tsx`（待確認） | Navigator 頁面整合 |
| 後端 測試 | `backend/tests/test_techniques_router.py` | 包含 attack-path 相關測試 |
| E2E 測試 | （待實作） | 前端 E2E 尚未覆蓋 AttackPathTimeline |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

### 後端

| 指標名稱 | 類型 | 標籤 | 告警閾值 |
|----------|------|------|----------|
| `athena_attack_path_query_duration_seconds` | Histogram | `operation_id` | P95 > 2s |
| `athena_attack_path_entries_count` | Gauge | `operation_id` | — |
| `athena_attack_path_highest_tactic_idx` | Gauge | `operation_id` | — |
| `athena_attack_path_errors_total` | Counter | `error_type` | > 10/min |

### 前端

N/A（純展示元件，無需前端可觀測性指標）

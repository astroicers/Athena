# SPEC-024：Phase F — UX 精修 + LLM 監控 + Web Terminal + Topology Tab

> 傘形 SPEC，覆蓋 Phase F 所有新增/修改模組。已實作完成，補建 SPEC 以符合 ASP Pre-Implementation Gate。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-024 |
| **關聯 ADR** | 無新架構決策（功能性改善 + 互動性增強）；Web Terminal 複用 ADR-015（DirectSSHEngine 架構） |
| **估算複雜度** | 高（跨 10+ 前端元件 + 2 後端 router + 1 後端 service） |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |
| **tech-debt** | 無 |

---

## 🎯 目標（Goal）

> 解決 4 個實際使用後發現的問題：(1) LLM 分析過程完全黑盒，無法監控 (2) OODA Timeline 資料量爆炸難以閱讀 (3) AI Recommendation 無歷史可查 (4) Compromised 機器無法下指令。同時改善拓撲圖可用性（節點縮小 + 獨立 Tab + 點擊詳情）。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `operation_id` | str | URL path | 已存在的作戰 ID |
| `target_id` | str | URL path（terminal） | 必須 `is_compromised = 1` |
| `cmd` | str | WebSocket JSON `{"cmd": "..."}` | 長度 ≤ 1024；非破壞性指令 |
| `limit` | int | Query param（recommendations） | 1–100，預設 20 |

---

## 📤 預期輸出（Expected Output）

### 後端

1. **`GET /operations/{op_id}/recommendations?limit=N`** 回傳最近 N 筆 `OrientRecommendation` 列表（降冪排序）
2. **`WS /ws/{op_id}/targets/{target_id}/terminal`** 建立 SSH 連線後：
   - 連線成功：`{"output": "Connected to ...", "exit_code": 0, "prompt": "user@host:~$ "}`
   - 執行指令：`{"output": "...", "exit_code": N, "prompt": "..."}`
   - 失敗：`{"error": "..."}`
3. **`WS /ws/{op_id}`** 的 `orient.thinking` 事件：
   - LLM 呼叫前：`{"status": "started", "backend": "api_key"}`
   - LLM 呼叫後：`{"status": "completed", "backend": "api_key", "latency_ms": 1234}`

### 前端

1. Monitor 頁面 AIDecisionPanel 顯示 LLM 分析中/latency 狀態
2. OODA Timeline 支援摺疊、ORIENT 截斷、phase filter、show all N
3. Monitor 頁面顯示 Recommendation History 可摺疊面板（最多 20 筆）
4. Planner 頁面 compromised 目標旁出現 `▶ Terminal` 按鈕
5. TerminalPanel modal 可執行互動式 SSH 命令，含輸入歷史（↑↓）
6. Monitor 頁面頂部 `[OVERVIEW]` / `[TOPOLOGY]` Tab 切換
7. TOPOLOGY Tab 中拓撲圖佔 3/4 寬，動態高度填滿視窗
8. 點擊拓撲節點 → 右側 NodeDetailPanel 顯示 IP/OS/角色/狀態/Kill Chain/Facts

---

## ✅ Done When

- [x] `GET /operations/{op_id}/recommendations` 回傳列表，HTTP 200
- [x] WebSocket terminal 連線到 compromised target，`whoami` 回傳正確 username
- [x] 破壞性指令（`rm -rf /`）被拒絕，回傳 error
- [x] Monitor AIDecisionPanel 在 ORIENT 階段顯示 `● ANALYZING...`
- [x] OODA Timeline 預設只展開最新 1 個 iteration，舊的摺疊
- [x] ORIENT 文字超 150 字元顯示截斷 + `[展開]`
- [x] Phase filter chips 正常篩選
- [x] Recommendation History 面板顯示歷史列表
- [x] Planner 頁面 compromised target 出現 TERMINAL 按鈕
- [x] TerminalPanel ↑↓ 瀏覽歷史正常
- [x] Monitor 頁面顯示 OVERVIEW / TOPOLOGY Tab 切換
- [x] TOPOLOGY Tab 拓撲圖填滿 3/4 寬，Kill Chain 條貼底部
- [x] 點擊節點 → NodeDetailPanel 顯示 facts
- [x] ACCEPT RECOMMENDATION 按鈕已移除
- [x] Modal 背景為純黑（非半透明）
- [x] 無目標時 OODA CYCLE / EXPORT / EXECUTE MISSION 按鈕 disabled
- [x] `pytest` 227 passed
- [x] `tsc --noEmit` clean

---

## 🔧 實作範圍（Edge Cases & Constraints）

### Web Terminal 安全限制

```python
_CMD_BLACKLIST = ("rm -rf /", "mkfs", "dd if=/dev/zero", "> /dev/sda", "shred /dev")
MAX_CMD_LEN = 1024
```

- 每條指令 timeout 30s（asyncssh `conn.run(cmd, timeout=30)`）
- 只允許 `is_compromised = 1` 的 target
- credentials 從 `facts` 表的 `trait = 'credential.ssh'` 讀取（格式 `user:pass@host:port`）
- SSH 連線使用 `known_hosts=None`（lab 環境，非生產）

### OODA Timeline 截斷規則

- ORIENT 文字 > 150 字元：截斷 + `[展開]` 按鈕（per-entry state，key = `${iteration}-${phase}`）
- 預設展開最新 1 個 iteration（`defaultExpandLatest = 1`）
- 預設顯示最新 3 個 iteration，`[顯示全部 N 筆]` 按鈕
- phase filter：ALL / OBS / ORI / DEC / ACT（多選 = full display）

### TopologyView 高度計算

```typescript
const PAGE_CHROME = 216; // header(48) + KPI(80) + tabs(40) + spacing(48)
const graphHeightPx = Math.max(300, window.innerHeight - PAGE_CHROME - kcHeight - GAP);
```

- 使用 `ResizeObserver` 動態測量 Kill Chain bar 高度
- NodeDetailPanel 用 `h-full` 與拓撲圖同高

---

## 📂 影響檔案

### 新增
| 檔案 | 說明 |
|------|------|
| `backend/app/routers/terminal.py` | WebSocket SSH terminal 端點 |
| `frontend/src/hooks/useTerminal.ts` | Terminal WebSocket hook |
| `frontend/src/components/terminal/TerminalPanel.tsx` | Terminal modal UI |
| `frontend/src/components/topology/TopologyView.tsx` | Topology Tab 全頁佈局 |
| `frontend/src/components/topology/NodeDetailPanel.tsx` | 節點詳情側欄 |

### 修改
| 檔案 | 改動摘要 |
|------|----------|
| `backend/app/routers/recommendations.py` | 新增 list endpoint（GET + Query param limit） |
| `backend/app/services/orient_engine.py` | 廣播 `orient.thinking` WS 事件（started/completed + latency_ms） |
| `backend/app/main.py` | include terminal router |
| `frontend/src/app/monitor/page.tsx` | TabBar + activeTab + orient.thinking 訂閱 + recHistory state + 歷史面板 |
| `frontend/src/app/planner/page.tsx` | TERMINAL 按鈕 + terminalTarget state + disabled 條件 |
| `frontend/src/components/topology/AIDecisionPanel.tsx` | llmThinking/llmBackend/llmLatencyMs props + 狀態列 UI |
| `frontend/src/components/topology/NetworkTopology.tsx` | onNodeClick/nodeSizeMultiplier/height props；節點縮小 |
| `frontend/src/components/ooda/OODATimeline.tsx` | 全元件重寫（摺疊/截斷/filter） |
| `frontend/src/components/ooda/RecommendationPanel.tsx` | 移除 ACCEPT 按鈕及相關 props |
| `frontend/src/components/modal/AddTargetModal.tsx` | Modal overlay `bg-black/60` → `bg-black` |
| `frontend/src/components/modal/ReconResultModal.tsx` | Modal overlay `bg-black/60` → `bg-black` |
| `frontend/src/components/modal/HexConfirmModal.tsx` | Modal overlay `bg-black/60` → `bg-black` |

---

## 🧪 測試策略

### 後端（pytest）

- `test_recommendations_list`：`GET /recommendations?limit=5` 回傳 ≤ 5 筆、HTTP 200
- `test_terminal_ws_no_target`：連線到不存在 target → `{"error": "Target not found"}`
- `test_terminal_ws_not_compromised`：is_compromised=0 → `{"error": "Target is not compromised"}`
- `test_orient_thinking_broadcast`：mock ws_manager，確認 `orient.thinking` 事件廣播兩次（started + completed）

### 前端（Vitest）

- `RecommendationPanel.test.tsx`：確認「ACCEPT RECOMMENDATION」button 不存在
- `OODATimeline.test.tsx`：超過 150 字元 ORIENT 文字截斷；phase filter 隱藏非選中 phase
- `TerminalPanel.test.tsx`：↑↓ 鍵瀏覽歷史；sendCommand 呼叫 addEntry("input", cmd)

---

_SPEC 由 Claude Sonnet 4.6 於 2026-03-04 補建，對應 Phase F 實作。_

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| 新增 WebSocket terminal endpoint | 前端開啟 TerminalPanel modal | `backend/app/routers/terminal.py`, `backend/app/main.py` | pytest `test_terminal_router.py` + `test_terminal.py` |
| orient_engine 廣播 `orient.thinking` WS 事件 | OODA ORIENT 階段 LLM 呼叫 | `backend/app/services/orient_engine.py`, `frontend/src/app/monitor/page.tsx`（待確認） | pytest `test_orient_engine.py` 驗證 mock ws 廣播 |
| recommendations endpoint 新增 | Monitor 頁面載入歷史列表 | `backend/app/routers/recommendations.py` | pytest `test_recommendations_router.py` |
| Modal overlay 改為純黑背景 | 任何 Modal 開啟 | `AddTargetModal`, `ReconResultModal`, `HexConfirmModal` | 視覺驗證 |
| OODA Timeline 元件全面重寫 | Monitor 頁面渲染 | `frontend/src/components/ooda/OODATimeline.tsx` | Unit test `OODATimeline.test.tsx` |

---

## ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| 1. Revert terminal router + main.py include | 無 DB schema 變動 | `/ws/{op_id}/targets/{tid}/terminal` 回傳 404 | ✅ |
| 2. Revert orient_engine `orient.thinking` 廣播 | 無資料影響 | Monitor 頁面不顯示 LLM 分析狀態 | ✅ |
| 3. Revert recommendations list endpoint | 無資料影響 | `GET /recommendations` 回傳 404 | ✅ |
| 4. Revert 前端元件（OODATimeline, TerminalPanel, TopologyView, NodeDetailPanel） | 無持久化資料影響 | 前端恢復舊版 UI | ✅ 可分別 revert |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參考 |
|----|------|------|----------|----------|
| P1 | 正向 | Compromised target 開啟 terminal，執行 `whoami` | 回傳正確 username，exit_code=0 | Scenario: Terminal 執行合法指令 |
| P2 | 正向 | Monitor 頁面 ORIENT 階段 LLM 呼叫 | AIDecisionPanel 顯示 `ANALYZING...` + latency | — |
| P3 | 正向 | OODA Timeline 有 5 個 iteration | 最新 1 個展開，其餘摺疊，顯示 `[顯示全部 5 筆]` | — |
| N1 | 負向 | Terminal 執行破壞性指令 `rm -rf /` | 回傳 error，指令被拒絕 | Scenario: Terminal 拒絕破壞性指令 |
| N2 | 負向 | 連線到 `is_compromised=0` 的 target | 回傳 `{"error": "Target is not compromised"}` | — |
| N3 | 負向 | 連線到不存在的 target | 回傳 `{"error": "Target not found"}` | — |
| B1 | 邊界 | ORIENT 文字恰好 150 字元 | 完整顯示，不截斷，無 `[展開]` 按鈕 | Scenario: ORIENT 截斷邊界 |
| B2 | 邊界 | ORIENT 文字 151 字元 | 截斷顯示 + `[展開]` 按鈕 | Scenario: ORIENT 截斷邊界 |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Phase F — UX 精修 + Terminal + Topology
  Background:
    Given 已建立作戰 "OP-DELTA"
    And 作戰包含 compromised target "10.0.0.15"（is_compromised=1）

  Scenario: Terminal 執行合法指令
    Given 使用者在 Planner 頁面點擊 target 旁的 TERMINAL 按鈕
    When 在 TerminalPanel 輸入 "whoami"
    Then 收到包含 username 的 output
    And exit_code 為 0
    And prompt 顯示 "user@host:~$"

  Scenario: Terminal 拒絕破壞性指令
    Given 使用者已開啟 TerminalPanel
    When 輸入 "rm -rf /"
    Then 收到 error response
    And 指令未在遠端執行

  Scenario: ORIENT 截斷邊界
    Given OODA iteration 的 ORIENT 分析文字為 160 字元
    When 使用者查看 OODA Timeline
    Then ORIENT 文字截斷至 150 字元
    And 顯示 "[展開]" 按鈕
    When 使用者點擊 "[展開]"
    Then 顯示完整 160 字元文字

  Scenario: Topology Tab 節點詳情
    Given 使用者在 Monitor 頁面切換到 TOPOLOGY Tab
    When 點擊拓撲圖中的某節點
    Then 右側 NodeDetailPanel 顯示 IP、OS、角色、狀態
    And 顯示 Kill Chain 進度
    And 顯示相關 Facts 列表
```

---

## 🔍 追溯性（Traceability）

| 類型 | 檔案路徑 | 說明 |
|------|----------|------|
| 後端 Router | `backend/app/routers/terminal.py` | WebSocket SSH terminal endpoint |
| 後端 Router | `backend/app/routers/recommendations.py` | `GET /recommendations` endpoint |
| 後端 Service | `backend/app/services/orient_engine.py` | `orient.thinking` WS 事件廣播 |
| 前端 Hook | `frontend/src/hooks/useTerminal.ts` | Terminal WebSocket hook |
| 前端 元件 | `frontend/src/components/terminal/TerminalPanel.tsx` | Terminal modal UI |
| 前端 元件 | `frontend/src/components/ooda/OODATimeline.tsx` | OODA Timeline（摺疊/截斷/filter） |
| 後端 測試 | `backend/tests/test_terminal_router.py` | Terminal router 測試 |
| 後端 測試 | `backend/tests/test_terminal.py` | Terminal 功能測試 |
| 後端 測試 | `backend/tests/test_orient_engine.py` | orient thinking 廣播測試 |
| 後端 測試 | `backend/tests/test_recommendations_router.py` | Recommendations 列表測試 |
| 前端 測試 | `frontend/src/components/terminal/__tests__/TerminalPanel.test.tsx` | TerminalPanel unit test |
| 前端 測試 | `frontend/src/components/ooda/__tests__/OODATimeline.test.tsx` | OODATimeline unit test |
| E2E 測試 | `frontend/e2e/sit-terminal.spec.ts` | Terminal SIT 測試 |
| E2E 測試 | `frontend/e2e/sit-error-handling.spec.ts` | 錯誤處理 SIT 測試 |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

### 後端

| 指標名稱 | 類型 | 標籤 | 告警閾值 |
|----------|------|------|----------|
| `athena_terminal_session_duration_seconds` | Histogram | `target_id` | P95 > 300s |
| `athena_terminal_command_total` | Counter | `target_id`, `blocked` (`true`, `false`) | `blocked=true` > 10/min |
| `athena_terminal_connection_errors_total` | Counter | `error_type` (`not_found`, `not_compromised`, `ssh_failed`) | > 5/min |
| `athena_orient_thinking_latency_ms` | Histogram | `operation_id`, `backend` | P95 > 10000ms |
| `athena_recommendations_query_total` | Counter | `operation_id` | — |

### 前端

N/A

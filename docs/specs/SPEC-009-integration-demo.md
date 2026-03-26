# SPEC-009：整合與 Demo 場景

> 端對端 Demo「OP-2024-017 PHANTOM-EYE」+ 7 種 WebSocket 事件驗證。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-009 |
| **關聯 ADR** | ADR-007（WebSocket 7 事件）、ADR-012（C5ISR 框架映射） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | strict |

---

## 🎯 目標（Goal）

> 驗證 Athena 完整端對端流程：從種子資料載入到 OODA 循環執行到 UI 即時更新，確保所有元件正確整合。同時建立可重現的 Demo 腳本，讓「OP-2024-017 PHANTOM-EYE」場景在 UI 上可視化運行。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| Demo 流程 | 文件 | ROADMAP Phase 6.1 | 6 步驟 OODA 循環 |
| 7 種 WebSocket 事件 | ADR | ADR-007 + ROADMAP Phase 6.2 | 事件名稱與格式嚴格對映 |
| 種子資料 | SPEC | SPEC-003 輸出 | OP-2024-017 完整資料 |
| 4 個畫面 | SPEC | SPEC-006 輸出 | 所有畫面渲染正確 |
| OODA 引擎 | SPEC | SPEC-007 輸出 | 6 服務可運作 |
| 執行引擎 | SPEC | SPEC-008 輸出 | mock 模式可用 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. Demo 流程腳本

按 ROADMAP Phase 6.1 定義，完整 Demo 包含 6 步驟的 OODA 循環：

```
步驟 1：OBSERVE — Agent 回報網路掃描結果
  - 前置：種子資料已載入（4 個 Agent, 5 個 Target）
  - 動作：系統顯示 T1595.001 Active Scanning 已完成
  - 預期 UI：
    - /monitor：3D 拓樸顯示 5 個節點 + 掃描連線
    - /monitor：日誌顯示 "Active Scanning completed"
    - /c5isr：Cyber 域 health 更新

步驟 2：ORIENT — PentestGPT 分析態勢
  - 動作：POST /api/operations/{id}/ooda/trigger
  - 預期 UI：
    - /c5isr：OODA 指示器切換至 ORIENT
    - /c5isr：PentestGPT 推薦卡更新（T1003.001, confidence=87%）
    - /navigator：對應技術高亮
  - WebSocket 事件：ooda.phase(orient), recommendation

步驟 3：DECIDE — 指揮官審閱建議
  - 動作：指揮官在 UI 查看 3 個選項
  - 預期 UI：
    - /c5isr：RecommendCard 顯示 3 個 TacticalOption
    - /planner：任務步驟表更新
  - 如果 risk_level=HIGH → HexConfirmModal 彈出
  - 動作：POST /api/operations/{id}/recommendations/{rid}/accept

步驟 4：ACT — Caldera 執行 LSASS dump
  - 動作：系統透過 engine_router 路由至 Caldera（或 mock）
  - 預期 UI：
    - /monitor：3D 拓樸顯示執行中連線（脈動動畫）
    - /planner：步驟 #02 狀態 → running → completed
    - /navigator：T1003.001 格子變綠（success）
  - WebSocket 事件：execution.update(running), execution.update(success)

步驟 5：OBSERVE（第二輪）— 新情報收集
  - 動作：fact_collector 萃取 LSASS dump 結果
  - 預期 UI：
    - /monitor：日誌顯示 "Credential harvested: CORP\Administrator"
    - /c5isr：ISR 域 health 更新
  - WebSocket 事件：fact.new, log.new

步驟 6：ORIENT（第二輪）— PentestGPT 更新建議
  - 動作：orient_engine 分析新情報
  - 預期 UI：
    - /c5isr：RecommendCard 更新為新建議
    - /c5isr：OODA 迭代計數 +1
  - WebSocket 事件：recommendation, ooda.phase(orient)

→ 循環持續...
```

### 2. WebSocket 事件驗證清單

| 事件 | 觸發時機 | 消費畫面 | 驗證方式 |
|------|---------|---------|---------|
| `log.new` | 日誌產生 | Battle Monitor | 即時日誌列表更新 |
| `agent.beacon` | Agent 心跳 | Battle Monitor | 狀態燈號閃爍 |
| `execution.update` | 技術狀態變更 | Navigator, Planner | 矩陣格/步驟狀態即時更新 |
| `ooda.phase` | OODA 階段切換 | C5ISR Board, Planner | OODA 指示器同步 |
| `c5isr.update` | 域健康度變更 | C5ISR Board | DomainCard health bar 更新 |
| `fact.new` | 新情報收集 | C5ISR Board | 情報計數更新 |
| `recommendation` | PentestGPT 新建議 | C5ISR Board, Navigator | RecommendCard 更新 |

事件格式驗證：

```json
{
  "event": "execution.update",
  "data": {
    "execution_id": "...",
    "technique_id": "T1003.001",
    "status": "success",
    "target_id": "..."
  },
  "timestamp": "2026-02-23T10:30:00Z"
}
```

### 3. Demo 輔助腳本（選用）

```
backend/app/seed/demo_runner.py
```

一鍵執行 Demo 流程的自動化腳本：
- 使用 `httpx` 依序呼叫 API
- 每步之間 `sleep(DEMO_STEP_DELAY)` 供觀看者跟隨（環境變數 `DEMO_STEP_DELAY`，預設 3 秒）
- 輸出每步的預期結果和實際結果
- 可配合 `MOCK_LLM=true` 在無 API key 下運行

### 4. 健康檢查端點

```
GET /api/health
```

回傳：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "services": {
    "database": "connected",
    "caldera": "connected" | "disconnected" | "mock",
    "shannon": "connected" | "disabled",
    "websocket": "active",
    "llm": "mock" | "claude" | "openai" | "unavailable"
  }
}
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| Caldera 不可用 | Mock 模式自動啟用，Demo 繼續 |
| LLM API 不可用 | `MOCK_LLM=true` 自動啟用 |
| WebSocket 斷線 | 前端顯示 reconnecting 狀態 |
| 種子資料未載入 | Demo runner 先檢查並自動載入 |

---

## ⚠️ 邊界條件（Edge Cases）

- Demo 必須在 `MOCK_LLM=true` + 無 Caldera 的環境下可完整運行（mock all）
- WebSocket 事件推送的順序必須與 OODA 階段一致（先 ooda.phase → 再 recommendation）
- Demo runner 需處理 API 回傳非 200 的情況（retry 一次後跳過）
- 3D 拓樸在 Demo 中需動態新增/修改連線（execution.update 觸發）
- HexConfirmModal 在 Demo 中需手動操作（不自動關閉）
- 日誌串流在 Demo 開始前應清空（或從指定時間點開始）
- 健康檢查端點不需身份驗證（ADR-011）

---

## ✅ 驗收標準（Done When）

- [x] `docker-compose up` + 開啟 `localhost:3000` → 種子資料自動載入，4 畫面渲染正確
- [x] 手動觸發 `POST /api/operations/{id}/ooda/trigger` → 完整 OODA 循環執行
- [x] 所有 7 種 WebSocket 事件可在 browser console 觀察到
- [x] `/c5isr` 的 OODA 指示器在循環中正確切換（observe → orient → decide → act）
- [x] `/c5isr` 的 RecommendCard 在 Orient 完成後更新
- [x] `/navigator` 的 MITRECell 在 execution.update 後變色
- [x] `/monitor` 的日誌串流在 log.new 事件後自動滾動
- [x] `/monitor` 的 Agent 信標在 agent.beacon 後閃爍
- [x] `GET /api/health` 回傳所有服務狀態
- [x] `MOCK_LLM=true` + 無 Caldera 下完整 Demo 可執行

---

## 🚫 禁止事項（Out of Scope）

- 不要實作多次自動 OODA 迭代——Demo 手動觸發每輪
- 不要建立 E2E 自動化測試框架（Cypress/Playwright）——手動驗證
- 不要實作完整 Caldera operation 管理——使用 mock
- 不要建立影片/GIF 錄製工具——Phase 7 範圍
- 不要修改 SPEC-003 的種子資料——使用已定義的值

---

## 📎 參考資料（References）

- ROADMAP：Phase 6.1（Demo 流程）、Phase 6.2（WebSocket 事件流）
- ADR-007：[WebSocket 即時通訊](../adr/ADR-007-websocket-realtime-communication.md)
- ADR-012：[C5ISR 框架映射](../adr/ADR-012-c5isr-framework-mapping.md)
- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 8（Seed Data）
- SPEC-003：種子資料（依賴）
- SPEC-006：4 畫面（依賴）
- SPEC-007：OODA 引擎（依賴）
- SPEC-008：執行引擎客戶端（依賴）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->

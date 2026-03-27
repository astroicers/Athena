# SPEC-026：動態攻擊情勢圖（Attack Situation Diagram）

> 純 SVG + React 即時攻擊情勢圖，整合 Kill Chain 進度 + OODA 環形指示器 + C5ISR 健康條。已實作完成，補建 SPEC 以符合 ASP Pre-Implementation Gate。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-026 |
| **關聯 ADR** | 無新架構決策（純前端視覺化元件，消費現有 WebSocket 事件，零新依賴） |
| **估算複雜度** | 中（1 hook + 5 SVG 元件 + Monitor 頁面整合） |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |
| **tech-debt** | 無 |

---

## 🎯 目標（Goal）

> 提供類似 mermaid 的動態流程圖，即時顯示 Kill Chain 7 階段進度、OODA 循環當前 phase、C5ISR 6 域健康度。透過現有 WebSocket 事件（`execution.update`、`ooda.phase`、`c5isr.update`）即時更新，不新增後端 endpoint。

### 設計決策

選擇**純 SVG + React** 而非：
- mermaid.js（~400KB，不支援即時更新）
- react-flow（~150KB，過重）
- elkjs（~200KB WASM）

與專案既有 custom Canvas rendering（NetworkTopology）保持一致的輕量路線。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `techniques` | TechniqueExecution[] | Monitor 頁面 state | 已 fetch 的技術列表 |
| `oodaPhase` | string \| null | WebSocket `ooda.phase` | OBSERVE / ORIENT / DECIDE / ACT |
| `executionUpdate` | object \| null | WebSocket `execution.update` | 含 `techniqueId` + `status` |
| `c5isrDomains` | C5ISRDomain[] | GET `/api/operations/{op_id}/c5isr` + WS `c5isr.update` | 6 域健康度 |

---

## 📤 預期輸出（Expected Output）

### 圖表結構

```
┌─────────────────────────────────────────────────────────┐
│  ╔═══════╗    ╔═══════╗    ╔═══════╗    ╔═══════╗      │
│  ║ RECON ║──▶ ║WEAPON ║──▶ ║DELIVER║──▶ ║EXPLOIT║──▶...│
│  ║ 3/5 ✓ ║    ║ 1/2 ✓ ║    ║ 0/1   ║    ║       ║      │
│  ╚═══════╝    ╚═══════╝    ╚═══════╝    ╚═══════╝      │
│       │                          ▲                       │
│       │         ┌────────────────┘                       │
│       │    ╭──────────╮                                  │
│       └───▶│ OODA Ring│  OBS → ORI → DEC → ACT          │
│            ╰──────────╯                                  │
│                                                          │
│  ┌CMD─┬CTRL┬COMM┬COMP┬CYBR┬─ISR┐  C5ISR Health Bar     │
│  │ 85%│ 70%│ 60%│ 90%│ 75%│ 80%│                        │
│  └────┴────┴────┴────┴────┴────┘                        │
└─────────────────────────────────────────────────────────┘
```

### 元件清單

| 元件 | 說明 |
|------|------|
| `AttackSituationDiagram` | 主容器（SVG viewBox 1200×300），含 CSS keyframe 動畫定義 |
| `SituationNode` | Kill Chain 階段方塊（140×70px），含階段名稱 + 技術計數 + 狀態色 |
| `SituationEdge` | 連接箭頭：completed（實線 cyan）、active（虛線 + 流動動畫）、pending（灰色虛線） |
| `OODARing` | 四段弧形（O/O/D/A），overlay 在當前活躍 stage 上，active phase 高亮 cyan |
| `C5ISRMiniBar` | HTML bar 6 個域方塊，百分比 + 色階（green > 70% / yellow > 40% / red ≤ 40%） |

### 資料 Hook

```typescript
interface SituationData {
  stages: SituationStage[];        // 7 個 kill chain 階段 + 技術統計
  currentStageIndex: number;       // 當前最高活躍階段
  oodaPhase: OODAPhase | null;     // 當前 OODA phase
  c5isrHealth: Record<string, number>; // 6 域健康度
  activeTechniqueId: string | null;
  overallProgress: number;         // 0-100%
}
```

### 整合位置

Monitor 頁面新增 **SITUATION** tab：

```typescript
const MONITOR_TABS = [
  { id: "overview", label: "OVERVIEW" },
  { id: "topology", label: "TOPOLOGY" },
  { id: "situation", label: "SITUATION" },
];
```

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| Monitor 頁面新增 SITUATION tab | 使用者切換至 SITUATION tab | Monitor 頁面（Tab 切換邏輯） | 手動確認 3 個 Tab 正確切換，無 console error |
| C5ISR WebSocket 訂閱新增 | SITUATION tab 載入時 | `c5isr.update` WS handler | 開啟 SITUATION tab 後觸發 C5ISR 更新，確認 MiniBar 即時刷新 |
| SVG viewBox 佔用 Monitor 頁面空間 | SITUATION tab 被選中 | Monitor 頁面整體 layout | 在不同視窗尺寸下確認 SVG 不溢出容器 |
| useSituationData hook 消費 techniques state | Monitor 頁面已 fetch techniques | Monitor 頁面 state 管理 | 確認 hook 正確接收 techniques 並分組為 7 個 Kill Chain stage |

---

## ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|---------|---------|---------|----------|
| `git revert` 對應 commit | 無 — 純前端 UI 元件，無資料庫變更 | Monitor 頁面僅顯示 OVERVIEW / TOPOLOGY 兩個 Tab | 是 |
| 若需保留 C5ISR fetch 邏輯，可選擇性 revert situation 元件 | 無 | C5ISR 資料仍可由其他元件消費 | 否（需手動驗證） |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參照 |
|----|------|------|---------|---------|
| P1 | 正向 | Monitor 頁面載入後切換至 SITUATION tab | 渲染 7 個 Kill Chain 節點 + 6 條連接箭頭 + OODA Ring + C5ISR MiniBar | Scenario: 正常載入 Situation Diagram |
| P2 | 正向 | 技術執行觸發 `execution.update` WS 事件 | 對應 stage 節點狀態即時更新（pending → active → completed） | Scenario: 即時更新 Kill Chain 進度 |
| P3 | 正向 | OODA phase 變更觸發 `ooda.phase` WS 事件 | OODA Ring 高亮對應 phase 弧形 | Scenario: 即時更新 Kill Chain 進度 |
| N1 | 負向 | techniques 清單為空（無任何技術資料） | 7 個節點全部顯示 pending 狀態（0/0），無 JS error | Scenario: 空資料狀態下顯示預設圖表 |
| N2 | 負向 | C5ISR API 回傳 500 | C5ISR MiniBar 顯示 N/A 或 0%，不阻塞 Kill Chain 渲染 | Scenario: 空資料狀態下顯示預設圖表 |
| B1 | 邊界 | 視窗 resize 至 768px 寬 | SVG preserveAspectRatio 正確縮放，節點不重疊 | Scenario: 正常載入 Situation Diagram |
| B2 | 邊界 | 所有 7 個 stage 同時為 active 狀態 | 所有節點同時 pulsing，動畫不衝突 | Scenario: 即時更新 Kill Chain 進度 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Attack Situation Diagram 即時視覺化
  Background:
    Given 使用者已登入並進入 Monitor 頁面
    And 至少一個 operation 處於 active 狀態

  Scenario: 正常載入 Situation Diagram
    When 使用者點擊 SITUATION tab
    Then 頁面渲染 7 個 Kill Chain 階段節點
    And 節點之間顯示 6 條連接箭頭
    And OODA Ring 顯示在當前活躍 stage 上方
    And C5ISR MiniBar 顯示 6 個域的健康百分比
    And SVG viewBox 在 1200x300 範圍內正確縮放

  Scenario: 即時更新 Kill Chain 進度
    Given 使用者已在 SITUATION tab
    When 後端廣播 execution.update 事件（technique 狀態變為 running）
    Then 對應 Kill Chain 階段節點從 pending 變為 active（pulsing 動畫）
    And 連接箭頭從灰色虛線變為虛線流動動畫
    When 後端廣播 ooda.phase 事件（phase 變為 ORIENT）
    Then OODA Ring 的 ORIENT 弧形高亮 cyan

  Scenario: 空資料狀態下顯示預設圖表
    Given operation 尚未執行任何技術
    When 使用者點擊 SITUATION tab
    Then 7 個節點全部顯示 pending 狀態
    And 節點計數顯示 0/0
    And OODA Ring 不高亮任何 phase
    And 頁面無 JavaScript console error
```

---

## 🔗 追溯性（Traceability）

| 追溯項目 | 檔案路徑 | 狀態 |
|---------|---------|------|
| 資料 Hook | `frontend/src/hooks/useSituationData.ts` | 已實作 |
| 主 SVG 容器 | `frontend/src/components/situation/AttackSituationDiagram.tsx` | （待確認檔案位置） |
| Kill Chain 節點 | `frontend/src/components/situation/SituationNode.tsx` | （待確認檔案位置） |
| 連接箭頭 | `frontend/src/components/situation/SituationEdge.tsx` | （待確認檔案位置） |
| OODA 環形指示器 | `frontend/src/components/situation/OODARing.tsx` | （待確認檔案位置） |
| C5ISR 健康條 | `frontend/src/components/situation/C5ISRMiniBar.tsx` | （待確認檔案位置） |
| 單元測試 | （待實作） | （待實作） |
| E2E 測試 | （待實作） | （待實作） |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

| 面向 | 內容 |
|------|------|
| **後端** | N/A — 本功能為純前端 SVG 視覺化元件，不涉及後端變更。WebSocket 事件消費使用既有 `execution.update`、`ooda.phase`、`c5isr.update`，無新增後端 endpoint 或日誌。 |
| **前端** | N/A |

---

## ✅ Done When

- [x] Monitor 頁面顯示 OVERVIEW / TOPOLOGY / SITUATION 三個 Tab
- [x] SITUATION tab 渲染 7 個 Kill Chain 節點 + 6 條連接箭頭
- [x] 節點顯示階段名稱 + 技術計數（成功/總數）
- [x] 節點依狀態顯示色彩：completed（亮色 + glow）、active（pulsing）、pending（dim）
- [x] 連接箭頭依狀態顯示：completed（實線 cyan）、active（虛線流動）、pending（灰色虛線）
- [x] OODA Ring overlay 在當前活躍 stage 上，4 段弧形，active phase 高亮
- [x] C5ISR MiniBar 顯示 6 域百分比 + 色階
- [x] C5ISR 資料透過 GET fetch + `c5isr.update` WS 即時更新
- [x] SVG viewBox 響應式（preserveAspectRatio）
- [x] `tsc --noEmit` clean
- [x] `next build` clean

---

## 🔧 實作範圍（Edge Cases & Constraints）

### Kill Chain 階段定義

複用 `NetworkTopology.tsx` 的 `KILL_CHAIN_COLORS` 色階：

| 階段 | Label | 色碼 |
|------|-------|------|
| reconnaissance | RECON | #00d4ff |
| weaponization | WEAPON | #ff6b6b |
| delivery | DELIVER | #ffd93d |
| exploitation | EXPLOIT | #ff8c42 |
| installation | INSTALL | #c471ed |
| command_and_control | C2 | #6c5ce7 |
| actions_on_objectives | ACTIONS | #00b894 |

### 節點狀態判定

```typescript
type StageStatus = "completed" | "active" | "pending";
// completed: succeeded > 0 且無 running
// active: 有 running 技術，或 currentStageIndex === stageIndex
// pending: 其餘
```

### SVG 動畫

- `SituationEdge` active 狀態：`stroke-dasharray: 8 4` + `stroke-dashoffset` animation 1s linear infinite
- `SituationNode` active 狀態：glow filter `feGaussianBlur stdDeviation=3` + `feComposite`

### C5ISR 資料整合

Monitor 頁面新增：
1. `c5isrDomains` state + GET fetch 於 `Promise.all`
2. `c5isr.update` WebSocket subscription（`useEffect`）

### 零後端變更

本功能完全消費現有事件，不新增任何 backend endpoint 或 WS 事件類型。

---

## 📂 影響檔案

### 新增
| 檔案 | 說明 |
|------|------|
| `frontend/src/hooks/useSituationData.ts` | 資料聚合 hook（techniques → stages 分組） |
| `frontend/src/components/situation/AttackSituationDiagram.tsx` | 主 SVG 容器 + CSS animations |
| `frontend/src/components/situation/SituationNode.tsx` | Kill Chain 階段方塊 |
| `frontend/src/components/situation/SituationEdge.tsx` | 連接箭頭 + 動畫 |
| `frontend/src/components/situation/OODARing.tsx` | OODA 環形指示器 |
| `frontend/src/components/situation/C5ISRMiniBar.tsx` | C5ISR 健康條 |

### 修改
| 檔案 | 改動摘要 |
|------|----------|
| `frontend/src/app/monitor/page.tsx` | 新增 SITUATION tab + `c5isrDomains` state + C5ISR fetch + WS 訂閱 |

---

## 🧪 測試策略

### 視覺驗收（人工）

- 瀏覽器開 `/monitor` → SITUATION tab，確認 7 節點 + 箭頭 + OODA Ring + C5ISR bar 正確渲染
- 執行 OODA cycle，觀察圖表即時更新
- 視窗 resize 驗證 SVG 響應式縮放

### 型別安全（自動）

- `tsc --noEmit` 確認無型別錯誤
- `next build` 確認編譯成功

---

_SPEC 由 Claude Opus 4.6 於 2026-03-04 補建，對應 Attack Situation Diagram 實作。_


# SPEC-006：4 畫面實作

> 像素級對齊 .pen 設計稿，實作 C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-006 |
| **關聯 ADR** | ADR-009（前端元件架構）、ADR-012（C5ISR 框架映射） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 根據 6 個 `.pen` 設計稿，實作 Athena 的 4 個核心畫面，每個畫面載入種子資料後可完整渲染。所有元件需像素級對齊設計稿，使用 SPEC-005 定義的佈局、型別與 Hooks。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| C5ISR Board 設計 | .pen | `athena-c5isr-board.pen` | 像素級對齊 |
| MITRE Navigator 設計 | .pen | `athena-mitre-navigator.pen` | 像素級對齊 |
| Mission Planner 設計 | .pen | `athena-mission-planner.pen` | 像素級對齊 |
| Battle Monitor 設計 | .pen | `athena-battle-monitor.pen` | 像素級對齊 |
| 設計系統 | .pen | `athena-design-system.pen` | 元件 1:1 對映 |
| UI-to-Data 映射 | 文件 | `data-architecture.md` Section 7 | 資料來源嚴格對映 |
| Hooks + 型別 | SPEC | SPEC-005 輸出 | 使用已定義的 hooks 和型別 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 畫面 1：C5ISR 指揮看板（`/c5isr`）

路徑：`frontend/src/app/c5isr/page.tsx`

| 區塊 | 元件 | 資料來源 |
|------|------|---------|
| KPI 列 | 4 張 `MetricCard` | `Operation.active_agents`, `.success_rate`, `.techniques_executed`, `.threat_level` |
| C5ISR 六域 | `C5ISRStatusBoard` → 6 張 `DomainCard` | `C5ISRStatus[]`（GET `/c5isr`） |
| OODA 指示器 | `OODAIndicator` | `Operation.current_ooda_phase` |
| PentestGPT 推薦 | `RecommendCard` | `PentestGPTRecommendation`（GET `/recommendations/latest`） |
| 作戰執行表 | `DataTable` | `TechniqueExecution[]` joined Technique + Target |
| 迷你拓樸 | 靜態/簡化版拓樸 | `Target[]` + topology edges |

專屬元件（`components/c5isr/`）：
- `C5ISRStatusBoard.tsx` — 六域狀態面板（2x3 grid）
- `DomainCard.tsx` — 單域狀態卡（域名 + 狀態 Badge + health ProgressBar + 細節）

### 畫面 2：MITRE 導航器（`/navigator`）

路徑：`frontend/src/app/navigator/page.tsx`

| 區塊 | 元件 | 資料來源 |
|------|------|---------|
| ATT&CK 矩陣 | `MITREMatrix` → 多個 `MITRECell` | `TechniqueWithStatus[]` grouped by tactic（GET `/techniques`） |
| Kill Chain 進度 | `KillChainIndicator` | 7 階段 + 各階段 completed count |
| 技術詳情 | `TechniqueCard` | 選中技術的詳情（名稱、描述、風險、執行紀錄） |
| PentestGPT 建議 | `RecommendCard`（複用） | `PentestGPTRecommendation` |

專屬元件（`components/mitre/`）：
- `MITRECell.tsx` — ATT&CK 矩陣格（技術 ID + 狀態色塊）
- `KillChainIndicator.tsx` — 7 階段橫向進度條

### 畫面 3：任務規劃器（`/planner`）

路徑：`frontend/src/app/planner/page.tsx`

| 區塊 | 元件 | 資料來源 |
|------|------|---------|
| 任務步驟表 | `DataTable` | `MissionStep[]`（GET `/mission/steps`） |
| OODA 時間軸 | `OODATimeline` → `OODATimelineEntry` | `OODAIteration[]`（GET `/ooda/timeline`） |
| 主機卡片 | 5 張 `HostNodeCard` | `Target[]`（GET `/targets`） |
| 步驟執行控制 | Execute 按鈕 + 狀態指示 | POST `/mission/execute` |

專屬元件（`components/ooda/`）：
- `OODAIndicator.tsx` — 四階段圓形/線性指示器（當前階段高亮）
- `OODATimelineEntry.tsx` — 時間軸單筆條目（時間 + 摘要 + 階段 Badge）

### 畫面 4：戰場監控（`/monitor`）

路徑：`frontend/src/app/monitor/page.tsx`

| 區塊 | 元件 | 資料來源 |
|------|------|---------|
| KPI 列 | 2 張 `MetricCard` | `Operation.data_exfiltrated_bytes`（2.4 MB Exfiltrated）、`Operation.active_agents`（12 Active Connections） |
| **3D 網路拓樸** | `NetworkTopology` | `TopologyData`（GET `/topology`） |
| Agent 信標面板 | `AgentBeacon` 列表 | `Agent[]`（GET `/agents`）+ `agent.beacon` WS |
| 即時日誌 | `LogStream` → `LogEntry` | `log.new` WebSocket 事件 |
| 威脅儀表 | `ThreatLevelGauge` | `Operation.threat_level` |

專屬元件（`components/topology/`）：
- `NetworkTopology.tsx` — react-force-graph-3d 封裝（`dynamic import, ssr: false`）
  - 節點：依 `Target.is_compromised` + `Agent.status` 著色的發光球體
  - 邊：8 種連線類型（攻擊路徑、C2 通道、掃描等），含粒子流動動畫
  - 互動：懸停顯示 tooltip、點擊顯示詳情面板
- `AttackNode.tsx` — 3D 拓樸中的攻擊節點渲染（自訂 Three.js 節點外觀，依狀態著色發光）
- `AttackVectorLine.tsx` — 攻擊向量連線渲染（箭頭方向 + 粒子流動 + 連線類型標籤）
- `TrafficStream.tsx` — 連線上的流量粒子串流動畫（封裝 Three.js 粒子系統，表示即時資料流）
- `ThreatLevelGauge.tsx` — 0-10 威脅等級半圓儀表

專屬元件（`components/data/`）：
- `DataTable.tsx` — 通用表格（排序、分頁、列按設計稿對齊）
- `LogEntry.tsx` — 單筆日誌（severity 色帶 + 時間 + 來源 + 訊息）
- `AgentBeacon.tsx` — Agent 狀態燈號（alive=綠色脈動、dead=紅色、pending=黃色）

專屬元件（`components/cards/`）：
- `MetricCard.tsx` — KPI 數據卡（標題 + 數值 + 變化趨勢）
- `HostNodeCard.tsx` — 主機節點卡（hostname + IP + role + 入侵狀態）
- `TechniqueCard.tsx` — 技術詳情卡（MITRE ID + 名稱 + 描述 + 風險 + 執行紀錄）
- `RecommendCard.tsx` — PentestGPT 推薦卡（situation + 3 options + confidence）

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| API 回傳空資料 | 顯示 empty state（「尚無資料」而非空白頁） |
| WebSocket 未連線 | 顯示 connection indicator（降級為 polling 或靜態渲染） |
| 3D 拓樸載入失敗 | 顯示 2D fallback 或 loading spinner |
| 種子資料未載入 | 各畫面顯示合理的空狀態 |

---

## ⚠️ 邊界條件（Edge Cases）

- `NetworkTopology` 必須使用 `dynamic(() => import('react-force-graph-3d'), { ssr: false })`（ADR-009）
- `MITRECell` 需依 `TechniqueStatus` 著色：success=綠、running=藍脈動、failed=紅、queued=灰、untested=暗灰、partial=黃
- `LogEntry` 需依 `LogSeverity` 著色：info=藍、success=綠、warning=橙、error=紅、critical=紅閃爍（含 `[SUCCESS] Domain Admin acquired` 等勝利日誌）
- `DomainCard` 的 status Badge 需依 `C5ISRDomainStatus` 著色（ADR-012 的 8 種語義）
- `OODAIndicator` 需在所有畫面（C5ISR Board、Planner）同步顯示當前階段（透過 `useOODA` hook）
- `DataTable` 需支援列排序（至少 step_number、status）
- `LogEntry` 在 Battle Monitor 中需自動滾動至底部（新日誌）
- `HexConfirmModal` 在 HIGH 風險操作時由 Mission Planner 的 Execute 按鈕觸發
- 自動化模式切換（MANUAL / SEMI_AUTO）位於 `PageHeader` 或 `Sidebar`，使用 `Toggle` 元件 + `PATCH /api/operations/{id}` 更新 `automation_mode`（data-architecture.md Section 7）
- 所有元件的深色主題色來自 `globals.css` 的 CSS Custom Properties

---

## ✅ 驗收標準（Done When）

- [x] `cd frontend && npm test` — 畫面元件測試全數通過
- [x] `/c5isr` — 4 張 KPI 卡片 + C5ISR 六域面板 + OODA 指示器 + 推薦卡 + 執行表 渲染正確
- [x] `/navigator` — ATT&CK 矩陣依 Tactic 分欄 + Kill Chain 進度 + 技術詳情面板 渲染正確
- [x] `/planner` — 任務步驟表 + OODA 時間軸 + 5 張主機卡片 渲染正確
- [x] `/planner` — [+ ADD] 按鈕觸發 `AddTargetModal`（Phase 13）
- [x] `/planner` — HostNodeCard [RECON SCAN] 按鈕觸發掃描 + `ReconResultModal` 顯示結果（Phase 13）
- [x] `/monitor` — 3D 拓樸 + Agent 信標 + 即時日誌 + 威脅儀表 渲染正確
- [x] `/monitor` — Kill Chain 節點彩色環形邊框 + `KillChainIndicator` 7 段進度條（Phase 13）
- [x] `/monitor` — `AIDecisionPanel` 顯示 AI 決策即時狀態（Phase 13）
- [x] 3D 拓樸在 `/monitor` 載入後無 SSR 錯誤
- [x] 所有畫面的種子資料正確渲染（數值、狀態、色彩對映）
- [ ] C5ISR 六域 health bar 顯示正確百分比（100%, 90%, 60%, 93%, 73%, 67%）— ⚠️ 實際值由 OODA 循環動態更新，與初始設計值不同
- [x] KPI 卡片顯示種子資料值（12 Agents、73% Success、47 Techniques、7.4 Threat）
- [x] 頁面切換無全頁重載（Next.js client-side navigation）

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 OODA 引擎的真實觸發邏輯——畫面僅顯示資料
- 不要實作 Caldera/Shannon 真實執行——Execute 按鈕呼叫 API stub
- 不要新增設計稿未定義的 UI 元素
- 不要使用 CSS-in-JS 或內聯樣式——使用 Tailwind utility classes
- 不要引入 chart library（如 recharts、d3）——使用 CSS/SVG 手繪
- 不要實作響應式/行動版佈局——僅桌面版（1920x1080 設計稿基準）

---

## 📎 參考資料（References）

- ADR-009：[前端元件架構](../adr/ADR-009-frontend-component-architecture.md)
- ADR-012：[C5ISR 框架映射](../adr/ADR-012-c5isr-framework-mapping.md)
- ADR-004：[半自動化模式](../adr/ADR-004-semi-auto-with-manual-override.md)（HexConfirmModal）
- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 7（UI-to-Data Traceability）
- 設計稿：`athena-c5isr-board.pen`、`athena-mitre-navigator.pen`、`athena-mission-planner.pen`、`athena-battle-monitor.pen`
- SPEC-005：前端基礎（依賴——型別、佈局、hooks、atoms）

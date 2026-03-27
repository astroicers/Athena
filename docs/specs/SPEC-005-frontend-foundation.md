# SPEC-005：前端基礎（型別 + 佈局 + Hooks）

> TypeScript 型別對映 + App Shell 佈局 + API/WebSocket Hooks + 原子元件。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-005 |
| **關聯 ADR** | ADR-009（前端元件架構）、ADR-007（WebSocket） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 建立前端基礎設施：TypeScript 型別定義（13 個型別檔案，對映後端 13 Enum + 12 Model）、App Shell 佈局元件（Sidebar + AlertBanner + PageHeader + CommandInput）、API 封裝與 WebSocket Hooks、以及可重用的原子/導航/對話框元件，為 Phase 4 的 4 畫面實作提供基礎。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 13 個 Enum 定義 | 文件 | `data-architecture.md` Section 2 | 1:1 對映後端 |
| 12 個 Model 定義 | 文件 | `data-architecture.md` Section 4 | 欄位名稱轉 camelCase |
| App Shell 設計 | .pen | `athena-shell.pen` | 像素級對齊 |
| 設計系統 | .pen | `athena-design-system.pen` | 32 個變數 + 56 個元件 |
| 7 種 WebSocket 事件 | ADR | ADR-007 | 事件名稱與格式 |
| API 端點清單 | SPEC | SPEC-004 | fetch 封裝 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. TypeScript 型別（`frontend/src/types/`）

| 檔案 | 匯出 | 備註 |
|------|------|------|
| `enums.ts` | 13 個 enum | 值使用 snake_case 字串對映後端 |
| `operation.ts` | `Operation` interface | 所有欄位 |
| `target.ts` | `Target` interface | |
| `agent.ts` | `Agent` interface | |
| `technique.ts` | `Technique`, `TechniqueWithStatus` | |
| `fact.ts` | `Fact` interface | |
| `ooda.ts` | `OODAIteration`, `OODATimelineEntry` | |
| `recommendation.ts` | `PentestGPTRecommendation`, `TacticalOption` | |
| `mission.ts` | `MissionStep` interface | |
| `c5isr.ts` | `C5ISRStatus` interface | |
| `log.ts` | `LogEntry` interface | |
| `api.ts` | `ApiResponse<T>`, `PaginatedResponse<T>`, `TopologyData`, `TopologyNode`, `TopologyEdge`, `WebSocketEvent` | |
| `index.ts` | 統一 re-export | |

型別命名規則：
- interface 欄位使用 camelCase（跟隨 TypeScript 慣例）
- enum 值使用 UPPER_SNAKE_CASE
- 後端 `snake_case` → 前端 `camelCase` 轉換在 API 層處理

### 2. 佈局元件（`frontend/src/components/layout/`）

| 元件 | 功能 | 設計稿對應 |
|------|------|-----------|
| `Sidebar.tsx` | 左側導航列：Logo + 4 個 NavItem + 系統狀態指示 + 使用者區塊 | `athena-shell.pen` Sidebar |
| `PageHeader.tsx` | 頁面標題 + 作戰代號 + 模式切換 Toggle | `athena-shell.pen` Header |
| `AlertBanner.tsx` | 全域警報橫幅（可收合） | `athena-shell.pen` AlertBanner |
| `CommandInput.tsx` | 底部指令輸入列 | `athena-shell.pen` CommandInput |

`app/layout.tsx` 根佈局：
```
┌──────────────────────────────────────────┐
│ AlertBanner (可選，固定頂部)              │
├──────┬───────────────────────────────────┤
│      │ PageHeader                        │
│ Side │──────────────────────────────────│
│ bar  │                                   │
│      │ {children} — 各畫面內容           │
│      │                                   │
│      │──────────────────────────────────│
│      │ CommandInput (固定底部)            │
└──────┴───────────────────────────────────┘
```

### 3. API 封裝（`frontend/src/lib/api.ts`）

```typescript
// Base URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
// Fetch 封裝：
//   - GET/POST/PATCH/DELETE 方法
//   - 自動 JSON parse
//   - 錯誤處理（非 2xx 拋出 ApiError）
//   - snake_case ↔ camelCase 自動轉換
```

### 4. Hooks（`frontend/src/hooks/`）

| Hook | 功能 | 依賴 |
|------|------|------|
| `useOperation.ts` | 管理當前作戰資料（GET + 自動刷新） | `lib/api.ts` |
| `useWebSocket.ts` | WebSocket 連線 + 7 種事件分發 + 自動重連 | `NEXT_PUBLIC_WS_URL` |
| `useOODA.ts` | 訂閱 OODA 階段變化（`ooda.phase` 事件） | `useWebSocket` |
| `useLiveLog.ts` | 即時日誌串流（`log.new` 事件 + 緩衝） | `useWebSocket` |

`useWebSocket` 核心介面：
```typescript
interface UseWebSocketReturn {
  isConnected: boolean;
  events: WebSocketEvent[];
  send: (data: unknown) => void;
  subscribe: (eventType: string, callback: (data: unknown) => void) => () => void;
}
```

### 5. 原子元件（`frontend/src/components/atoms/`）

| 元件 | Props | 設計稿對應 |
|------|-------|-----------|
| `Button.tsx` | `variant: "primary" \| "secondary" \| "danger"`, `size`, `disabled`, `onClick` | Design System Button |
| `Badge.tsx` | `variant: "success" \| "warning" \| "error" \| "info"`, `children` | Design System Badge |
| `StatusDot.tsx` | `status: AgentStatus \| C5ISRDomainStatus`, `pulse: boolean` | Design System StatusDot |
| `Toggle.tsx` | `checked`, `onChange`, `label` | Design System Toggle |
| `ProgressBar.tsx` | `value: number`, `max: number`, `variant` | Design System ProgressBar |
| `HexIcon.tsx` | `icon`, `size`, `variant` | Design System HexIcon |

### 5b. 導航元件（`frontend/src/components/nav/`）

| 元件 | Props | 設計稿對應 |
|------|-------|-----------|
| `NavItem.tsx` | `href`, `icon`, `label`, `isActive` | Shell Sidebar NavItem |
| `TabBar.tsx` | `tabs`, `activeTab`, `onChange` | Design System TabBar |

### 5c. 對話框元件（`frontend/src/components/modal/`）

| 元件 | Props | 設計稿對應 |
|------|-------|-----------|
| `HexConfirmModal.tsx` | `isOpen`, `title`, `riskLevel`, `onConfirm`, `onCancel` | Design System HexConfirmModal |

### 6. 常數（`frontend/src/lib/constants.ts`）

```typescript
export const NAV_ITEMS = [
  { href: "/c5isr", icon: "command", label: "C5ISR Board" },
  { href: "/navigator", icon: "mitre", label: "MITRE Navigator" },
  { href: "/planner", icon: "mission", label: "Mission Planner" },
  { href: "/monitor", icon: "monitor", label: "Battle Monitor" },
];

export const C5ISR_DOMAINS = ["command", "control", "comms", "computers", "cyber", "isr"] as const;

export const RISK_COLORS = { low: "green", medium: "yellow", high: "orange", critical: "red" } as const;
```

### 7. 全域樣式（`frontend/src/styles/globals.css`）

```css
@import "tailwindcss";

/* Athena Design Token — 從 athena-design-system.pen 映射 */
:root {
  --color-bg-primary: #0a0a1a;
  --color-bg-surface: #1a1a2e;
  --color-bg-elevated: #25253e;
  --color-accent: #00d4ff;
  --color-accent-hover: #33ddff;
  --color-text-primary: #ffffff;
  --color-text-secondary: #a0a0b0;
  --color-border: #2a2a4a;
  /* ... 其餘 24 個變數由設計稿映射決定 */
}
```

### 8. Tailwind 配置（`frontend/tailwind.config.ts`）

配置 Athena 自訂 Theme Token，映射 CSS Custom Properties：

```typescript
// extend.colors: athena-bg, athena-surface, athena-accent, etc.
// extend.fontFamily: mono for military feel
// content: ["./src/**/*.{ts,tsx}"]
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| API 不可用 | `useOperation` 返回 loading 狀態，不崩潰 |
| WebSocket 斷線 | `useWebSocket` 自動重連（exponential backoff） |
| 未知事件類型 | 記錄 console.warn，不拋錯 |

---

## ⚠️ 邊界條件（Edge Cases）

- `useWebSocket` 在 SSR 時不建立連線（`typeof window !== 'undefined'` 守衛）
- `useWebSocket` 自動重連策略：指數退避（1s → 2s → 4s → 8s → max 30s），重連時顯示 `isConnected: false`
- `HexConfirmModal` 的 `riskLevel` prop 決定確認按鈕顏色（CRITICAL = 紅色 + 雙重確認）
- `Sidebar` 需高亮當前路由的 NavItem（使用 `usePathname`）
- `app/page.tsx`（首頁）需 redirect 至 `/c5isr`
- Tailwind v4 使用 `@import "tailwindcss"` 而非 v3 的 `@tailwind base/components/utilities`
- 所有元件使用 `"use client"` 標記（因為使用 hooks 和事件處理）
- `api.ts` 的 snake_case ↔ camelCase 轉換需遞迴處理巢狀物件
- ADR-009 定義 10 個元件目錄：`layout/`、`atoms/`、`nav/`、`modal/` 由本 SPEC 建立；`cards/`、`data/`、`mitre/`、`ooda/`、`c5isr/`、`topology/` 由 SPEC-006 建立

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| TypeScript 型別變更影響全前端 | `types/*.ts` 中的 interface/enum 修改時 | 所有引用該型別的元件、hooks、pages | `npm run build` 無 TypeScript 錯誤 |
| App Shell 佈局變更影響所有頁面 | `layout.tsx`、`Sidebar.tsx`、`PageHeader.tsx` 修改時 | SPEC-006 的 4 個畫面（C5ISR、Navigator、Planner、Monitor） | 所有頁面在 Sidebar + Header 框架內正常渲染 |
| `useWebSocket` hook 變更影響即時功能 | WebSocket 連線邏輯或事件格式修改時 | `useOODA`、`useLiveLog`、所有訂閱 WS 事件的元件 | WebSocket 連線成功且事件正確分發 |
| CSS 變數（Design Token）變更影響全域主題 | `globals.css` 中的 `--color-*` 修改時 | 所有使用 Tailwind athena-* 色彩的元件 | 頁面背景色為深色軍事主題 |
| `lib/api.ts` snake_case/camelCase 轉換 | API 回應結構或轉換邏輯變更時 | 所有呼叫 API 的 hooks 與元件 | 前端資料物件欄位為 camelCase |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 1. `git revert <commit>` 還原前端基礎變更 2. 確認 SPEC-006 畫面元件尚未依賴（若已依賴需一併還原） 3. `npm run build` 確認編譯通過 |
| **資料影響** | 無資料影響——前端為純呈現層，不持久化任何資料 |
| **回滾驗證** | `npm run dev` 啟動成功；`localhost:3000` 渲染正常（或回退至空白頁） |
| **回滾已測試** | ☑ 否（前端基礎層，回滾等同重建 UI 框架） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | `npm run dev` 啟動前端 | 編譯成功，localhost:3000 可存取 | S1 |
| P2 | ✅ 正向 | 存取 `localhost:3000` | 渲染含 Sidebar 的 App Shell，自動 redirect 至 `/c5isr` | S1 |
| P3 | ✅ 正向 | `import { Operation, OODAPhase } from '@/types'` | TypeScript 編譯通過，型別定義完整 | S1 |
| P4 | ✅ 正向 | 渲染 Button、Badge、StatusDot 原子元件 | 元件正常顯示，variant props 切換樣式 | S1 |
| P5 | ✅ 正向 | `useWebSocket` 連線至 `ws://localhost:8000/ws/{id}` | `isConnected: true`，可接收事件 | S1 |
| N1 | ❌ 負向 | 後端 API 不可用時載入頁面 | `useOperation` 回傳 loading 狀態，頁面不崩潰 | S2 |
| N2 | ❌ 負向 | WebSocket 伺服器斷線 | `useWebSocket` 自動重連（指數退避），`isConnected: false` | S2 |
| N3 | ❌ 負向 | 未知 WebSocket 事件類型 | `console.warn` 記錄警告，不拋出錯誤 | S2 |
| B1 | 🔶 邊界 | SSR 環境下 `useWebSocket` | 不建立連線（`typeof window !== 'undefined'` 守衛） | S3 |
| B2 | 🔶 邊界 | `HexConfirmModal` riskLevel=CRITICAL | 確認按鈕為紅色 + 雙重確認流程 | S3 |
| B3 | 🔶 邊界 | WebSocket 重連策略達到最大退避 | 退避時間 cap 在 30s，持續嘗試重連 | S3 |

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-005 前端基礎（型別 + 佈局 + Hooks）
  作為 Athena 平台開發者
  我想要 完整的 TypeScript 型別、App Shell 佈局與 API/WebSocket Hooks
  以便 Phase 4 的 4 個畫面可直接使用基礎設施開發

  Background:
    Given frontend/ 目錄結構已建立（SPEC-001）
    And 後端 API 已啟動（SPEC-004）

  # --- 正向場景 ---

  Scenario: S1 - App Shell 佈局正確渲染
    Given 前端開發伺服器已啟動
    When 存取 localhost:3000
    Then 頁面自動 redirect 至 /c5isr
    And 左側顯示 Sidebar 含 4 個導航項目
    And 當前頁面的 NavItem 高亮顯示
    And 頁面背景色為 --color-bg-primary（深色軍事主題）
    And PageHeader 顯示頁面標題

  Scenario: S1b - TypeScript 型別完整對映後端
    Given types/ 目錄包含 13 個型別檔案
    When 從 index.ts 匯出所有型別
    Then 13 個 enum 與 12 個 interface 全部可用
    And enum 值使用 UPPER_SNAKE_CASE
    And interface 欄位使用 camelCase

  Scenario: S1c - 原子元件可正常渲染
    Given atoms/ 目錄包含 Button、Badge、StatusDot、Toggle、ProgressBar、HexIcon
    When 在頁面中渲染各元件
    Then 每個元件依照 variant props 顯示正確樣式
    And 符合 Deep Gemstone 設計系統規範

  # --- 負向場景 ---

  Scenario: S2 - 後端不可用時前端優雅降級
    Given 後端 API 未啟動
    When 存取 localhost:3000
    Then App Shell 佈局正常渲染
    And useOperation 回傳 loading 狀態
    And 頁面不顯示 JavaScript 錯誤

  # --- 邊界場景 ---

  Scenario: S3 - WebSocket SSR 守衛與自動重連
    Given 前端使用 Next.js SSR
    When 伺服端渲染 useWebSocket hook
    Then 不建立 WebSocket 連線
    And 客戶端 hydration 後自動建立連線
    And 斷線後以指數退避策略重連（max 30s）
```

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `frontend/src/types/enums.ts` | （TypeScript 編譯驗證） | 2026-03-26 |
| `frontend/src/types/operation.ts` | `frontend/src/hooks/__tests__/useOperation.test.ts` | 2026-03-26 |
| `frontend/src/types/ooda.ts` | `frontend/src/hooks/__tests__/useOODA.test.ts` | 2026-03-26 |
| `frontend/src/types/index.ts` | （TypeScript 編譯驗證） | 2026-03-26 |
| `frontend/src/components/layout/Sidebar.tsx` | `frontend/src/components/layout/__tests__/Sidebar.test.tsx` | 2026-03-26 |
| `frontend/src/components/layout/PageHeader.tsx` | `frontend/src/components/layout/__tests__/PageHeader.test.tsx` | 2026-03-26 |
| `frontend/src/components/atoms/Toggle.tsx` | `frontend/src/components/atoms/__tests__/Toggle.test.tsx` | 2026-03-26 |
| `frontend/src/components/atoms/StatusDot.tsx` | `frontend/src/components/atoms/__tests__/StatusDot.test.tsx` | 2026-03-26 |
| `frontend/src/components/atoms/ProgressBar.tsx` | `frontend/src/components/atoms/__tests__/ProgressBar.test.tsx` | 2026-03-26 |
| `frontend/src/components/nav/NavItem.tsx` | `frontend/src/components/nav/__tests__/TabBar.test.tsx` | 2026-03-26 |
| `frontend/src/components/modal/HexConfirmModal.tsx` | `frontend/src/components/modal/__tests__/HexConfirmModal.test.tsx`（待確認路徑） | 2026-03-26 |
| `frontend/src/lib/api.ts` | `frontend/src/lib/__tests__/api.test.ts` | 2026-03-26 |
| `frontend/src/hooks/useWebSocket.ts` | `frontend/e2e/full-workflow.spec.ts`（間接 E2E 驗證） | 2026-03-26 |
| `frontend/src/hooks/useOperation.ts` | `frontend/src/hooks/__tests__/useOperation.test.ts` | 2026-03-26 |
| `frontend/src/hooks/useOODA.ts` | `frontend/src/hooks/__tests__/useOODA.test.ts` | 2026-03-26 |
| `frontend/src/hooks/useLiveLog.ts` | `frontend/src/hooks/__tests__/useLiveLog.test.ts` | 2026-03-26 |
| `frontend/src/lib/constants.ts` | （TypeScript 編譯驗證） | 2026-03-26 |
| `frontend/src/app/layout.tsx` | `frontend/e2e/navigation.spec.ts` | 2026-03-26 |
| `frontend/src/lib/designTokens.ts` | （TypeScript 編譯驗證） | 2026-03-26 |

## 📊 可觀測性（Observability）

N/A（純前端 UI 變更）

---

## ✅ 驗收標準（Done When）

- [x] `cd frontend && npm test` — 前端基礎元件測試全數通過
- [x] `cd frontend && npm run dev` — 啟動成功
- [x] `localhost:3000` — 渲染含 Sidebar 的 App Shell
- [x] `localhost:3000` — 自動 redirect 至 `/c5isr`
- [x] Sidebar 顯示 4 個導航項目，當前頁面高亮
- [x] `frontend/src/types/index.ts` — 匯出所有 13 個 enum + 12 個 interface
- [x] `frontend/src/hooks/useWebSocket.ts` — 可建立 WebSocket 連線（console 無錯誤）
- [x] Button、Badge、StatusDot 等原子元件可在頁面中渲染
- [x] 頁面背景色為 `--color-bg-primary`（深色軍事主題）

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 4 個畫面的具體內容——SPEC-006 範圍
- 不要實作 3D 拓樸元件——SPEC-006 範圍
- 不要引入狀態管理庫（Redux、Zustand）——使用 React hooks + Context
- 不要使用 Tailwind v3 語法（`@tailwind base` 等）
- 不要建立測試檔案——POC 階段前端不強制測試
- 不要引入 CSS-in-JS 方案——使用 Tailwind utility classes

---

## 📎 參考資料（References）

- ADR-009：[前端元件架構](../adr/ADR-009-frontend-component-architecture.md)
- ADR-007：[WebSocket 即時通訊](../adr/ADR-007-websocket-realtime-communication.md)
- 專案結構：[project-structure.md](../architecture/project-structure.md) Section「前端應用層」
- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 2（Enums）+ Section 4（Models）
- 設計稿：`athena-shell.pen`、`athena-design-system.pen`
- SPEC-004：REST API Routes（依賴——API 端點定義）


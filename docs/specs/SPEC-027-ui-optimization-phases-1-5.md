# SPEC-027：UI Optimization Phases 1-5

> 全面提升 Athena C5ISR 平台前端 UI 的可讀性、響應式、視覺一致性與效能。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-027 |
| **關聯 ADR** | 無架構影響 — 純前端 UI/UX 改善 |
| **估算複雜度** | 高（跨 5 個 Phase、40+ 檔案） |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 解決 Athena 前端 UI 的可讀性不足（8-9px 字型、低對比度按鈕）、零響應式支援、視覺不一致（inline header 樣式分散）、缺少 SVG 視覺元素、以及 Monitor 頁面資訊架構問題（6 層垂直堆疊需大量捲動），使指揮控制平台更易於快速判讀。

---

## 📥 輸入規格（Inputs）

本 SPEC 為純前端 UI 改善，無 API 輸入變更。

修改基於以下分析結果：
- 全站 `text-[8px]` 6 處、`text-[9px]` 46+ 處
- `Button.tsx` primary variant 使用 20% 透明度
- 全站零個 `focus-visible` 樣式
- 全站零個 Tailwind 響應式前綴
- 3 個 Modal 使用不透明 backdrop
- 15+ 處 inline section header 字型大小不一致
- Monitor 頁面 6 層垂直堆疊

---

## 📤 輸出規格（Expected Output）

### Phase 1+2 — Quick Wins + SVG Card Enhancements
- QW-1: Primary Button 改為實心填充 `bg-athena-accent text-athena-bg`
- QW-2: 全域 `:focus-visible` 指示器（1px accent outline）
- QW-3: Modal backdrop 改為 `bg-athena-bg/80 backdrop-blur-sm`
- QW-4: 最小字型底線提升至 10px（`text-[8px]`/`text-[9px]` → `text-[10px]`）
- QW-5: 空狀態加入虛線邊框 + 引導文字
- QW-6: Button 加入 `icon` prop
- ME-6a: MetricCard SVG 迷你圓弧指標 + trend 指示器
- ME-6b: DomainCard SVG 六角邊框
- ME-6c: HostNodeCard SVG 狀態圖示（盾牌/雷達）
- ME-7: Planner 按鈕加入 SVG icon

### Phase 3 — Nav + Responsive + MITRE
- ME-3: 5 個 SVG 導航圖示取代 Unicode 字元
- ME-1: 響應式斷點（`grid-cols-2 lg:grid-cols-4` 等）
- ME-5: MITRE ATT&CK Matrix compact mode toggle

### Phase 4 — Components + Skeleton + Topology
- ME-2: SectionHeader 統一元件（page/card 兩級）
- ME-4: Loading Skeleton 取代全頁掃描線
- ME-8: Network Topology Canvas 節點角色圖示（DC/Server/Workstation/Router）

### Phase 5 — Dashboard Layout + Sidebar
- LI-1: Monitor 頁面改為固定高度 2x2 dashboard grid
- LI-2: 可收合側邊欄（expanded 224px ↔ collapsed 64px）+ SidebarContext
- LI-3: SlidePanel 右側抽屜元件（3 種寬度、backdrop blur、ESC 關閉）
- LI-4: VirtualList 虛擬捲動元件（viewport windowing、auto-scroll）

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| 全域字型底線提升至 10px | Phase 1 部署後 | 所有使用 `text-[8px]`/`text-[9px]` 的元件 | grep 全專案確認無 `text-[8px]`/`text-[9px]` |
| Button icon prop 新增 | Button 元件使用時 | 現有 Button 呼叫者 | `npm run build` 無型別錯誤（icon 為 optional） |
| SectionHeader 替換 inline header | Phase 4 部署後 | 15+ 使用 inline header 的元件 | 視覺審查所有 section header 字型一致 |
| Skeleton 替換 PageLoading | 頁面載入時 | 4 個使用 PageLoading 的頁面 | 載入時顯示 Skeleton 而非掃描線 |
| Monitor 佈局重組為 2x2 grid | Monitor 頁面載入時 | Monitor 頁面所有子元件 | 子元件適應 flex layout，無垂直捲動 |
| 可收合側邊欄 | 使用者點擊收合按鈕 | 所有頁面（via client-shell） | 內容區寬度隨 SidebarContext 狀態變化 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1: 1024px 以下螢幕，響應式斷點觸發 grid 重排
- Case 2: Sidebar collapsed 時 NavItem 只顯示 icon，需 title tooltip
- Case 3: VirtualList 空 items 陣列 → 顯示空狀態
- Case 4: SlidePanel ESC 按鍵在多個 panel 開啟時只關閉最上層
- Case 5: Monitor fixed layout 在極小視窗高度下的 overflow 處理

### ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|---------|---------|---------|----------|
| `git revert` 對應 commit（93182d6, 8f4b483, 3260d9c, f36af84） | 無 — 不涉及任何資料層 | `npm run build` 零錯誤；UI 回到最小字型 8px、透明按鈕樣式 | 是 |
| 若僅需回退特定 Phase，可選擇性 revert 單一 commit | 無 | 該 Phase 功能回退，其餘 Phase 不受影響 | 否（需手動驗證） |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參照 |
|----|------|------|---------|---------|
| P1 | 正向 | Primary Button 渲染 | 按鈕為實心填充 `bg-athena-accent`，文字可讀 | Scenario: UI 元件正確渲染 |
| P2 | 正向 | SectionHeader 替換 inline header | 所有頁面 section header 字型大小一致 | Scenario: UI 元件正確渲染 |
| P3 | 正向 | Monitor 頁面 2x2 dashboard grid | 4 個區塊固定高度不捲動 | Scenario: Monitor Dashboard 固定佈局 |
| N1 | 負向 | Button icon prop 未傳入 | 按鈕僅顯示文字，無 JS error | Scenario: UI 元件正確渲染 |
| N2 | 負向 | VirtualList items 為空陣列 | 顯示空狀態（虛線邊框 + 引導文字） | Scenario: UI 元件正確渲染 |
| B1 | 邊界 | 視窗寬度 1024px 觸發響應式斷點 | grid 從 4 欄重排為 2 欄 | Scenario: 響應式佈局斷點觸發 |
| B2 | 邊界 | Sidebar collapsed 時 NavItem | 僅顯示 icon + title tooltip | Scenario: 響應式佈局斷點觸發 |
| B3 | 邊界 | SlidePanel ESC 按鍵（多個 panel 開啟） | 僅關閉最上層 panel | Scenario: Monitor Dashboard 固定佈局 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: UI Optimization Phases 1-5 視覺品質提升
  Background:
    Given 使用者已登入 Athena 平台
    And 瀏覽器視窗寬度為 1440px

  Scenario: UI 元件正確渲染
    When 使用者瀏覽任意頁面
    Then 全站最小字型不低於 10px
    And Primary Button 為實心填充非透明
    And 所有可聚焦元素具有 focus-visible 指示器
    And Modal backdrop 使用 blur 效果
    And SectionHeader 元件字型大小一致（page 級與 card 級各一種）

  Scenario: 響應式佈局斷點觸發
    Given 使用者在任意包含 grid layout 的頁面
    When 視窗寬度縮小至 1024px 以下
    Then grid 從 4 欄重排為 2 欄
    And Sidebar 自動收合至 64px 寬度
    And NavItem 僅顯示 icon 並附帶 title tooltip

  Scenario: Monitor Dashboard 固定佈局
    When 使用者進入 Monitor 頁面
    Then 頁面顯示 2x2 固定高度 dashboard grid
    And 無需垂直捲動即可看到所有區塊
    And 子元件適應 flex layout 自動填滿容器
```

---

## 🔗 追溯性（Traceability）

| 追溯項目 | 檔案路徑 | 狀態 |
|---------|---------|------|
| SectionHeader 元件 | `frontend/src/components/atoms/SectionHeader.tsx` | 已實作 |
| Skeleton 元件 | `frontend/src/components/ui/Skeleton.tsx` | 已實作 |
| VirtualList 元件 | `frontend/src/components/ui/VirtualList.tsx` | 已實作 |
| SlidePanel 元件 | `frontend/src/components/ui/SlidePanel.tsx` | 已實作 |
| SidebarContext | `frontend/src/contexts/SidebarContext.tsx` | 已實作 |
| WarRoom 頁面整合 | `frontend/src/app/warroom/page.tsx` | 已實作 |
| Attack Surface 頁面 | `frontend/src/app/attack-surface/page.tsx` | 已實作 |
| Planner EngagementPanel | `frontend/src/components/planner/EngagementPanel.tsx` | 已實作 |
| Planner ObjectivesPanel | `frontend/src/components/planner/ObjectivesPanel.tsx` | 已實作 |
| 單元測試 — EngagementPanel | `frontend/src/components/planner/__tests__/EngagementPanel.test.tsx` | 已實作 |
| 單元測試 — ObjectivesPanel | `frontend/src/components/planner/__tests__/ObjectivesPanel.test.tsx` | 已實作 |
| E2E 測試 | （待實作） | （待實作） |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

| 面向 | 內容 |
|------|------|
| **後端** | N/A — 本功能為純前端 UI/UX 改善，不涉及後端 API 變更。 |
| **前端** | N/A |

---

## ✅ 驗收標準（Done When）

- [x] `npm run build` 零 TypeScript 錯誤
- [x] `npx vitest run` 全數通過（27 檔案 63 測試）
- [x] `text-[8px]` / `text-[9px]` 全域已清除
- [x] SVG 圖示風格一致：1.5px stroke、currentColor、線條風格
- [x] 響應式：1024px 斷點正確觸發 grid 重排
- [x] 已更新 `CHANGELOG.md`
- [x] Pencil mockup 已建立並歸檔

---

## 🚫 禁止事項（Out of Scope）

- 不修改後端 API
- 不修改資料模型
- 不引入新 npm 依賴

---

## 📎 參考資料（References）

- 設計稿: `design/athena-design-system.pen`（Phase 2-5 mockup frames）
- 實作計畫: `.claude/plans/gentle-cuddling-llama.md`
- SVG 風格參考: `ThreatLevelGauge.tsx`、`OODARing.tsx`

---

## 變更記錄

| 日期 | 變更 |
|------|------|
| 2026-03-04 | 建立 SPEC（追溯記錄，Phase 1-5 已實作完成） |


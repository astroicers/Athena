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

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| 全域字型底線 10px | 所有使用 8-9px 的元件 | 可讀性提升，佈局微幅調整 |
| Button icon prop | 現有 Button 呼叫者 | 無破壞性 — icon 為 optional prop |
| SectionHeader 元件替換 inline header | 15+ 元件 | 視覺統一，無功能變更 |
| Skeleton 替換 PageLoading | 4 個頁面 | 載入體驗改善 |
| Monitor 佈局重組 | Monitor 頁面所有子元件 | 固定高度不捲動，子元件需適應 flex layout |
| 可收合側邊欄 | 所有頁面（via client-shell） | 內容區寬度隨側邊欄狀態變化 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1: 1024px 以下螢幕，響應式斷點觸發 grid 重排
- Case 2: Sidebar collapsed 時 NavItem 只顯示 icon，需 title tooltip
- Case 3: VirtualList 空 items 陣列 → 顯示空狀態
- Case 4: SlidePanel ESC 按鍵在多個 panel 開啟時只關閉最上層
- Case 5: Monitor fixed layout 在極小視窗高度下的 overflow 處理

### 回退方案（Rollback Plan）

- **回退方式**: `git revert` 對應 commit（93182d6, 8f4b483, 3260d9c, f36af84）
- **不可逆評估**: 無不可逆部分 — 純前端 UI 變更
- **資料影響**: 無 — 不涉及任何資料層

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

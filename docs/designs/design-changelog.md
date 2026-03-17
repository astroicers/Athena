# Design Changelog

所有設計相關變更紀錄。

---

## [2026-03-17] 全頁面 .pen 設計同步 + UI 修復

### Added
- `pencil-new-v2.pen` 新增 frame：
  - War Room V2 - OPSEC (`EEbwu`，x:3080 y:8000) — 4 Metric Cards + Noise Trend + OPSEC Events
  - War Room V2 - Decision (`Nntpe`，x:4620 y:8000) — Confidence Breakdown + Noise×Risk Matrix + History
  - Planner - Attack Graph Tab (`2qyS3`，x:3080 y:6000) — SVG Canvas + Stats Panel + Legend
- 建立 `SPEC-051-design-token-and-pen-sync-protocol.md` — Design Token 唯一真相來源 + 禁止模式

### Changed
- 標記孤兒 frame 為 deprecated：`lVZKT`（OPSEC Dashboard）、`nPItC`（AI Decision Breakdown）
- 修復 4 個 TabBar `alignItems: end` → `center`（.pen: TGT9O, cEDoL, RDSgS, TTmjJ）
- 修復前端 TabBar.tsx `items-end` → `items-center`
- 空狀態邊框統一：`border border` bug → `border-white/5` + `bg-[#111827] rounded-lg p-6`
- 輸入框邊框統一：`#374151` → `#1f2937`
- 更新 `frontend/DESIGN_MAP.md` 加入 token 速查表和禁止模式

### Fixed
- EngagementPanel.tsx:96 — `border border rounded`（缺色）
- ObjectivesPanel.tsx:218 — `border border rounded`（缺色）
- MissionTab.tsx:338 — `border-[#1f293740]`（半透明不一致）
- MissionTab.tsx:186 — `border-[#374151]`（混用 gray-700）

---

## [2026-03-09] PoC 報告 + 漏洞儀表板設計稿

### Added
- PoC Report 頁面設計（`pencil-new.pen` frame `Y7R6y`，1440x900）
  - Sidebar 導航、PageHeader、4 張 MetricCard
  - 展開狀態 PoC 卡片（T1003.001，含 CommandBlock + OutputBlock + EnvTags）
  - 收合狀態 PoC 卡片（T1110.001）
- Vulnerability Dashboard 頁面設計（`pencil-new.pen` frame `hs3WF`，1440x900）
  - SeverityHeatStrip（CRITICAL/HIGH/MEDIUM 三段）
  - VulnStatusPipeline（DISCOVERED → CONFIRMED → EXPLOITED → REPORTED）
  - VulnTable（表頭 + CRITICAL + HIGH 兩列資料）

---

## [2026-03-08] Executive-Ready UI/UX 大改版

> commit `618c48f`，56 檔案，+1884/-227 行

### Changed
- 全面重構 Design Token 體系（32+ CSS 自訂屬性）
- 字型 Scale 強制：floor 12px（投影機可讀）
- 文字對比度提升：`--color-text-secondary: #c0c0d0`
- TacticalDashboard 指標放大（96 → 140px）
- Canvas 標籤字級提升（11 → 14px）
- i18n 術語修正："Targets Pwned" → "Targets Compromised"

### Added
- Red Team Aesthetic 效果 Token（grid-line, scanline, glow-*）
- 4 頁面啟用 `athena-grid-bg` 戰術網格
- 新頁面：`/poc`（PoC 報告）、`/vulns`（漏洞儀表板）
- 新元件群：`poc/`（PocCommandBlock, PocRecordCard, PocSummaryBar）
- 新元件群：`vulns/`（SeverityHeatStrip, VulnStatusPipeline, VulnTable, VulnDetailPanel）

---

## [2026-03-05] Situation Diagram 視覺重設計

### Changed
- 節點從矩形改為六角形 + radial gradient + 多層 glow（feGaussianBlur 3/6）
- 連線從直線改為 cubic bezier + 粒子動畫
- C5ISR Mini Bar 改為六角形 gauge

---

## [2026-02-27] 戰情室改版

### Changed
- Tactical Dashboard 重新設計
- Floating Node Card（拓樸選中節點卡片）
- Topology UX 改善：拖曳、縮放、節點選取

---

## [2026-02-26] UI 最佳化 Phase 1-5

### Changed
- Phase 1-2：按鈕對比度、Focus indicator、Modal backdrop blur、字級最低 12px
- Phase 3：5 個 SVG 導航圖示、響應式斷點（1024px）、MITRE compact mode
- Phase 4：SectionHeader 統一元件、Loading Skeleton、拓樸圖示
- Phase 5：戰情室 2x2 固定高度佈局、可收合 Sidebar（224px ↔ 64px）、SlidePanel

---

## [2026-02-22] 初始設計系統

### Added
- `athena-design-system.pen`：56 個元件定義、32+ Design Token
- `athena-shell.pen`：App Shell 設計（Sidebar、PageHeader、AlertBanner、CommandInput）
- `athena-battle-monitor.pen`：戰情室（War Room）設計
- `athena-c5isr-board.pen`：C5ISR 指揮板設計
- `athena-mitre-navigator.pen`：MITRE ATT&CK 導航器設計
- `athena-mission-planner.pen`：任務規劃器設計
- ADR-009：前端元件架構決策（領域驅動 10 目錄分類）

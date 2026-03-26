# UI/UX 規格書 (UI/UX Specification)

> 本文件為 Athena 專案的 UI/UX 設計規格，與 `SRS.md` 第 8 節「介面規格」保持同步。設計稿來源為 Pencil MCP 檔案。

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | Athena — 紅隊作戰指揮平台 |
| **版本** | v1.0.0 |
| **最後更新** | 2026-03-25 |
| **狀態** | Accepted |
| **設計稿連結** | `design/pencil-new-v2.pen`（Pencil MCP） |
| **設計系統** | Deep Gemstone v3 |
| **Token 來源** | `design-system/tokens.yaml` |
| **前端負責人** | Athena Contributors |

---

## 1. Design System

> Athena 採用自建 Design System「**Deep Gemstone v3**」，以寶石藍 + 翡翠綠 + 琥珀金為核心色調，搭配深色背景營造紅隊作戰指揮中心的戰術氛圍。所有 Token 定義於 `design-system/tokens.yaml`，經由 CSS 變數實作於 `frontend/src/styles/globals.css`，再透過 Tailwind CSS v4 自訂主題延伸。

### 1.1 Color Palette（色彩系統）

#### 背景色（Background Colors）

| Token | Hex | CSS Variable | Tailwind | 用途 |
|-------|-----|-------------|----------|------|
| `bg-primary` | `#09090B` | `--color-bg-primary` | `athena-bg` | 主背景（鋅黑） |
| `bg-surface` | `#18181B` | `--color-bg-surface` | `athena-surface` | 卡片/面板背景（鋅灰） |
| `bg-elevated` | `#27272A` | `--color-bg-elevated` | `athena-elevated` | 浮層/下拉背景（深鋅） |
| `bg-surface-hover` | `rgba(255,255,255,0.03)` | `--color-bg-surface-hover` | — | 表格列 hover 態 |
| `bg-overlay` | `rgba(0,0,0,0.60)` | `--color-bg-overlay` | — | Modal 遮罩 |

#### 品牌/強調色（Accent — Sapphire Blue）

| Token | Hex | CSS Variable | Tailwind | 用途 |
|-------|-----|-------------|----------|------|
| `accent` | `#1E6091` | `--color-accent` | `athena-accent` | 寶石藍 — 主要操作/品牌色 |
| `accent-hover` | `#1A5276` | `--color-accent-hover` | — | 深寶石藍 — hover 態 |
| `accent-bg` | `rgba(30,96,145,0.12)` | `--color-accent-bg` | — | 寶石藍半透明背景（Badge/選取） |

#### 文字色（Text Colors — Zinc Scale, WCAG AA）

| Token | Hex | CSS Variable | 對比度 (on #09090B) | 用途 |
|-------|-----|-------------|---------------------|------|
| `text-primary` | `#D4D4D8` | `--color-text-primary` | 7:1 | 主文字（鋅白） |
| `text-secondary` | `#A1A1AA` | `--color-text-secondary` | 5.5:1 | 次要文字 |
| `text-tertiary` | `#71717A` | `--color-text-tertiary` | 4.0:1 | 輔助文字/Placeholder |

#### 文字透明度階梯（Text Opacity Scale）

| Token | 值 | CSS Variable | 用途 |
|-------|-----|-------------|------|
| `text-ghost` | `rgba(212,212,216,0.125)` | `--color-text-ghost` | 背景裝飾文字 |
| `text-faint` | `rgba(212,212,216,0.19)` | `--color-text-faint` | 極淡標籤 |
| `text-muted` | `rgba(212,212,216,0.25)` | `--color-text-muted` | 靜音標籤 |
| `text-dim` | `rgba(212,212,216,0.375)` | `--color-text-dim` | 暗淡標籤 |
| `text-soft` | `rgba(212,212,216,0.50)` | `--color-text-soft` | 柔和標籤 |
| `text-subtle` | `rgba(212,212,216,0.63)` | `--color-text-subtle` | 細微標籤 |

#### 邊框色（Border Colors — Zinc, 增強可見度）

| Token | Hex | CSS Variable | 對比度 | 用途 |
|-------|-----|-------------|--------|------|
| `border` | `#3F3F46` | `--color-border` | 2.8:1 | 預設邊框 |
| `border-subtle` | `#52525B` | `--color-border-subtle` | 3.5:1 | 強化邊框 |

#### 語意色（Status — Gemstone）

| Token | Hex | CSS Variable | Tailwind | 用途 |
|-------|-----|-------------|----------|------|
| `success` | `#059669` | `--color-success` | `athena-success` | 翡翠綠 — 成功/完成 |
| `warning` | `#B45309` | `--color-warning` | `athena-warning` | 琥珀金 — 警告 |
| `error` | `#B91C1C` | `--color-error` | `athena-error` | 深紅 — 錯誤 |
| `critical` | `#991B1B` | `--color-critical` | `athena-critical` | 暗血紅 — 嚴重 |
| `info` | `#1E6091` | `--color-info` | — | 寶石藍 — 資訊（同 accent） |
| `error-text` | `#DC2626` | `--color-error-text` | — | 錯誤文字（高對比版） |

#### 語意色背景（Status Background Tints）

| Token | 值 | CSS Variable | 用途 |
|-------|-----|-------------|------|
| `error-bg` | `rgba(185,28,28,0.12)` | `--color-error-bg` | 錯誤 Badge 背景 |
| `warning-bg` | `rgba(180,83,9,0.12)` | `--color-warning-bg` | 警告 Badge 背景 |
| `success-bg` | `rgba(5,150,105,0.12)` | `--color-success-bg` | 成功 Badge 背景 |
| `accent-bg` | `rgba(30,96,145,0.12)` | `--color-accent-bg` | Info Badge 背景 |

#### OODA 階段色（War Room / 決策追蹤）

| 階段 | Hex | CSS Variable | 語意 |
|------|-----|-------------|------|
| Observe（觀察） | `#1E6091` | `--color-phase-observe` | 寶石藍 |
| Orient（定向） | `#7C3AED` | `--color-phase-orient` | 紫水晶 |
| Decide（決策） | `#B45309` | `--color-phase-decide` | 琥珀金 |
| Act（行動） | `#059669` | `--color-phase-act` | 翡翠綠 |

#### 特效色（Red Team Aesthetic）

| Token | 值 | CSS Variable | 用途 |
|-------|-----|-------------|------|
| `grid-line` | `rgba(63,63,70,0.25)` | `--color-grid-line` | 戰術網格線 |
| `scanline` | `rgba(30,96,145,0.03)` | `--color-scanline` | CRT 掃描線 |
| `glow-green` | `rgba(5,150,105,0.4)` | `--color-glow-green` | 翡翠光暈（active 狀態） |
| `glow-red` | `rgba(185,28,28,0.4)` | `--color-glow-red` | 深紅光暈（alert 狀態） |
| `glow-cyan` | `rgba(30,96,145,0.3)` | `--color-glow-cyan` | 寶石藍光暈 |

#### 白色透明度階梯（背景/疊加用）

| Token | 值 | CSS Variable | 用途 |
|-------|-----|-------------|------|
| `white-5` | `rgba(255,255,255,0.02)` | `--color-white-5` | 微弱疊加 |
| `white-8` | `rgba(255,255,255,0.03)` | `--color-white-8` | 輕微疊加 |
| `white-10` | `rgba(255,255,255,0.06)` | `--color-white-10` | 可辨疊加 |

> Athena 為純暗色主題，不支援亮色模式。所有色彩值均以深色背景為基準計算對比度。

---

### 1.2 Typography Scale（字體排版）

**字體族：**

| 類別 | 字體堆疊 | CSS Variable | 用途 |
|------|----------|-------------|------|
| Monospace（主要） | `"JetBrains Mono", "Fira Code", monospace` | `--font-mono` | 全站主字體 — 導航、標籤、數據、程式碼 |
| Sans-serif（輔助） | `"Inter", system-ui, sans-serif` | `--font-sans` | UI 文字標籤、描述文字 |

> Athena 以 Monospace 為全站預設字體（`body { font-family: var(--font-mono) }`），契合紅隊工具的終端機/指揮中心視覺語言。

**字級階梯：**

| Token | Font Size | CSS Variable | 用途 |
|-------|-----------|-------------|------|
| `caption` | 10px | `--fs-caption` | Badge 內文、微型文字 |
| `metric-label` | 11px | `--fs-metric-label` | 指標標籤 |
| `floor` | 12px | `--fs-floor` | 最小字級、表格標頭、輔助說明 |
| `heading-card` | 13px | `--fs-heading-card` | 卡片標題 |
| `body` | 14px | `--fs-body` | 內文、表格內容、次要資訊 |
| `heading-section` | 18px | `--fs-heading-section` | 區塊標題 |
| `heading-page` | 28px | `--fs-heading-page` | 頁面標題 |
| `metric` | 32px | `--fs-metric` | 大型指標數字 |

**字重使用規則：**

| 字重 | 值 | 用途 |
|------|-----|------|
| Regular | 400 | 內文、描述 |
| Semibold | 600 | 按鈕文字、互動元素 |
| Bold | 700 | 標題、導航、強調 |

**數字排版：**

- 所有指標數字使用 `font-variant-numeric: tabular-nums`（對齊用途），透過 `.athena-tabular-nums` 工具類別實現

---

### 1.3 Spacing System（間距系統）

**基礎單位：** 4px（Tailwind 預設模式）

**自訂 Token：**

| Token | Value | CSS Variable | 用途 |
|-------|-------|-------------|------|
| `badge-x` | 12px | `--sp-badge-x` | Badge 水平內距 |
| `badge-y` | 5px | `--sp-badge-y` | Badge 垂直內距 |
| `cell` | 14px | `--sp-cell` | 表格單元格內距 |
| `card` | 20px | `--sp-card` | 卡片內距 |

**Tailwind 間距（慣用值）：**

| 用途 | 值 | Tailwind Class |
|------|-----|----------------|
| Icon 與文字間距 | 4px | `gap-1` |
| 元素內小間距 | 6px | `gap-1.5` |
| NavItem 間距 | 4px | `gap-1` |
| 表單欄位間距 | 12px | `gap-3` |
| 卡片 Padding | 16px | `p-4` |
| Section 間距 | 24px | `gap-6` |
| 頁面側邊 Padding | 24px | `px-6` |

---

### 1.4 Border Radius（圓角系統）

| Token | Value | CSS Variable | Tailwind | 用途 |
|-------|-------|-------------|----------|------|
| `default` | 4px | `--radius` | `rounded-[var(--radius)]` | 統一圓角 — 所有元件（按鈕、卡片、輸入框、Badge） |

> Athena 採用統一 4px 圓角策略，所有元件共用同一圓角值，確保視覺一致性。Badge 例外使用 `rounded-full`。

---

### 1.5 Component Library（元件庫）

**基礎框架：** 自建元件（無第三方 UI 庫），基於 React + Tailwind CSS v4

**元件清單（依開發優先級排序）：**

| 元件 | 路徑 | 優先級 | 對應頁面 | 備註 |
|------|------|--------|----------|------|
| `Button` | `atoms/Button.tsx` | P0 | 全站 | primary/secondary/danger 三種變體 |
| `Badge` | `atoms/Badge.tsx` | P0 | 全站 | success/warning/error/info 四種語意變體 |
| `DataTable` | `data/DataTable.tsx` | P0 | Operations, Vulns, Tools | 含排序、空狀態 |
| `Sidebar` | `layout/Sidebar.tsx` | P0 | 全站 | 左側固定導航，200px 寬 |
| `PageHeader` | `layout/PageHeader.tsx` | P0 | 全站 | 含標題 + 作戰代號 Badge + trailing 動作區 |
| `TabBar` | `nav/TabBar.tsx` | P0 | War Room, Attack Surface | 水平分頁切換 |
| `NavItem` | `nav/NavItem.tsx` | P0 | Sidebar 內 | 導航項（icon + label + active 態） |
| `StatusDot` | `atoms/StatusDot.tsx` | P0 | Tools, Operations | 狀態指示燈（含 pulse 動畫） |
| `OODAIndicator` | `ooda/OODAIndicator.tsx` | P1 | War Room | OODA 四階段指示器 |
| `OODATimeline` | `ooda/OODATimeline.tsx` | P1 | War Room | OODA 循環時間軸 |
| `C5ISRHealthGrid` | `c5isr/C5ISRHealthGrid.tsx` | P1 | Dashboard, War Room | 3x2 網格，6 個 C5ISR 域 |
| `C5ISRDomainCard` | `c5isr/C5ISRDomainCard.tsx` | P1 | Dashboard, War Room | 單一 C5ISR 域卡片（健康%） |
| `MermaidRenderer` | `c5isr/MermaidRenderer.tsx` | P1 | War Room | Mermaid 流程圖渲染 |
| `OODAFlowDiagram` | `c5isr/OODAFlowDiagram.tsx` | P1 | War Room | OODA-C5ISR 關聯流程圖 |
| `MetricCard` | `cards/MetricCard.tsx` | P1 | Dashboard | 指標卡片（大字體數值） |
| `TechniqueCard` | `cards/TechniqueCard.tsx` | P1 | Attack Surface | MITRE ATT&CK 技術卡片 |
| `RecommendCard` | `cards/RecommendCard.tsx` | P1 | War Room | 建議行動卡片 |
| `HostNodeCard` | `cards/HostNodeCard.tsx` | P1 | Attack Graph | 主機節點卡片 |
| `MITRECell` | `mitre/MITRECell.tsx` | P1 | Attack Surface | ATT&CK 矩陣單元格 |
| `KillChainIndicator` | `mitre/KillChainIndicator.tsx` | P1 | Attack Surface | Kill Chain 進度指示器 |
| `Toast` | `ui/Toast.tsx` | P1 | 全站 | 操作反饋通知 |
| `Tooltip` | `ui/Tooltip.tsx` | P1 | 全站 | 懸浮提示 |
| `Skeleton` | `ui/Skeleton.tsx` | P1 | 全站 | 載入骨架屏 |
| `SlidePanel` | `ui/SlidePanel.tsx` | P2 | War Room | 側邊滑出面板 |
| `VirtualList` | `ui/VirtualList.tsx` | P2 | Vulns, Operations | 虛擬捲動長列表 |
| `TimeSeriesChart` | `ui/TimeSeriesChart.tsx` | P2 | Dashboard | 時序圖表 |
| `ProgressBar` | `atoms/ProgressBar.tsx` | P2 | 多頁面 | 進度條 |
| `HexIcon` | `atoms/HexIcon.tsx` | P2 | 全站 | 六角形圖示容器 |
| `SectionHeader` | `atoms/SectionHeader.tsx` | P2 | 全站 | 區塊標題（card/section 兩種層級） |
| `LocaleSwitcher` | `layout/LocaleSwitcher.tsx` | P2 | 全站 | 語系切換（en/zh-TW） |
| `ConstraintBanner` | `layout/ConstraintBanner.tsx` | P2 | 全站 | OPSEC 約束橫幅 |
| `ToolRegistryTable` | `tools/ToolRegistryTable.tsx` | P1 | Tools | MCP 工具註冊表 |
| `ToolExecuteModal` | `tools/ToolExecuteModal.tsx` | P1 | Tools | 工具執行對話框 |
| `AddTargetModal` | `modal/AddTargetModal.tsx` | P2 | War Room | 新增目標對話框 |
| `RecommendationPanel` | `ooda/RecommendationPanel.tsx` | P2 | War Room | AI 建議面板 |

---

## 2. 頁面流程

### 2.1 使用者旅程地圖（User Journey Map）

#### 旅程：紅隊作戰任務執行

```
建立作戰行動 (Operations) --> 進入戰情室 (War Room) --> OODA 循環
  --> Observe: 偵察目標、收集情報
  --> Orient: 分析攻擊面、識別弱點
  --> Decide: 選擇攻擊路徑、制定方案
  --> Act: 執行攻擊工具、記錄結果
  --> 回到 Observe（持續循環）
  --> 記錄弱點 (Vulns) --> 撰寫 PoC --> 結束行動
```

**各階段情緒曲線（1-10）：**
- 建立作戰行動：7（目標明確，準備就緒）
- 偵察階段（Observe）：6（資訊蒐集中，需要耐心）
- 分析定向（Orient）：5（大量資訊待消化，認知負荷高）
- 制定方案（Decide）：7（方向逐漸清晰）
- 執行攻擊（Act）：9（獲得結果，成就感高）
- 記錄弱點與 PoC：6（文件工作，但有成果產出）

**痛點與優化機會：**
- Orient 階段資訊過載 --> C5ISR Health Grid 提供六維度一目了然的健康概覽
- Decide 階段缺乏建議 --> RecommendationPanel 提供 AI 輔助建議
- 工具狀態不透明 --> StatusDot + pulse 動畫即時回報工具 ONLINE/OFFLINE

---

#### 旅程：攻擊面分析

```
進入 Attack Surface --> 瀏覽 MITRE ATT&CK 矩陣 --> 點選技術卡片查看詳情
  --> 關聯已知弱點 --> 切換至 Attack Graph 檢視拓撲
  --> 識別高價值路徑 --> 回到 War Room 制定方案
```

---

### 2.2 導航結構（Information Architecture）

```
Athena（左側 Sidebar 固定導航）
|
+-- Operations (/operations)              [作戰行動列表]
|   +-- 新建行動 (/operations/new)
|   +-- 行動詳情 (/operations/:id)
|       +-- TARGETS 標籤頁
|       +-- DETAILS 標籤頁
|
+-- War Room (/warroom)                   [戰情室 — 核心指揮中心]
|   +-- OODA Panel（左側：四階段可展開區塊）
|   |   +-- Observe（觀察 — 偵察結果）
|   |   +-- Orient（定向 — 攻擊面分析）
|   |   +-- Decide（決策 — 方案選擇）
|   |   +-- Act（行動 — 執行記錄）
|   +-- Center Visualization（中央：C5ISR 健康網格 + OODA 流程圖）
|   +-- Action Log（右側：操作日誌 + 終端機）
|   +-- TARGETS 標籤頁（目標左列 + 右側 Markdown 詳情）
|
+-- Attack Surface (/attack-surface)      [ATT&CK 攻擊面]
|   +-- MITRE 矩陣檢視
|   +-- Kill Chain 指示器
|
+-- Attack Graph (/attack-graph)          [攻擊路徑圖]
|   +-- Force-graph-3d 網路拓撲
|   +-- 節點詳情面板
|
+-- Vulns (/vulns)                        [弱點追蹤]
|   +-- 弱點列表（DataTable）
|   +-- PoC 證據面板
|
+-- Tools (/tools)                        [MCP 工具註冊表]
|   +-- 工具列表（分 Tactic 群組）
|   +-- 工具執行 Modal
|   +-- Playbook 瀏覽器
|   +-- 新手引導
|
+-- Decisions (/decisions)                [決策追蹤]
+-- OPSEC (/opsec)                        [OPSEC 約束監控]
+-- PoC (/poc)                            [PoC 管理]
+-- Planner (/planner)                    [任務規劃 — 已整併至 War Room]
```

**主導航項目（Sidebar NAV_ITEMS）：**

| 順序 | 路由 | 圖示 | 標籤（i18n Key） |
|------|------|------|-----------------|
| 1 | `/operations` | OperationsIcon | `Nav.operations` |
| 2 | `/warroom` | MonitorIcon | `Nav.warRoom` |
| 3 | `/attack-surface` | AttackGraphIcon | `Nav.attackSurface` |
| 4 | `/vulns` | VulnsIcon | `Nav.vulns` |
| 5 | `/tools` | ToolsIcon | `Nav.tools` |

---

## 3. 元件規格

> 每個元件定義：Props、States、Behavior、無障礙需求。

### 3.1 Button 元件

**路徑：** `frontend/src/components/atoms/Button.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `variant` | `'primary' \| 'secondary' \| 'danger'` | `'secondary'` | 視覺樣式 |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | 尺寸 |
| `disabled` | `boolean` | `false` | 禁用狀態 |
| `icon` | `ReactNode` | — | 左側圖示 |
| `className` | `string` | `""` | 額外 CSS 類別 |
| `children` | `ReactNode` | — | 按鈕內容 |

**尺寸規格：**

| Size | Padding | Font Size |
|------|---------|-----------|
| `sm` | `px-3 py-1` | 12px (`text-xs`) |
| `md` | `px-4 py-2` | 14px (`text-sm`) |
| `lg` | `px-6 py-3` | 16px (`text-base`) |

**States：**

| 狀態 | 視覺效果 |
|------|----------|
| Default (primary) | `#1E6091` 背景，`#D4D4D8` 文字，`#1E6091` 邊框 |
| Hover (primary) | `#1A5276` 背景 |
| Default (secondary) | `#18181B` 背景，`#D4D4D8` 文字，`#52525B` 邊框 |
| Hover (secondary) | `#27272A` 背景 |
| Default (danger) | `rgba(185,28,28,0.12)` 背景，`#B91C1C` 文字 |
| Focus | 2px `#1E6091` ring，offset 2px |
| Disabled | 50% opacity，cursor `not-allowed` |

**Behavior：**
- `icon` 與 `children` 透過 `gap-1.5` 間距排列
- 使用 `font-mono font-semibold` 確保戰術風格一致
- 統一圓角 `rounded-[var(--radius)]`（4px）

**無障礙：**
- 原生 `<button>` 標籤，保留完整鍵盤語意
- Focus 使用 `focus:ring-2 focus:ring-[var(--color-accent)]`
- Icon-only 按鈕需補 `aria-label`

---

### 3.2 Badge 元件

**路徑：** `frontend/src/components/atoms/Badge.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `variant` | `'success' \| 'warning' \| 'error' \| 'info'` | `'info'` | 語意變體 |
| `children` | `ReactNode` | 必填 | Badge 內容 |

**States（各變體色彩）：**

| Variant | 背景 | 文字色 | 邊框色 |
|---------|------|--------|--------|
| `success` | `rgba(5,150,105,0.12)` | `#059669` | `rgba(5,150,105,0.25)` |
| `warning` | `rgba(180,83,9,0.12)` | `#B45309` | `rgba(180,83,9,0.25)` |
| `error` | `rgba(185,28,28,0.12)` | `#B91C1C` | `rgba(185,28,28,0.25)` |
| `info` | `rgba(30,96,145,0.12)` | `#1E6091` | `rgba(30,96,145,0.25)` |

**Behavior：**
- `rounded-full` 全圓角（例外於全站 4px 規則）
- `font-mono font-semibold text-xs`
- `inline-flex items-center shrink-0 whitespace-nowrap` 防止換行

---

### 3.3 DataTable 元件

**路徑：** `frontend/src/components/data/DataTable.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `columns` | `Column<T>[]` | 必填 | 欄位定義（key, header, render?, sortable?, width?） |
| `data` | `T[]` | 必填 | 資料陣列 |
| `keyField` | `string` | 必填 | 唯一識別欄位名 |
| `emptyMessage` | `string` | `"No data available"` | 空狀態文字 |

**Column 介面：**

| 欄位 | Type | 說明 |
|------|------|------|
| `key` | `string` | 資料欄位鍵 |
| `header` | `string` | 表頭文字 |
| `render` | `(row: T) => ReactNode` | 自訂渲染函式 |
| `sortable` | `boolean` | 是否可排序 |
| `width` | `number \| string` | 欄位寬度 |

**States：**

| 狀態 | 說明 |
|------|------|
| 有資料 | 完整表格，hover 行高亮（`white/5`） |
| 空狀態 | 居中顯示 `emptyMessage`，`text-secondary` 色 |
| 排序中 | 表頭顯示 `▲`/`▼` 指示器，文字變為 `accent` 色 |

**Behavior：**
- 排序為前端記憶體排序（`useMemo` 最佳化），支援數字與字串
- 表頭 `uppercase tracking-wider text-secondary`，字級 12px
- 列高 40px（`h-10`），內距 `px-4 py-2`
- 邊框 + 圓角包裹整體表格

**無障礙：**
- 使用語意 `<table>`, `<thead>`, `<tbody>`, `<th>`, `<td>`
- 可排序欄位以 `cursor-pointer` 提示可互動

---

### 3.4 Sidebar 元件

**路徑：** `frontend/src/components/layout/Sidebar.tsx`

**Props：** 無（讀取路由狀態與 i18n）

**結構：**

| 區域 | 說明 |
|------|------|
| Logo | 「A」字母方塊（accent 背景，sans 字體）+ 「ATHENA」文字（mono, bold, tracking-wider） |
| 分隔線 | `border-b` |
| 導航列表 | 5 個 `NavItem`，依 `NAV_ITEMS` 常數渲染 |
| 底部 | GitHub Star 連結（黃色星號） |

**規格：**
- 固定寬度 200px，全高 `h-full`
- 背景 `bg-athena-surface`，右邊框 `border-[var(--color-border)]`
- 不可收合（Desktop-first 設計，最小 1280px 視窗）

**NavItem Active 態：**
- 當前路由匹配時高亮顯示（accent 色）

---

### 3.5 TabBar 元件

**路徑：** `frontend/src/components/nav/TabBar.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `tabs` | `{ id: string; label: string }[]` | 必填 | 分頁定義 |
| `activeTab` | `string` | 必填 | 當前選中分頁 ID |
| `onChange` | `(tabId: string) => void` | 必填 | 切換回調 |

**States：**

| 狀態 | 視覺效果 |
|------|----------|
| Active Tab | `accent` 色文字 + `font-semibold` + 底部 3px accent 色指示條 |
| Inactive Tab | `text-tertiary` 色，hover 時變 `text-secondary` |

**規格：**
- 高度 40px（`h-10`），水平排列
- 背景 `bg-primary`，底部邊框
- 指示條：底部 3px 高，accent 色，頂部圓角

---

### 3.6 PageHeader 元件

**路徑：** `frontend/src/components/layout/PageHeader.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `title` | `string` | 必填 | 頁面標題 |
| `operationCode` | `string` | — | 作戰代號（顯示為 accent Badge） |
| `trailing` | `ReactNode` | — | 右側操作區域 |

**規格：**
- 高度 48px（`h-12`），`px-6`
- 背景 `bg-surface`，底部邊框
- 標題 13px `font-mono font-bold tracking-wider`
- 作戰代號 Badge：accent 色背景 12% + accent 邊框 25% + accent 文字

---

### 3.7 StatusDot 元件

**路徑：** `frontend/src/components/atoms/StatusDot.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `status` | `string` | 必填 | 狀態字串 |
| `pulse` | `boolean` | `false` | 是否顯示 ping 動畫 |

**狀態色彩映射：**

| 狀態 | 背景色 |
|------|--------|
| `alive`, `operational`, `nominal` | success 背景 |
| `active`, `scanning` | accent |
| `engaged`, `pending`, `degraded` | warning 背景 |
| `untrusted`, `dead` | error 背景 |
| `critical` | critical/10 |
| `offline` | elevated |

**規格：**
- 尺寸 10x10px（`h-2.5 w-2.5`），全圓
- pulse 模式：外層 `animate-ping` + 75% opacity

---

### 3.8 OODAIndicator 元件

**路徑：** `frontend/src/components/ooda/OODAIndicator.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `currentPhase` | `OODAPhase \| string \| null` | 必填 | 當前 OODA 階段 |

**States：**

| 狀態 | 視覺效果 |
|------|----------|
| Active Phase | accent 背景 12% + accent 文字 + accent 邊框 |
| Past Phase | accent 背景 12% + accent 文字（無邊框） |
| Future Phase | elevated/30 背景 + tertiary 文字 |

**規格：**
- 四個等寬區塊水平排列，中間以 `→` 箭頭連接
- 卡片外殼：surface 背景 + border + 4px 圓角 + `p-4`
- 含 SectionHeader + 提示文字

---

### 3.9 C5ISRHealthGrid 元件

**路徑：** `frontend/src/components/c5isr/C5ISRHealthGrid.tsx`

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `domains` | `C5ISRStatus[]` | 必填 | 六個 C5ISR 域狀態 |
| `onDomainClick` | `(domain: C5ISRDomain) => void` | — | 域卡片點擊回調 |

**C5ISR 六域排列（3x2 Grid）：**

| 域 | 全稱 | 位置 |
|----|------|------|
| Command | 指揮 | 左上 |
| Control | 控制 | 中上 |
| Communications | 通信 | 右上 |
| Computers | 計算 | 左下 |
| Cyber | 網路 | 中下 |
| ISR | 情監偵 | 右下 |

**規格：**
- `grid grid-cols-3 gap-2`
- 標題「C5ISR DOMAIN HEALTH」以 `text-xs font-bold uppercase tracking-wider` 全大寫顯示
- 每張 DomainCard 顯示域名 + 健康百分比

---

## 4. 響應式規則

### 4.1 設計策略

Athena 為 **Desktop-first** 設計，目標使用情境為軍事/企業級紅隊作戰指揮中心，操作者使用大型螢幕。

**最小支援視窗寬度：** 1280px

### 4.2 Breakpoints

| 名稱 | 寬度範圍 | 支援等級 |
|------|----------|----------|
| `xl` (desktop) | 1280px - 1535px | P0 — 主要目標 |
| `2xl` (wide) | >= 1536px | P0 — 主要目標 |
| `lg` (laptop) | 1024px - 1279px | P1 — 有限支援（側邊欄可能受壓縮） |
| `md` (tablet) | 768px - 1023px | P2 — 未規劃 |
| `sm` / `xs` (mobile) | < 768px | 不支援 |

### 4.3 佈局策略

| 頁面/元件 | Desktop (xl+) | Laptop (lg) |
|-----------|---------------|-------------|
| 全域佈局 | 固定 200px Sidebar + 主內容區 | 同上（Sidebar 不收合） |
| War Room | 三欄：OODA Panel + Center Viz + Action Log | 同上（內容自適應） |
| Dashboard | 多欄 Grid（3-4 欄） | 2-3 欄 Grid |
| DataTable | 完整表格 | 完整表格（水平捲動） |
| Attack Graph | Force-graph-3d 全尺寸 | 同上 |
| Modal | 置中 Dialog | 置中 Dialog |

### 4.4 觸控規則

由於目標為桌面環境，觸控優化為次要考量。但仍確保：
- 互動元素最小點擊目標 36x36px
- 不依賴 Hover-only 互動傳遞關鍵資訊

---

## 5. 無障礙標準（Accessibility）

### 5.1 合規目標

- **WCAG 等級：** 2.1 AA
- **測試工具：** axe DevTools、Lighthouse

### 5.2 色彩對比度

| 組合 | 最小要求 | 實際比率 | 通過 |
|------|---------|---------|------|
| 主文字 `#D4D4D8` on `#09090B` | 4.5:1 (AA) | 12.6:1 | PASS |
| 次要文字 `#A1A1AA` on `#09090B` | 4.5:1 (AA) | 7.5:1 | PASS |
| 輔助文字 `#71717A` on `#09090B` | 3:1 (AA Large) | 4.4:1 | PASS |
| Accent `#1E6091` on `#09090B` | 3:1 (AA Large) | 3.6:1 | PASS |
| Success `#059669` on `#09090B` | 3:1 (AA Large) | 4.8:1 | PASS |
| Warning `#B45309` on `#09090B` | 3:1 (AA Large) | 4.2:1 | PASS |
| Error `#B91C1C` on `#09090B` | 3:1 (AA Large) | 3.3:1 | PASS |
| Error Text `#DC2626` on `#09090B` | 4.5:1 (AA) | 4.6:1 | PASS |

### 5.3 鍵盤導航（Keyboard Navigation）

| 場景 | 行為 |
|------|------|
| Tab 順序 | Sidebar -> PageHeader -> 主內容區，與視覺閱讀順序一致 |
| Focus 樣式 | 1px `accent` outline，offset 2px（全域 `:focus-visible` 規則） |
| Modal 開啟 | Focus 移至 Modal 第一個互動元素 |
| Modal 關閉 | Focus 返回觸發按鈕 |
| TabBar | Tab 鍵在分頁間移動，Enter/Space 選取 |
| DataTable | 可排序欄位可 Tab 進入，Enter 切換排序 |

### 5.4 Screen Reader 支援

- 使用語意 HTML：`<aside>`（Sidebar）、`<header>`（PageHeader）、`<nav>`（導航）、`<main>`（主內容）、`<table>`（DataTable）
- 圖示按鈕提供 `aria-label`
- 狀態 Badge 的顏色資訊同時以文字傳達（如「ONLINE」、「CRITICAL」）
- 動態內容更新使用 `aria-live="polite"`

### 5.5 i18n 無障礙

- 語系切換（en / zh-TW）透過 `LocaleSwitcher` 元件
- 所有使用者可見文字經由 `next-intl` 管理，支援 Screen Reader 朗讀正確語言

---

## 6. 動畫與互動

### 6.1 Transition 規則

| 場景 | Duration | Easing | CSS |
|------|----------|--------|-----|
| 按鈕 Hover | 150ms | `ease` | `transition-colors` |
| NavItem Hover | 150ms | `ease` | `transition-colors` |
| StatusDot Pulse | 持續 | `ease-in-out` | `animate-ping` |
| 表格列 Hover | 150ms | `ease` | `transition-colors` |
| SlidePanel 開啟 | 300ms | `ease-out` | `slideIn` keyframe |
| Toast 出現 | 300ms | `ease-out` | Slide + Fade |
| Toast 消失 | 200ms | `ease-in` | Slide + Fade |
| Skeleton 載入 | 1500ms | `linear` | Pulse 循環 |
| GitHub Star Hover | 150ms | `ease` | `transition-transform scale-125` |

**減少動畫模式（`prefers-reduced-motion`）：**

應於全域 CSS 加入：

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 6.2 Red Team Aesthetic 特效

| 特效 | CSS Class | 說明 |
|------|-----------|------|
| 戰術網格背景 | `.athena-grid-bg` | 24x24px 網格線疊加於背景 |
| CRT 掃描線 | `.athena-scanline` | `::after` 偽元素，2px 間距水平掃描線 |
| 翡翠光暈 | `.athena-glow-active` | `text-shadow: 0 0 8px` 綠色光暈（active 元素） |
| 深紅光暈 | `.athena-glow-alert` | `text-shadow: 0 0 8px` 紅色光暈（alert 元素） |
| 等寬數字 | `.athena-tabular-nums` | `font-variant-numeric: tabular-nums`（指標對齊） |

### 6.3 Loading States

| 場景 | 載入方式 | 元件 |
|------|----------|------|
| 頁面初次載入 | Skeleton Screen | `PageLoading` / `Skeleton` |
| 資料表格載入 | 骨架行 | `Skeleton` in `DataTable` |
| 工具執行中 | 按鈕 Spinner / disabled | `Button` disabled 態 |
| Force-graph 渲染 | 漸進式節點載入 | Force-graph-3d 內建 |

### 6.4 Feedback Patterns（操作反饋）

| 操作類型 | 反饋方式 | 顯示時間 |
|----------|----------|----------|
| 成功（建立行動、新增目標） | Toast（success 綠色） | 3 秒後自動消失 |
| 錯誤（API 失敗） | Toast（error 紅色） | 5 秒或使用者關閉 |
| 破壞性操作（刪除行動） | 確認 Dialog（HexConfirmModal） | 使用者主動確認 |
| 工具執行結果 | Terminal 輸出 + Toast | 持續顯示 |
| OPSEC 約束違反 | ConstraintBanner（頁面頂部） | 持續顯示直到解除 |

### 6.5 空狀態設計（Empty States）

| 頁面 | 空狀態文字 | 行動引導 |
|------|-----------|---------|
| Operations 列表 | 尚無作戰行動 | 「建立第一個行動」按鈕 |
| DataTable 通用 | `emptyMessage` 參數（預設 "No data available"） | 居中文字，`text-secondary` |
| Vulns 列表 | 尚未發現弱點 | 引導至 Tools 頁面執行掃描 |
| Tools 工具列表 | 無可用工具 | 檢查 MCP 服務連線 |

---

## 附錄

### A. 設計 Token 來源

| 來源 | 路徑 |
|------|------|
| 設計稿（Source of Truth） | `design/pencil-new-v2.pen` |
| Token YAML 定義 | `design-system/tokens.yaml` |
| CSS Variables 實作 | `frontend/src/styles/globals.css` |
| Tailwind 配置 | `frontend/tailwind.config.ts` |

**同步流程：** `pencil-new-v2.pen` (設計) --> `tokens.yaml` (規格) --> `globals.css` (實作) --> `tailwind.config.ts` (擴展)

### B. 瀏覽器測試矩陣

| 瀏覽器 | 版本 | 作業系統 | 優先級 |
|--------|------|----------|--------|
| Chrome | 最新 2 版 | Windows, macOS, Linux | P0 |
| Firefox | 最新 2 版 | Windows, macOS, Linux | P1 |
| Edge | 最新 2 版 | Windows | P1 |
| Safari | 最新 2 版 | macOS | P2 |

> Mobile 瀏覽器不在測試範圍內（Desktop-first，最小 1280px）。

### C. i18n 支援

| 語系 | 代碼 | 狀態 |
|------|------|------|
| English | `en` | 完整支援 |
| 繁體中文 | `zh-TW` | 完整支援 |

**實作方式：** `next-intl` 套件，所有 UI 文字透過 `useTranslations()` hook 取得。

### D. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-03-25 | 初版建立 — 完整 Deep Gemstone v3 設計系統、11 頁面、30+ 元件規格 | Athena Contributors |

### E. 相關文件

- [`SRS.md`](./SRS.md) — 軟體需求規格書
- [`SDS.md`](./SDS.md) — 軟體設計規格書
- [`ROADMAP.md`](./ROADMAP.md) — 專案路線圖
- [`architecture.md`](./architecture.md) — 系統架構文件
- 設計稿：`design/pencil-new-v2.pen`（透過 Pencil MCP 開啟）

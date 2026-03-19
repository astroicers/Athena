# Athena Design System

> 本文件的色值衍生自 tokens.yaml，不獨立定義

> 紅隊滲透測試平台的統一設計系統。
> 目標受眾：50-60 歲高階主管，投影機簡報場景。

---

## 設計哲學

1. **Red Team Aesthetic** — 深色底（#09090B）、CRT 掃描線、六角形元素、多層光暈、戰術網格
2. **漸進式揭露** — Level 1 總覽（5 秒掌握）→ Level 2 列表（30 秒定位）→ Level 3 詳情（完整操作）
3. **設計即規格** — 所有視覺決策可量化、可追溯：設計決策 → Design Token → CSS 屬性
4. **投影機可讀** — 最小字級 12px、高對比文字（secondary: #71717A）、大指標數字 32px

---

## Token 參照

| 檔案 | 職責 |
|------|------|
| `design-system/tokens.yaml` | Token 完整定義（YAML 結構化） |
| `frontend/src/styles/globals.css` | CSS 自訂屬性（Runtime 真相來源） |
| `frontend/tailwind.config.ts` | Tailwind 映射（`athena-*` 前綴） |

---

## 設計稿（Pencil MCP）

> .pen 檔案必須留在 `design/` 目錄，Pencil MCP 工具依賴此路徑。

| 設計稿 | 涵蓋範圍 | 最後更新 |
|--------|---------|---------|
| ~~athena-design-system.pen~~ | legacy — 已由 pencil-new-v2.pen 取代 | 2026-03-04 |
| athena-shell.pen | App Shell + Sidebar + 導航 | 2026-02-22 |
| athena-battle-monitor.pen | 戰情室（War Room） | 2026-02-22 |
| athena-c5isr-board.pen | C5ISR 指揮板 | 2026-02-22 |
| athena-mitre-navigator.pen | MITRE ATT&CK 導航器 | 2026-02-22 |
| athena-mission-planner.pen | 任務規劃器 | 2026-02-22 |
| **pencil-new-v2.pen** | **全頁面統一設計稿（當前活躍）** | 2026-03-17 |
| ~~pencil-new.pen~~ | legacy — 已由 v2 取代 | 2026-03-09 |

---

## 元件架構

> 參照 ADR-009：前端元件架構決策

17 個領域驅動目錄（`frontend/src/components/`）：

| 目錄 | 職責 | 代表元件 |
|------|------|---------|
| `atoms/` | 基礎元件 | Button, Badge, StatusDot, Toggle, ProgressBar, HexIcon |
| `cards/` | 卡片元件 | MetricCard, HostNodeCard, AgentCard |
| `data/` | 資料展示 | DataTable, LogStream, JsonViewer |
| `layout/` | 佈局元件 | Sidebar, AlertBanner, PageHeader, CommandInput |
| `modal/` | 彈窗 | HexConfirmModal, DetailPanel |
| `nav/` | 導航 | NavItem, TabBar, NavIcons |
| `mitre/` | MITRE ATT&CK | MITREMatrix, KillChainBar, TechniqueDetail |
| `ooda/` | OODA 迴圈 | OODAIndicator, OODATimeline, PhaseCard |
| `c5isr/` | C5ISR 評估 | DomainCard, HealthBar, C5ISRGrid |
| `topology/` | 網路拓樸 | NetworkTopology, FloatingNodeCard, NodeDetailPanel |
| `poc/` | PoC 報告 | PocCommandBlock, PocRecordCard, PocSummaryBar |
| `vulns/` | 漏洞管理 | SeverityHeatStrip, VulnStatusPipeline, VulnTable |
| `situation/` | 態勢圖 | AttackSituationDiagram |
| `terminal/` | 終端機 | TerminalPanel |
| `tools/` | 工具管理 | ToolCard |
| `warroom/` | 戰情室 | TacticalDashboard, AgentBeacon |
| `ui/` | 通用 UI | Skeleton, SectionHeader |

---

## 設計語言

- **六角形**：節點、Gauge、確認 Modal 均使用六角形
- **多層光暈**：feGaussianBlur stdDeviation 3/6（active 加倍）
- **粒子動畫**：拓樸連線、Situation Diagram 邊
- **戰術網格**：24px 間距背景（`.athena-grid-bg`）
- **CRT 掃描線**：終端風格元件（`.athena-scanline`）

---

## 狀態規範

```yaml
interactive: [default, hover, active, focus, disabled]
data:        [loading, empty, error, success]
form:        [pristine, dirty, valid, invalid, submitting]
```

所有資料驅動元件必須覆蓋 `data` 四態。互動元件必須覆蓋 `interactive` 五態。

---

## 禁止事項

詳見 `.asp/profiles/design_dev.md`「設計禁止事項」章節。核心規則：

- 禁止 magic number 間距（必須用 token）
- 禁止 inline style（必須用 class 或 Tailwind）
- 禁止忽略 loading / error / empty 三態
- 禁止使用未定義在 tokens 中的顏色值

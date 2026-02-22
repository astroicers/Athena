# [ADR-009]: 前端元件架構與設計系統整合

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Phase 3-4 需將 Pencil.dev 設計稿（56 個元件、32 個設計變數）轉化為 React 元件，並實作 4 個畫面。需決定：

1. 元件目錄分類策略
2. 設計 Token 與 Tailwind 的整合方式
3. 3D 拓樸元件的 SSR 處理策略
4. 設計稿與程式碼的對齊原則

---

## 評估選項（Options Considered）

### 元件分類策略

#### 選項 A：領域驅動分類（10 類目錄）

```
components/
├── layout/     (Sidebar, AlertBanner, PageHeader, CommandInput)
├── atoms/      (Button, Badge, StatusDot, Toggle, ProgressBar, HexIcon)
├── cards/      (MetricCard, HostCard, AgentCard)
├── data/       (DataTable, LogStream, JsonViewer)
├── mitre/      (MITREMatrix, MITRECell, KillChainBar, TechniqueDetail)
├── ooda/       (OODAIndicator, OODATimeline, PhaseCard)
├── c5isr/      (DomainStatusCard, HealthBar, C5ISRGrid)
├── topology/   (ForceGraph3D, TopologyControls, NodeTooltip)
├── modal/      (HexConfirmModal, DetailPanel)
└── nav/        (NavItem, TabBar)
```

- **優點**：按業務領域分組，開發時直覺定位；每個目錄對映一個設計關注點；3D 拓樸元件隔離（方便 SSR 排除）
- **缺點**：部分元件可能跨領域使用（如 Badge 在多處出現）
- **風險**：低——atoms/ 作為基礎層被其他類目引用，是標準模式

#### 選項 B：Atomic Design（atoms / molecules / organisms / templates / pages）

- **優點**：業界廣為人知的分類方法
- **缺點**：Athena 的領域特殊性（MITRE、OODA、C5ISR）使得 molecules vs organisms 邊界模糊；開發時需思考「這是 molecule 還是 organism？」增加認知負擔
- **風險**：領域元件（MITREMatrix、OODAIndicator）不自然地落入 Atomic 分類

### 設計 Token 整合

#### 選項 A：Pencil.dev 變數 → Tailwind 自訂 Theme Token

將 `athena-design-system.pen` 的 32 個設計變數對映至 `tailwind.config.ts`：

```typescript
// tailwind.config.ts
theme: {
  extend: {
    colors: {
      'athena-bg':      'var(--color-bg-primary)',
      'athena-surface': 'var(--color-bg-surface)',
      'athena-accent':  'var(--color-accent)',
      // ... 映射 .pen 變數
    }
  }
}
```

- **優點**：設計稿與程式碼共用同一套 Token；Tailwind 的 utility class 直接使用 `bg-athena-surface`；設計變更只需更新 CSS 變數
- **缺點**：需手動建立 .pen 變數 → CSS 變數的映射（一次性工作）
- **風險**：Pencil.dev 變數更新時需同步 tailwind.config.ts

#### 選項 B：直接使用 Tailwind 預設 Token

- **優點**：零配置
- **缺點**：設計稿的色彩、間距、圓角無法直接對映；像素級對齊需大量 arbitrary value `[#1a1a2e]`
- **風險**：設計與程式碼分離，維護成本高

### 3D 拓樸 SSR 處理

#### 選項 A：`dynamic(() => import(...), { ssr: false })` + `"use client"`

```typescript
// components/topology/ForceGraph3D.tsx
"use client";
import dynamic from 'next/dynamic';

const ForceGraph = dynamic(
  () => import('react-force-graph-3d'),
  { ssr: false }
);
```

- **優點**：Next.js 官方推薦模式；3D 元件在 client 端渲染，其餘頁面保留 SSR/RSC 優勢；Three.js WebGL 初始化不在 server 端執行
- **缺點**：首次載入有短暫 loading 狀態
- **風險**：低——Battle Monitor Demo 已驗證此模式可行

#### 選項 B：整個 `/monitor` 頁面標記為 `"use client"`

- **優點**：更簡單
- **缺點**：整頁失去 Server Components 優勢；其他非 3D 元件（Log Stream、Agent Panel）也被迫 client-only
- **風險**：效能損失，不利於未來優化

---

## 決策（Decision）

每個問題選擇 **選項 A**：

| 決策 | 選擇 | 關鍵理由 |
|------|------|---------|
| 元件分類 | 領域驅動 10 類目錄 | 契合 Athena 特殊領域（MITRE/OODA/C5ISR） |
| 設計 Token | .pen 變數 → Tailwind Theme Token | 設計稿與程式碼單一真相來源 |
| 3D SSR | dynamic import + `"use client"` | 最小化 client-only 範圍 |

設計對齊原則：
- `.pen` 設計稿為 UI 真相來源——元件須像素級對齊
- 每個 `.pen` 元件對映一個 React 元件檔案
- 32 個設計變數透過 CSS Custom Properties 統一管理

---

## 後果（Consequences）

**正面影響：**

- 開發時按領域目錄定位元件，無需思考 Atomic Design 層級
- Tailwind Token 整合使 `bg-athena-surface` 等 class 語義清晰
- 3D 拓樸隔離在 `topology/` 目錄，SSR 排除邏輯集中管理
- 設計師修改 `.pen` 變數後，開發者只需更新 CSS 變數即可全域生效

**負面影響 / 技術債：**

- .pen → CSS 變數映射需手動建立（Phase 3 一次性工作，約 32 筆）
- `topology/` 下的元件測試需 mock WebGL context
- 領域目錄數量（10 類）較多，新增元件時需判斷歸屬

**後續追蹤：**

- [ ] Phase 3.1：建立 `frontend/src/types/` 對映後端 Enum + Model
- [ ] Phase 3.2：實作 layout/ 元件（Sidebar、AlertBanner、PageHeader）
- [ ] Phase 3.4：實作 atoms/ 元件（Button、Badge、StatusDot 等）
- [ ] Phase 4.4：實作 topology/ 元件（ForceGraph3D + dynamic import）

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（Next.js + Tailwind 選型）、ADR-007（WebSocket hook 在 hooks/ 目錄）、ADR-004（HexConfirmModal 在 modal/ 目錄）、ADR-012（c5isr/ 前端元件目錄的 C5ISR 框架映射）

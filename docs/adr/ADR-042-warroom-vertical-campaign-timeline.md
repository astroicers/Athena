# [ADR-042]: War Room Vertical Campaign Timeline

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-22 |
| **決策者** | 架構師 / 前端負責人 |

---

## 背景（Context）

War Room 原為 3-column 靜態佈局：

| 左欄 | 中欄 | 右欄 |
|------|------|------|
| OODA Loop 狀態 | C5ISR + Mermaid 流程圖 | 行動日誌 |

存在以下問題：

1. **展示性不足**：3-column 佈局適合監控，但不適合向客戶展示攻擊進程的簡報場景
2. **缺乏操作介入點**：操作員無法在 OODA 循環之間注入指令（Directive），只能被動觀察
3. **Mermaid 捆綁過重**：中欄使用 Mermaid.js 渲染 C5ISR 狀態圖，打包後佔 158kB，對於僅顯示狀態資訊而言過於沉重
4. **無自動模式**：AI 每次 OODA 循環後都需要人工確認，無法連續自主執行

---

## 評估選項（Options Considered）

### 選項 A：優化現有 3-column 佈局

- **優點**：改動最小，保留現有結構
- **缺點**：無法解決展示性問題；操作介入點需大幅修改中欄邏輯；Mermaid 依賴仍在
- **風險**：越加越複雜，3-column 空間有限

### 選項 B：垂直 Campaign Timeline + Status Panel

- **優點**：
  - 時間線自然呈現攻擊進程，適合展示
  - DirectiveInput 組件提供清晰的操作介入點
  - 移除 Mermaid 依賴，bundle size 大幅縮減
  - Auto Mode 滿足自主執行需求
  - C5ISR 健康狀態內嵌於 ORIENT 階段，資訊密度更高
- **缺點**：
  - 需要建立 7 個新組件
  - 後端可能需要新增 Directive API
  - 與 SPEC-050（Mermaid Flow Visualization）方向不同
- **風險**：新佈局的資訊密度需要反覆調校

### 選項 C：Tab 切換式佈局

- **優點**：Tab 切換可容納更多資訊面板
- **缺點**：切換隱藏了時序關係；操作員無法同時看到 timeline 和 status
- **風險**：關鍵資訊隱藏在非活躍 tab 中，不利於即時決策

---

## 決策（Decision）

我們選擇 **選項 B：垂直 Campaign Timeline + Status Panel**，因為：

1. 時間線佈局天然適合展示攻擊滲透進程（Recon -> OODA iterations -> Target Pivots -> Mission Objective）
2. DirectiveInput 組件解決了操作介入的核心需求
3. 移除 Mermaid 從 main bundle 顯著減少打包體積（158kB -> 7kB）
4. Auto Mode toggle 為未來全自主 OODA 循環鋪路

### 佈局架構

```
┌──────────────────────────────────────────────┐
│                War Room                       │
├────────────────────────┬─────────────────────┤
│   Campaign Timeline    │   Status Panel      │
│   (scrollable)         │   (fixed, 260px)    │
│                        │                     │
│ ▼ Recon               │  ┌─ C5ISR Health ─┐ │
│   └─ scan results     │  │ CMD   94% OK   │ │
│                        │  │ CTRL  91% OK   │ │
│ ▼ OODA Iteration #1   │  │ COMMS 35% CRIT │ │
│   ├─ OBSERVE          │  │ COMP  88% OK   │ │
│   ├─ ORIENT (C5ISR)   │  │ CYBER 65% WARN │ │
│   ├─ DECIDE           │  │ ISR   72% WARN │ │
│   └─ ACT              │  └────────────────┘ │
│                        │                     │
│ ▼ DirectiveInput      │  ┌─ Risk/Noise ───┐ │
│   └─ [operator cmd]   │  │ Noise: 3/10    │ │
│                        │  │ Risk:  Medium  │ │
│ ▼ OODA Iteration #2   │  │ Decision: ...  │ │
│   ├─ OBSERVE          │  └────────────────┘ │
│   ├─ ORIENT (C5ISR)   │                     │
│   ├─ DECIDE           │  [Auto Mode: OFF]   │
│   └─ ACT              │                     │
│                        │                     │
│ ▼ Target Pivot        │                     │
│   └─ new target info  │                     │
│                        │                     │
│ ▼ Mission Objective   │                     │
│   └─ completion status│                     │
└────────────────────────┴─────────────────────┘
```

### Timeline 節點類型

| 節點類型 | 說明 | 圖示/色彩 |
|----------|------|-----------|
| Recon | 初始偵察階段 | Sapphire Blue (`#1E6091`) |
| OODA Iteration | 包含 4 sub-phase（O-O-D-A） | 依 phase 狀態變色 |
| Directive | 操作員指令注入點 | Amber (`#B45309`) |
| Target Pivot | 攻擊目標切換 | Emerald (`#059669`) |
| Mission Objective | 最終任務目標達成 | 成功時 Emerald，進行中 Sapphire |

### 新增組件清單

| 組件 | 路徑 | 說明 |
|------|------|------|
| `CampaignTimeline` | `components/warroom/CampaignTimeline.tsx` | 主時間線容器 |
| `TimelineNode` | `components/warroom/TimelineNode.tsx` | 單一時間線節點 |
| `OodaIterationCard` | `components/warroom/OodaIterationCard.tsx` | OODA 迭代展開卡片 |
| `DirectiveInput` | `components/warroom/DirectiveInput.tsx` | 操作員指令輸入 |
| `StatusPanel` | `components/warroom/StatusPanel.tsx` | 右側固定狀態面板 |
| `C5ISRInlineHealth` | `components/warroom/C5ISRInlineHealth.tsx` | ORIENT 階段內嵌 C5ISR 健康 |
| `AutoModeToggle` | `components/warroom/AutoModeToggle.tsx` | 自動模式開關 |

### Mermaid 移除策略

- 從 main bundle 移除 `mermaid`（`react-mermaid2` / `mermaid`）依賴
- 若未來仍需 Mermaid（如 SPEC-050 場景），改為 dynamic import（`next/dynamic`）
- 預期 bundle size 變化：158kB -> 7kB（僅保留 timeline CSS）

---

## 後果（Consequences）

**正面影響：**
- Bundle size 減少約 150kB（移除 Mermaid main bundle 依賴）
- 攻擊進程以時間線呈現，展示效果大幅提升
- 操作員有明確的指令注入點（DirectiveInput）
- Auto Mode 支持未來全自主 OODA 循環

**負面影響 / 技術債：**
- 需建立 7 個新組件（`components/warroom/`）
- 後端需新增 Directive API endpoint（接收操作員指令）
- Auto Mode 需後端支持自主 OODA cycling（無人確認連續執行）
- SPEC-050（Mermaid Flow Visualization）需重新評估定位——可能降級為 optional/lazy-loaded 功能

**後續追蹤：**
- [ ] 建立 7 個 War Room 組件
- [ ] 後端：`POST /operations/{id}/directives` API
- [ ] 後端：Auto Mode OODA cycling endpoint
- [ ] 重新評估 SPEC-050 與本架構的關係
- [ ] 前端：Mermaid dynamic import 遷移（若保留）
- [ ] E2E 測試：timeline rendering + directive input

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Bundle size | main chunk < 200kB（移除 Mermaid 後） | `next build` + `@next/bundle-analyzer` | 組件完成時 |
| Timeline 渲染 | 50 個 OODA iterations 渲染 < 100ms | Chrome DevTools Performance | 組件完成時 |
| Directive 延遲 | 操作員指令 -> OODA 接收 < 500ms | WebSocket 測試 | API 完成時 |
| Auto Mode 連續執行 | 無人介入連續 10 次 OODA cycling 無錯誤 | 整合測試 | Auto Mode 完成時 |

> 若 timeline 在高迭代次數（100+）下出現渲染卡頓，應評估虛擬滾動（react-window）方案。

---

## 關聯（Relations）

- 取代：無（War Room 首次重大架構變更）
- 被取代：無
- 參考：ADR-003（OODA Loop Engine Architecture）、ADR-012（C5ISR Framework Mapping）、ADR-040（C5ISR Reverse OODA Influence）、SPEC-050（OODA↔C5ISR Mermaid Flow Visualization，需重新評估）

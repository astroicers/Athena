# Attack Situation Diagram — 視覺重新設計

> 將 Situation Diagram 提升至與 Topology/C5ISR 同等的 SVG 視覺水準

| 欄位 | 內容 |
|------|------|
| **日期** | 2026-03-04 |
| **狀態** | **Implemented** ✅ (2026-03-05) |
| **影響範圍** | `/monitor` → SITUATION tab |
| **修改檔案** | `SituationNode.tsx`, `SituationEdge.tsx`, `AttackSituationDiagram.tsx`, `C5ISRMiniBar.tsx` |

---

## 變更摘要

### Before
- 節點：140×70 `<rect>` 圓角矩形，純色邊框
- 連接線：`<line>` 直線 + dash 動畫
- C5ISR 列：HTML `<div>` + 細進度條
- 背景：空白

### After

#### SituationNode — 六角形發光節點
- 外框：flat-top hexagon `<polygon>`（120×104）
- 背景：`<radialGradient>` 從 stage color → `#1a1a2e`
- 多層 glow：`<feGaussianBlur>` stdDeviation 3/6（active 加倍至 6/12）
- 進度弧：`strokeDasharray` 沿六角形邊緣表示 `successCount/totalCount`
- active 節點帶 pulse 動畫、inactive 節點 opacity 0.3

#### SituationEdge — 漸層曲線 + 粒子動畫
- 路徑：`<path>` cubic bezier 曲線（帶上弧弧度）
- 漸層：`<linearGradient>` 從 source → target stage color
- 粒子：`<circle>` + `<animateMotion>` 沿曲線路徑移動
  - completed：3 粒子 / active：1 粒子 / pending：0 粒子
- 箭頭：終點 `<circle>` dot

#### AttackSituationDiagram — 背景 + SVG defs
- 背景網格：`<pattern>` grid（40px 間距，`#2a2a4a` opacity 0.25）
- 掃描線動畫：`<rect>` + `linearGradient`（`#00d4ff` opacity 0.04，6s 循環）
- 中線導引：虛線水平線（opacity 0.2）
- viewBox 從 `1200×300` → `1200×340`

#### C5ISRMiniBar — 六角形 mini gauge
- 每個 domain 改用 28×32 `<svg>` 六角形 gauge
- `<polygon>` + `strokeDasharray` 表示 health %
- 中央顯示百分比數字

## 設計一致性

| 設計語言 | 來源 | 應用 |
|---------|------|------|
| Radial gradient | `NetworkTopology.tsx` Canvas gradient | SVG `<radialGradient>` |
| Multi-layer glow | Topology 2-layer glow | SVG `<feGaussianBlur>` filter |
| Particle animation | Topology `linkDirectionalParticles` | SVG `<animateMotion>` |
| Hexagonal gauge | `DomainCard.tsx` HexGauge | Mini bar hex gauge |
| Color system | `globals.css` custom properties | 統一使用 |
| Kill chain colors | `NetworkTopology.tsx:28-36` | 共用色碼 |

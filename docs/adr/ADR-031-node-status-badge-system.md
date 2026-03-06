# [ADR-031]: Node Status Badge System

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 拓撲圖使用 Canvas 2D 繪製力導向圖。目前節點的視覺資訊層如下：

| 層 | 視覺元素 | 資訊類型 |
|----|---------|---------|
| 核心填充 | `PHASE_COLORS[attack_phase]` | 攻擊階段（session/scanning/idle…） |
| 中央圖示 | `drawRoleIcon` | 角色（DC/Server/Workstation…） |
| Kill Chain ring | 彩色外圈 | 當前 kill chain 階段 |
| OODA ring | 虛線外圈 | OODA 循環階段（active target only） |
| Arc bars | 四象限弧形 | 數值統計（掃描次數/端口數/情報數/憑證數） |

### 問題

1. **`is_compromised` 無視覺表達**：後端已傳送 `is_compromised` 到前端，graphData 也提取了 `isCompromised` 布林值，但 canvas 繪製完全不使用此欄位。使用者無法一眼辨識哪些節點已被入侵。

2. **Arc bars 語義不足**：弧形長度表示「數量」（幾次掃描、幾個端口），但紅隊指揮官更需要的是「狀態」（有沒有偵察過、有沒有入侵、什麼權限等級、有沒有持久化）。

3. **空間衝突**：Arc bars 位於 `size + 6` 半徑處，與 Kill Chain ring（`size + 2`）和任何新增的 badge 系統在視覺空間上互相干擾。

---

## 評估選項（Options Considered）

### 選項 A：在 arc bars 之外添加 badges（共存）

- **做法**：保留 arc bars，在更外層（`size + 10`）放置四角 badges
- **優點**：資訊最完整
- **缺點**：節點周圍過於擁擠、badges 與 arcs 語義重疊、縮放時雜亂

### 選項 B：用 DOM overlay 繪製 badges

- **做法**：類似 FloatingNodeCard，用 React 元件覆蓋在 canvas 上方
- **優點**：靈活的 CSS 樣式、支援 hover/tooltip
- **缺點**：大量 DOM 節點影響效能（每個節點 4 個 badge）、與 canvas 座標同步困難

### 選項 C：Canvas 四角 badges 取代 arc bars ✅

- **做法**：移除 arc bars，在節點四角繪製狀態 badges（Canvas 2D）
- **優點**：視覺乾淨、語義清晰（從「數量」→「狀態」）、與 `drawRoleIcon` 一致的繪製方式、效能最佳
- **缺點**：失去具體數值顯示（改由 FloatingNodeCard 提供）

---

## 決策（Decision）

採用**選項 C**：Canvas 四角 badges 取代 gamification arc bars。

### 四角分區設計

| 角落 | 類別 | 觸發條件 | 圖示 | 顏色 |
|------|------|---------|------|------|
| 左上 | 偵察完成 | `scanCount > 0` | 放大鏡 | `#4488ff` (藍) |
| 右上 | 已入侵 | `isCompromised === true` | 骷髏頭 | `#ff4444` (紅) |
| 左下 | 權限等級 | `privilegeLevel != null` | 盾牌 | User=#22c55e / Admin=#eab308 / SYSTEM=#ff4444 |
| 右下 | 持久化 | `persistenceCount > 0` | 鏈結 | `#ffaa00` (金) |

### 繪製規範

- 大小：`max(size * 0.35, 3)`，隨 zoom 自動縮放
- 位置：`size * 0.85` 偏移（不與 Kill Chain ring 衝突）
- 僅有狀態時繪製（無狀態 = 隱形）
- Zoom 門檻：`globalScale > 0.4`

### 圖例更新

TopologyLegend 的 Node Stats 區段替換為 Status Badges 區段，用方向箭頭（↖↗↙↘）標示角落位置。

---

## 影響（Consequences）

| 影響面 | 描述 |
|--------|------|
| **後端** | `targets.py` topology endpoint 新增 `persistenceCount` 查詢（1 條 SQL） |
| **前端** | `NetworkTopology.tsx` 移除 ~43 行 arc bars 程式碼，新增 `drawStatusBadges` 函數群 |
| **圖例** | `TopologyLegend.tsx` Node Stats 區段替換為 Status Badges |
| **i18n** | Legend 區段新增 4 個 key（替換舊的 scans/ports/facts/credentials） |
| **向下相容** | 無 — 純前端視覺變更，API 只新增欄位 |

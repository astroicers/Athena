# SPEC-035：Node Status Badge System

> 在拓撲圖節點四角繪製攻擊狀態標記（偵察/入侵/權限/持久化），取代 gamification arc bars，讓紅隊指揮官一眼掌握每個節點的攻擊進展。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-035 |
| **關聯 ADR** | ADR-031（Node Status Badge System） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 目標（Goal）

> 實作 Canvas 2D 四角狀態標記系統：左上（偵察完成）、右上（已入侵）、左下（權限等級）、右下（持久化/橫向），取代現有 gamification arc bars。同步更新 TopologyLegend 圖例與 i18n。

---

## 輸入規格（Inputs）

### 後端 topology API 回傳的 node.data 欄位

| 欄位 | 型別 | 來源 | 現有/新增 |
|------|------|------|----------|
| `is_compromised` | boolean | `targets.is_compromised` | 現有 |
| `privilege_level` | string \| null | `targets.privilege_level` | 現有 |
| `scanCount` | integer | `COUNT(recon_scans)` | 現有 |
| `factCount` | integer | `COUNT(facts)` | 現有 |
| `credentialCount` | integer | `COUNT(facts WHERE trait LIKE 'credential.%')` | 現有 |
| `openPortCount` | integer | `JSON_LENGTH(recon_scans.open_ports)` | 現有 |
| **`persistenceCount`** | integer | `COUNT(facts WHERE trait = 'host.persistence')` | **新增** |

---

## 輸出規格（Expected Output）

### Canvas 視覺效果

```
  🔍            ☠
  左上           右上
     ╭───────╮
     │  icon  │  ← 節點本體（phase 色 + role icon）
     ╰───────╯
  🛡            🔗
  左下           右下
```

| Badge | 角落 | 觸發條件 | 顏色 | Canvas 圖示 |
|-------|------|---------|------|------------|
| Recon | 左上 (↖) | `scanCount > 0` | `#4488ff` | 放大鏡（圓 + 斜柄） |
| Compromised | 右上 (↗) | `isCompromised === true` | `#ff4444` | 骷髏頭（半圓頭 + 眼 + 顎） |
| Privilege | 左下 (↙) | `privilegeLevel != null` | User=`#22c55e` / Admin/root/sudo=`#eab308` / SYSTEM=`#ff4444` | 盾牌 |
| Persistence | 右下 (↘) | `persistenceCount > 0` | `#ffaa00` | 鏈結（兩個互扣橢圓） |

### Badge 繪製規範

| 參數 | 值 | 說明 |
|------|---|------|
| `badgeRadius` | `max(size * 0.35, 3)` | 隨 zoom 縮放 |
| `offset` | `size * 0.85` | 從圓心偏移到四角 |
| Zoom 門檻 | `globalScale > 0.4` | 縮太遠時隱藏 |
| 底圓 | 25% alpha + 0.8px border | 半透明背景 |
| 圖示 | 白色線條 0.7px | 統一 stroke style |

---

## 實作步驟

### Step 1：後端 — 新增 `persistenceCount` 查詢

**檔案**：`backend/app/routers/targets.py`

在 per-node stats 查詢區塊（line ~338-370）新增：

```python
persist_cur = await db.execute(
    "SELECT COUNT(*) AS cnt FROM facts "
    "WHERE source_target_id = ? AND operation_id = ? "
    "AND trait = 'host.persistence'",
    (tid, operation_id),
)
persist_row = await persist_cur.fetchone()
persistence_count = persist_row["cnt"] if persist_row else 0
```

在 `n.data` 賦值區塊加入 `n.data["persistenceCount"] = persistence_count`。

### Step 2：前端 — 擴充 graphData node

**檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

在 `graphData` useMemo 的 node mapping 中新增欄位：

```typescript
scanCount: (n.data?.scanCount as number) || 0,
credentialCount: (n.data?.credentialCount as number) || 0,
privilegeLevel: (n.data?.privilegeLevel as string) || null,
persistenceCount: (n.data?.persistenceCount as number) || 0,
```

### Step 3：前端 — 新增 badge 繪製函數

**檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

在 `drawRoleIcon` 函數後新增：
- `drawBadgeCircle(ctx, cx, cy, r, color)` — 通用底圓
- `drawReconBadge(ctx, cx, cy, r)` — 放大鏡
- `drawSkullBadge(ctx, cx, cy, r)` — 骷髏頭
- `drawShieldBadge(ctx, cx, cy, r, level)` — 盾牌（顏色依 level）
- `drawChainBadge(ctx, cx, cy, r)` — 鏈結
- `drawStatusBadges(ctx, x, y, size, node)` — 主函數，判斷四角

### Step 4：前端 — 替換 arc bars

**檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

在 `handleNodeCanvasObject` 中：
- **移除** gamification arc bars 區塊（line ~343-386）
- **插入** `drawStatusBadges` 呼叫

### Step 5：圖例 — 替換 Node Stats → Status Badges

**檔案**：`frontend/src/components/topology/TopologyLegend.tsx`

移除 Node Stats 區段（arc bars 圖例），替換為 Status Badges 區段：
- 4 個 badge entry，各有彩色圓 + 方向箭頭（↖↗↙↘）+ 名稱

### Step 6：i18n

**檔案**：`frontend/messages/en.json`、`frontend/messages/zh-TW.json`

Legend 區段：
- 移除：`scans`、`ports`、`facts`、`credentials`、`nodeStats`
- 新增：`statusBadges`、`recon`、`compromised`、`privilege`、`persistence`

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| 後端 topology API 回傳新增 `persistenceCount` 欄位 | per-node stats 查詢 | `backend/app/routers/targets.py` | API response 含 `persistenceCount` 欄位 |
| 前端 graphData node 新增 4 個狀態欄位 | topology 資料 mapping | `NetworkTopology.tsx`（或對應拓撲元件） | node object 含 scanCount/credentialCount/privilegeLevel/persistenceCount |
| Arc bars 移除，替換為 status badges | Canvas 繪製邏輯變更 | `NetworkTopology.tsx` — handleNodeCanvasObject | 視覺驗證：節點周圍無 arc bars，四角有 badges |
| TopologyLegend 圖例更新 | Legend 區段替換 | `TopologyLegend.tsx`（或對應 Legend 元件） | Legend 顯示 4 種 badge 而非 Node Stats |
| i18n key 變更（移除舊 key、新增新 key） | 語言檔案修改 | `frontend/messages/en.json`、`frontend/messages/zh-TW.json` | `make i18n-check` 通過 |

---

### 回退方案（Rollback Plan）

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|---------|---------|-----------|
| `git revert` commit | 無 DB schema 變更，`persistenceCount` 為查詢時計算 | Arc bars 恢復；badges 移除；`make build` 通過 | Yes — 純新增/替換 Canvas 繪製邏輯 |
| 確認 i18n key 還原 | i18n key 還原至舊版 | `make i18n-check` 通過 | Yes |

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 | 場景參考 |
|----|------|------|------|---------|---------|
| P1 | 正向 | 掃描後顯示 Recon badge | target 已執行 nmap scan（scanCount > 0） | 左上出現藍色放大鏡 badge | Scenario: Recon badge after scan |
| P2 | 正向 | Compromised badge | target is_compromised=true | 右上出現紅色骷髏頭 badge | Scenario: Compromised badge display |
| P3 | 正向 | Privilege badge（root） | privilege_level="root" | 左下出現金色盾牌 badge | Scenario: Privilege badge by level |
| P4 | 正向 | Persistence badge | persistenceCount > 0 | 右下出現金色鏈結 badge | Scenario: Persistence badge display |
| N1 | 負向 | 未掃描節點無 badge | scanCount=0, isCompromised=false, privilegeLevel=null, persistenceCount=0 | 四角無任何標記 | Scenario: Clean node has no badges |
| N2 | 負向 | Zoom 過遠隱藏 badges | globalScale < 0.4 | badges 不繪製 | Scenario: Badges hidden at low zoom |
| B1 | 邊界 | 所有狀態同時存在 | scanCount>0, isCompromised=true, privilegeLevel="SYSTEM", persistenceCount>0 | 四角都有對應標記 | Scenario: All four badges simultaneously |
| B2 | 邊界 | SYSTEM 級別用紅色盾牌 | privilegeLevel="SYSTEM" | 左下盾牌顏色為 #ff4444（紅色） | Scenario: SYSTEM privilege red shield |
| B3 | 邊界 | Arc bars 完全移除 | 任何節點 | 節點周圍無 arc bars 殘留 | Scenario: Arc bars fully removed |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Node Status Badge System
  作為紅隊指揮官，我需要一眼掌握每個拓撲節點的攻擊進展。

  Background:
    Given 一個已建立的 operation 含 target "192.168.1.10"
    And 拓撲圖已渲染

  Scenario: Recon badge after scan
    Given target 已完成 nmap 掃描（scanCount > 0）
    When 拓撲圖渲染該節點
    Then 左上角（↖）出現藍色（#4488ff）放大鏡 badge
    And badge 隨 zoom 縮放（badgeRadius = max(size * 0.35, 3)）

  Scenario: Compromised badge display
    Given target is_compromised = true
    When 拓撲圖渲染該節點
    Then 右上角（↗）出現紅色（#ff4444）骷髏頭 badge

  Scenario: Privilege badge by level
    Given target privilege_level = "root"
    When 拓撲圖渲染該節點
    Then 左下角（↙）出現金色（#eab308）盾牌 badge

  Scenario: All four badges simultaneously
    Given target scanCount=5, isCompromised=true, privilegeLevel="SYSTEM", persistenceCount=2
    When 拓撲圖渲染該節點
    Then 四角同時顯示：左上放大鏡、右上骷髏頭、左下紅色盾牌、右下金色鏈結

  Scenario: Badges hidden at low zoom
    Given globalScale < 0.4
    When 拓撲圖渲染任何節點
    Then 所有 status badges 不繪製
```

---

## 追溯性（Traceability）

| 產出物 | 檔案路徑 | 狀態 | 追溯日期 |
|--------|---------|------|---------|
| 後端 persistenceCount 查詢 | `backend/app/routers/targets.py`（line ~425） | 已實作 | 2026-03-26 |
| 前端拓撲元件 | `frontend/src/components/topology/NetworkTopology.tsx`（或同等路徑） | （待確認 — 目前未找到 topology/ 子目錄） | 2026-03-26 |
| 前端圖例元件 | `frontend/src/components/topology/TopologyLegend.tsx`（或同等路徑） | （待實作） | 2026-03-26 |
| Badge 繪製函數 | drawStatusBadges / drawReconBadge / drawSkullBadge / drawShieldBadge / drawChainBadge | （待實作） | 2026-03-26 |
| i18n — English | `frontend/messages/en.json`（statusBadges 相關 key） | （待實作） | 2026-03-26 |
| i18n — 繁體中文 | `frontend/messages/zh-TW.json`（statusBadges 相關 key） | （待實作） | 2026-03-26 |
| 後端測試 | `backend/tests/`（persistenceCount 查詢測試） | （待實作） | 2026-03-26 |
| 前端 e2e 測試 | `frontend/e2e/`（badge 視覺測試） | （待實作） | 2026-03-26 |

---

## 可觀測性（Observability）

本 SPEC 為前端 Canvas 繪製變更 + 後端查詢欄位新增，不涉及新的 API endpoint 或 MCP 工具。可觀測性 N/A。

後端 `persistenceCount` 為既有 per-node stats 查詢的擴展，效能影響包含在現有 topology API 的 response time monitoring 中。

---

## 驗收標準

| # | 場景 | 預期結果 |
|---|------|---------|
| 1 | 未掃描節點 | 四角無任何標記 |
| 2 | 執行 Recon Scan 後 | 左上出現藍色放大鏡 |
| 3 | `is_compromised = 1` | 右上出現紅色骷髏頭 |
| 4 | `privilege_level = "root"` | 左下出現金色盾牌 |
| 5 | `privilege_level = "SYSTEM"` | 左下出現紅色盾牌 |
| 6 | 有 `host.persistence` fact | 右下出現金色鏈結 |
| 7 | 所有狀態同時存在 | 四角都有對應標記 |
| 8 | `globalScale < 0.4` | 標記自動隱藏 |
| 9 | 圖例展開 | Status Badges 區段顯示四種標記 |
| 10 | Arc bars | 完全移除，節點周圍乾淨 |
| 11 | `make build` | 編譯通過 |
| 12 | `pytest` | 後端測試通過 |


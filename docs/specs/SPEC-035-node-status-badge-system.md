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

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->

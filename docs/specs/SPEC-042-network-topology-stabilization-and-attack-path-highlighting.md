# SPEC-042：Network Topology Stabilization and Attack Path Highlighting

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-042 |
| **關聯 ADR** | ADR-036（攻擊圖譜路徑最佳化） |
| **估算複雜度** | 中 |

---

## 目標（Goal）

> 解決 Network Topology 畫面中節點持續漂移導致操作員難以追蹤目標的問題，同時將攻擊圖引擎（`attack_graph_engine.py`）計算出的 `recommended_path` 以紅色高亮路徑的方式疊加於拓撲圖上，讓操作員可即時掌握系統建議的最佳攻擊鏈。附帶以子網分組（Subnet Grouping）改善多目標場景下的佈局可讀性。

---

## 輸入規格（Inputs）

### A. D3 Force 參數（前端靜態設定）

| 參數名稱 | 型別 | 現行值 | 新值 | 說明 |
|----------|------|--------|------|------|
| d3AlphaDecay | number | 0.03 | 0.08 | 3 倍加速衰減，減少節點漂移時間 |
| d3VelocityDecay | number | 0.3 | 0.5 | 增強阻尼，節點更快收斂 |
| cooldownTime | number | 5000 | 3000 | 力引擎最大運行時間（ms），加速停止 |
| d3.forceCollide | — | 無 | `d3.forceCollide().radius(nodeSize + 5).strength(0.8)` | 碰撞偵測，防止節點重疊 |

### B. 攻擊路徑資料（WebSocket）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| recommendedPath | `string[]` | `graph.updated` WebSocket 事件 | 攻擊圖節點 ID 陣列（格式 `{technique_id}::{target_id}`），長度 0-50 |
| operation_id | string | WebSocket 事件 | 對應當前 operation |

### C. 子網分組資料（REST API）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| network_segment | string | `targets` 資料表（透過 `/operations/{op_id}/topology` 回傳） | CIDR 格式（如 `10.0.1.0/24`），可為 NULL |

---

## 輸出規格（Expected Output）

### A. `graph.updated` WebSocket 事件 Payload（後端擴充）

```json
{
  "event": "graph.updated",
  "data": {
    "operation_id": "op-0001",
    "graph_id": "uuid-xxx",
    "stats": {
      "total_nodes": 26,
      "explored_nodes": 5,
      "pending_nodes": 12,
      "coverage_score": 0.19
    },
    "recommended_path": [
      "T1595.001::target-001",
      "T1190::target-001",
      "T1059.004::target-001",
      "T1021.004::target-001"
    ],
    "updated_at": "2026-03-08T12:00:00Z"
  }
}
```

`recommended_path` 為 `AttackGraph.recommended_path`（`list[str]`），每個元素為 `{technique_id}::{target_id}` 格式的攻擊圖節點 ID。前端需將相鄰兩個節點 ID 配對為邊，再比對拓撲圖上的 edge 進行高亮。

### B. Topology 節點資料擴充

`/operations/{op_id}/topology` 回傳的 `TopologyNode.data` 新增欄位：

```json
{
  "id": "target-001",
  "label": "web-server (10.0.1.5)",
  "type": "host",
  "data": {
    "hostname": "web-server",
    "ip_address": "10.0.1.5",
    "os": "Linux",
    "role": "Web Server",
    "network_segment": "10.0.1.0/24",
    "is_compromised": true,
    "is_active": true,
    "privilege_level": "User"
  }
}
```

### C. 前端 Props 型別擴充

```typescript
interface NetworkTopologyProps {
  // ... 現有 props ...
  /** 攻擊圖推薦路徑 — 攻擊圖節點 ID 陣列 */
  recommendedPath?: string[];
}
```

### D. 攻擊路徑視覺規格

| 屬性 | 值 | 說明 |
|------|------|------|
| 邊線顏色 | `#ff2222`（紅色） | 與既有 session edge `rgba(255,68,68,0.7)` 區別 |
| 邊線寬度 | 3px | 比 session edge（2.5px）略寬 |
| 動畫效果 | CSS keyframe pulse — `opacity: 0.6 → 1.0`，週期 1.5s | Canvas 實作用 `globalAlpha` 在 `requestAnimationFrame` 中交替 |
| 粒子數量 | 4 | 比 session edge（3）多一顆粒子 |
| 粒子顏色 | `#ff2222` | 與邊線同色 |
| 粒子速度 | 0.008 | 比一般 edge（0.005）略快 |

### E. 子網分組視覺規格

| 屬性 | 值 | 說明 |
|------|------|------|
| X 軸偏移 | 每個子網 200px | 透過 `d3.forceX()` 依子網分組施加吸引力 |
| 邊界框 | 虛線矩形，stroke `rgba(255,255,255,0.15)`，lineWidth 1，dash `[6, 4]` | Canvas 繪製，包圍同子網所有節點 + padding 30px |
| 子網標籤 | 邊界框左上角，字體 `10px monospace`，顏色 `rgba(255,255,255,0.4)` | 顯示 `network_segment` 值（如 `10.0.1.0/24`） |
| forceX 強度 | 0.15 | 柔性吸引，不會完全覆蓋 link force |

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| `graph.updated` 事件新增 `recommended_path` 欄位 | 攻擊圖 `rebuild()` 執行後 WebSocket broadcast | 所有訂閱 `graph.updated` 的前端元件 | 單元測試驗證 payload 含 `recommended_path`；空路徑時為 `[]` |
| topology endpoint 新增 `network_segment` 至 node data | `GET /operations/{op_id}/topology` 回傳時 | `frontend/src/components/ui/Skeleton.tsx`（NetworkTopology 元件） | API 測試驗證 node.data 含 `network_segment` 欄位 |
| D3 force 參數變更（alphaDecay、velocityDecay、cooldownTime） | NetworkTopology 元件載入時 | 拓撲圖節點佈局 | E2E 驗證：節點 3 秒內停止漂移 |
| 新增 `d3.forceCollide` 碰撞力 | force 引擎初始化時 | 節點間距擴展 | 視覺檢查：任意兩節點中心距離 > 半徑和 |
| TopologyLegend 新增「攻擊路徑」圖例 | Legend 渲染時 | Legend 展開高度增加 ~16px | i18n 測試：`en.json` 和 `zh-TW.json` 含 `Legend.attackPath` |

---

## 邊界條件（Edge Cases）

- **Case 1**：`recommended_path` 為空陣列 — 不渲染任何高亮邊線，行為與目前完全一致
- **Case 2**：`recommended_path` 中的節點 ID 無法對應到拓撲圖上的任何 edge — 跳過該段，僅高亮可匹配的部分。不應拋出錯誤
- **Case 3**：攻擊路徑跨越多個 target（橫向移動邊）— 路徑中的 `T1021.004::target-001` → `T1059.004::target-002` 需正確對應拓撲圖上 target-001 → target-002 的 edge
- **Case 4**：拓撲圖僅有 1 個節點（C2 + 0 targets）— 不渲染子網分組、不渲染攻擊路徑。已有的 `data.nodes.length <= 1` 守衛維持不變
- **Case 5**：所有 target 屬於同一子網 — `d3.forceX` 施加的偏移為 0（第一個子網置中），不影響佈局
- **Case 6**：`network_segment` 為 NULL — 歸入「未分類（unassigned）」群組，不繪製邊界框
- **Case 7**：D3 force 引擎尚未停止時收到新 `graph.updated` — 以最新路徑覆蓋，不累積。用 `useRef` 儲存最新路徑以避免 stale closure
- **Case 8**：節點數量 > 50 — 子網邊界框仍正確計算，但 `forceCollide` 半徑不隨節點數量動態調整（維持 `nodeSize + 5`）

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| `git revert <commit>` | 無資料損失。`recommended_path` 為攻擊圖引擎即時計算的衍生值，不持久化 | `make test && make lint` 全數通過；拓撲圖恢復舊版佈局 | 否（待實作後驗證） |
| 無需額外 DB migration | 無 DB schema 變更 | N/A | N/A |

> **不可逆評估**：此變更完全可逆。所有修改均為前端渲染邏輯和 WebSocket payload 追加欄位。

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景描述 | 輸入 | 預期結果 | 對應驗收場景 |
|----|------|----------|------|----------|-------------|
| P1 | 正向 | 攻擊路徑高亮渲染 — recommended_path 含 4 個節點 | WebSocket `graph.updated` 含 `recommended_path: ["T1595.001::t1","T1190::t1","T1059.004::t1","T1021.004::t2"]` | 拓撲圖中 C2→t1 和 t1→t2 邊以紅色 `#ff2222` 渲染，寬度 3px | Scenario: Attack path rendering on topology |
| P2 | 正向 | 子網分組 — 2 個不同子網 | topology API 回傳 target-A `10.0.1.0/24`、target-B `10.0.2.0/24` | 兩組節點在 X 軸偏移 200px，各有虛線邊界框和 CIDR 標籤 | Scenario: Subnet grouping layout |
| P3 | 正向 | D3 force 參數收斂 | 拓撲圖載入 5 個節點 | 節點 3 秒內停止漂移（`onEngineStop` 觸發） | Scenario: Attack path rendering on topology |
| N1 | 負向 | recommended_path 為空 | WebSocket 事件 `recommended_path: []` | 無高亮邊線，畫面與修改前一致 | Scenario: Attack path rendering on topology |
| N2 | 負向 | 路徑節點 ID 無法匹配拓撲邊 | `recommended_path` 含不存在的 target ID | 跳過無法匹配的段落，不拋錯 | Scenario: Attack path rendering on topology |
| N3 | 負向 | 僅 1 個節點（C2 + 0 targets） | topology API 回傳空 targets | 不渲染子網分組、不渲染攻擊路徑 | Scenario: Subnet grouping layout |
| B1 | 邊界 | network_segment 為 NULL | topology API 回傳 target 無 network_segment | 歸入未分類群組，不繪製邊界框 | Scenario: Subnet grouping layout |
| B2 | 邊界 | 所有 target 同子網 | 全部 target `network_segment=10.0.1.0/24` | `forceX` 偏移為 0（置中），不影響佈局 | Scenario: Subnet grouping layout |
| B3 | 邊界 | force 引擎未停止時收到新 graph.updated | 快速連續 2 次 WebSocket 事件 | 以最新路徑覆蓋，不累積 | Scenario: Attack path rendering on topology |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Network Topology Stabilization and Attack Path Highlighting
  SPEC-042 — D3 force 穩定化、攻擊路徑高亮、子網分組。

  Background:
    Given 系統已初始化且 operation "op-test" 已建立
    And operation 中有 target "target-001" IP "10.0.1.5" network_segment "10.0.1.0/24"
    And operation 中有 target "target-002" IP "10.0.2.10" network_segment "10.0.2.0/24"

  Scenario: Attack path rendering on topology
    Given 攻擊圖引擎計算出 recommended_path ["T1595.001::target-001","T1190::target-001","T1021.004::target-002"]
    When WebSocket 廣播 graph.updated 事件含 recommended_path
    Then WarRoom 頁面中 NetworkTopology 元件收到 recommendedPath prop
    And 拓撲圖中 C2→target-001 邊以紅色 #ff2222 渲染、寬度 3px
    And 拓撲圖中 target-001→target-002 邊以紅色 #ff2222 渲染、寬度 3px
    And 路徑邊線具有 opacity 脈動動畫（週期 1.5s）
    And 路徑邊線粒子數為 4，顏色 #ff2222
    When recommended_path 為空陣列
    Then 無高亮邊線渲染，畫面與修改前一致
    When recommended_path 含無法匹配的節點 ID
    Then 跳過該段，不拋出錯誤

  Scenario: Subnet grouping layout
    When 拓撲圖載入含 2 個不同子網的 targets
    Then target-001 和 target-002 在 X 軸上有 200px 偏移
    And 每個子網繪製虛線邊界框（stroke rgba(255,255,255,0.15)、dash [6,4]）
    And 邊界框左上角標示子網 CIDR（如 "10.0.1.0/24"）
    When 所有 target 屬於同一子網
    Then forceX 偏移為 0，佈局不受影響
    When target 的 network_segment 為 NULL
    Then 該節點不繪製邊界框
    And TopologyLegend 顯示「攻擊路徑（建議）」項目
```

---

## 追溯性（Traceability）

| 項目 | 檔案路徑 | 狀態 | 備註 |
|------|----------|------|------|
| SPEC 文件 | `docs/specs/SPEC-042-network-topology-stabilization-and-attack-path-highlighting.md` | 已建立 | 本文件 |
| 後端實作 — 攻擊圖引擎 | `backend/app/services/attack_graph_engine.py` | 已存在 | broadcast payload 擴充 `recommended_path` |
| 後端實作 — Topology API | `backend/app/routers/targets.py` | 已存在 | `get_topology()` node data 加入 `network_segment` |
| 後端模型 — AttackGraph | `backend/app/models/attack_graph.py` | 已存在 | `recommended_path: list[str]` |
| 前端實作 — NetworkTopology | `frontend/src/components/ui/Skeleton.tsx` | 已存在 | （待實作）force 參數、攻擊路徑渲染、子網分組 |
| 前端實作 — WarRoom | `frontend/src/app/warroom/page.tsx` | 已存在 | `graph.updated` 訂閱、`recommendedPath` state |
| 後端測試 — 攻擊圖 | `backend/tests/test_attack_graph.py` | 已存在 | 攻擊圖相關測試 |
| 後端測試 — 攻擊圖 router | `backend/tests/test_attack_graph_router.py` | 已存在 | 攻擊圖 API 測試 |
| E2E 測試 — WarRoom | `frontend/e2e/warroom.spec.ts` | 已存在 | WarRoom E2E 測試 |
| E2E 測試 — WarRoom tabs | `frontend/e2e/sit-warroom-tabs.spec.ts` | 已存在 | WarRoom SIT 測試 |
| ADR | ADR-036 | 已接受 | 攻擊圖譜路徑最佳化 |

> 追溯日期：2026-03-26

---

## 可觀測性（Observability）

| 項目 | 類型 | 名稱/格式 | 觸發條件 | 說明 |
|------|------|-----------|----------|------|
| 攻擊路徑廣播 | log (INFO) | `graph.updated broadcast: recommended_path length=%d` | `rebuild()` 完成後 | 記錄路徑節點數量 |
| Topology API network_segment | log (DEBUG) | `topology node %s: network_segment=%s` | `get_topology()` 執行時 | 記錄每個節點的子網歸屬 |
| 前端 | N/A | — | — | 前端為純渲染邏輯，無後端可觀測需求 |

---

## 實作細節（Implementation Details）

### Phase 1：D3 Force 參數調優（減少漂移）

**檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

1. 修改 `<ForceGraph2DComp>` 的靜態 props：

```tsx
// 現行值 → 新值
d3AlphaDecay={0.08}       // was 0.03
d3VelocityDecay={0.5}     // was 0.3
cooldownTime={3000}        // was 5000
```

2. 在 `useEffect` 中設定 `d3Force` 時新增碰撞力：

```tsx
useEffect(() => {
  const fg = fgRef.current;
  if (!fg) return;
  try {
    fg.d3Force("charge")?.strength(-400);
    fg.d3Force("link")?.distance(100);
    // SPEC-042: 碰撞偵測防止節點重疊
    fg.d3Force("collide", d3.forceCollide()
      .radius((node: Record<string, unknown>) => ((node.nodeSize as number) || 8) + 5)
      .strength(0.8)
    );
  } catch { /* not ready */ }
}, [graphData, ForceGraph2DComp]);
```

注意：`react-force-graph-2d` 已內建 d3-force，透過 `fg.d3Force(name, force)` API 設定自訂力。需從 `d3-force` 引入 `forceCollide`：

```tsx
import { forceCollide } from "d3-force";
```

### Phase 2：攻擊路徑資料傳遞

**後端檔案**：`backend/app/services/attack_graph_engine.py`

在 `rebuild()` 方法中，將 `recommended_path` 加入 WebSocket broadcast payload：

```python
await self._ws.broadcast(operation_id, "graph.updated", {
    "operation_id": operation_id,
    "graph_id": graph.graph_id,
    "stats": {
        "total_nodes": len(graph.nodes),
        "explored_nodes": explored,
        "pending_nodes": pending,
        "coverage_score": graph.coverage_score,
    },
    "recommended_path": graph.recommended_path,  # SPEC-042: 新增
    "updated_at": graph.updated_at,
})
```

**前端檔案**：`frontend/src/app/warroom/page.tsx`

新增 state 和 WebSocket 訂閱：

```tsx
const [recommendedPath, setRecommendedPath] = useState<string[]>([]);

// 訂閱 graph.updated
useEffect(() => {
  const unsub = ws.subscribe("graph.updated", (raw: unknown) => {
    const data = raw as Record<string, unknown>;
    const path = data.recommended_path as string[] | undefined;
    if (path) setRecommendedPath(path);
  });
  return unsub;
}, [ws]);
```

傳遞至 `<NetworkTopology>`：

```tsx
<NetworkTopology
  data={topology}
  recommendedPath={recommendedPath}
  // ... 其餘 props
/>
```

### Phase 3：攻擊路徑前端渲染

**檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

#### 3a. 路徑匹配邏輯

`recommended_path` 中的元素為攻擊圖節點 ID（`{technique_id}::{target_id}`），需轉換為拓撲圖的 target ID 對：

```tsx
const attackPathEdges = useMemo(() => {
  if (!recommendedPath || recommendedPath.length < 2) return new Set<string>();
  const edges = new Set<string>();
  for (let i = 0; i < recommendedPath.length - 1; i++) {
    const srcTargetId = recommendedPath[i].split("::")[1];
    const tgtTargetId = recommendedPath[i + 1].split("::")[1];
    if (srcTargetId && tgtTargetId && srcTargetId !== tgtTargetId) {
      // 跨 target 的橫向移動邊
      edges.add(`${srcTargetId}→${tgtTargetId}`);
    }
  }
  // 同時標記路徑涉及的 target，用於 C2→target 邊的高亮
  const pathTargetIds = new Set(
    recommendedPath.map((nid) => nid.split("::")[1]).filter(Boolean)
  );
  pathTargetIds.forEach((tid) => edges.add(`athena-c2→${tid}`));
  return edges;
}, [recommendedPath]);
```

#### 3b. 邊線渲染回調修改

修改 `getLinkColor`、`getLinkWidth`、`getLinkDash`、`getLinkParticles` 回調，在路徑匹配時覆蓋預設值：

```tsx
const getLinkColor = useCallback((link: Record<string, unknown>) => {
  const src = typeof link.source === "object"
    ? (link.source as Record<string, unknown>).id as string
    : link.source as string;
  const tgt = typeof link.target === "object"
    ? (link.target as Record<string, unknown>).id as string
    : link.target as string;
  if (attackPathEdges.has(`${src}→${tgt}`) || attackPathEdges.has(`${tgt}→${src}`)) {
    return "#ff2222";
  }
  // ... 既有邏輯
}, [attackPathEdges]);
```

#### 3c. 脈動動畫

使用 `requestAnimationFrame` 驅動 `globalAlpha` 脈動。在元件層級維護一個 `animationPhase` ref：

```tsx
const animPhase = useRef(0);

useEffect(() => {
  let raf: number;
  const tick = () => {
    animPhase.current = (Date.now() % 1500) / 1500; // 0 → 1 週期 1.5s
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}, []);
```

在 `getLinkWidth` 中，攻擊路徑邊的寬度加入脈動：

```tsx
if (isAttackPath) {
  const pulse = 0.6 + 0.4 * Math.sin(animPhase.current * Math.PI * 2);
  return 3 * pulse; // 寬度在 1.8-3px 間脈動
}
```

### Phase 4：子網分組

**後端檔案**：`backend/app/routers/targets.py`

在 `get_topology()` 的 `TopologyNode.data` 中加入 `network_segment`：

```python
nodes.append(
    TopologyNode(
        id=t["id"],
        label=f"{t['hostname']} ({ip})",
        type="host",
        data={
            "hostname": t["hostname"],
            "ip_address": ip,
            "os": t["os"],
            "role": t["role"],
            "network_segment": t["network_segment"],  # SPEC-042: 新增
            "is_compromised": bool(t["is_compromised"]),
            "is_active": bool(t["is_active"]),
            "privilege_level": t["privilege_level"],
        },
    )
)
```

**前端檔案**：`frontend/src/components/topology/NetworkTopology.tsx`

在 `graphData` 的 `useMemo` 中加入 `networkSegment`：

```tsx
return {
  id: n.id,
  // ... 現有欄位
  networkSegment: (n.data?.network_segment as string) || null,
};
```

在 force 設定的 `useEffect` 中加入 `d3.forceX`：

```tsx
// SPEC-042: 子網分組 X 軸偏移
const segments = [...new Set(
  graphData.nodes
    .map((n) => n.networkSegment)
    .filter(Boolean)
)].sort();

if (segments.length > 1) {
  const segmentIndex = new Map(segments.map((s, i) => [s, i]));
  const centerOffset = ((segments.length - 1) * 200) / 2;
  fg.d3Force("subnetX", d3.forceX()
    .x((node: Record<string, unknown>) => {
      const seg = node.networkSegment as string | null;
      if (!seg) return 0;
      const idx = segmentIndex.get(seg) ?? 0;
      return idx * 200 - centerOffset;
    })
    .strength(0.15)
  );
}
```

子網邊界框在 `nodeCanvasObject` 之後的額外 Canvas 繪製層實作。使用 `onRenderFramePost` callback（`react-force-graph-2d` 支援）繪製虛線矩形和標籤。

### Phase 5：TopologyLegend 擴充

**檔案**：`frontend/src/components/topology/TopologyLegend.tsx`

在 `EDGE_ENTRIES` 陣列中新增攻擊路徑項目：

```tsx
const EDGE_ENTRIES = [
  // ... 既有項目
  { key: "attackPath", color: "#ff2222", width: 3, dash: null },
];
```

在 `frontend/messages/en.json` 和 `frontend/messages/zh-TW.json` 的 `Legend` 區塊新增翻譯：

```json
{
  "Legend": {
    "attackPath": "Attack Path (Recommended)"
  }
}
```

```json
{
  "Legend": {
    "attackPath": "攻擊路徑（建議）"
  }
}
```

---

## 驗收標準（Done When）

### Phase 1 — D3 Force 參數調優

- [ ] `d3AlphaDecay` 設為 `0.08`，`d3VelocityDecay` 設為 `0.5`，`cooldownTime` 設為 `3000`
- [ ] `d3.forceCollide` 已啟用，半徑為 `nodeSize + 5`，強度 `0.8`
- [ ] 拓撲圖開啟後 3 秒內節點完全停止漂移（以 `onEngineStop` callback 驗證）
- [ ] 節點不再重疊（視覺檢查：任意兩節點中心距離 > 兩節點半徑之和）

### Phase 2 — 攻擊路徑資料傳遞

- [ ] `graph.updated` WebSocket 事件 payload 包含 `recommended_path` 欄位（`string[]`）
- [ ] `recommended_path` 為空時，payload 中該欄位為 `[]`（非 null、非 omitted）
- [ ] WarRoom 頁面正確訂閱 `graph.updated` 並將路徑傳遞至 `<NetworkTopology>`

### Phase 3 — 攻擊路徑前端渲染

- [ ] 推薦路徑上的 edge 以紅色 `#ff2222` 渲染，寬度 3px
- [ ] 路徑邊線具有 opacity 脈動動畫（0.6 → 1.0，週期 1.5s）
- [ ] 路徑邊線粒子數為 4，顏色 `#ff2222`，速度 `0.008`
- [ ] `recommended_path` 中節點 ID 無法匹配拓撲邊時，不拋出錯誤且不渲染該段
- [ ] `recommended_path` 為空時，畫面與修改前完全一致

### Phase 4 — 子網分組

- [ ] Topology API 回傳的 `TopologyNode.data` 包含 `network_segment` 欄位
- [ ] 不同子網的節點在 X 軸上有 200px 偏移（透過 `d3.forceX` 實現）
- [ ] 每個子網繪製虛線邊界框，左上角標示子網 CIDR
- [ ] 單一子網場景不產生偏移（`segments.length <= 1` 時跳過）
- [ ] `network_segment` 為 NULL 的節點不繪製邊界框

### Phase 5 — Legend 更新

- [ ] TopologyLegend 新增「攻擊路徑（建議）」項目，紅色實線，寬度 3
- [ ] `en.json` 和 `zh-TW.json` 包含 `Legend.attackPath` 翻譯鍵

### 整體驗收

- [ ] `make test` 全數通過
- [ ] `make lint` 無 error
- [ ] 無新增外部依賴（`d3-force` 已透過 `react-force-graph-2d` 內建）
- [ ] i18n schema 測試通過（`en.json` 與 `zh-TW.json` 鍵值一致）

---

## 禁止事項（Out of Scope）

- 不要修改 `attack_graph_engine.py` 的 Dijkstra 演算法或權重公式（屬 ADR-036 / SPEC-039 範疇）
- 不要新增 DB schema 變更（`network_segment` 欄位已存在於 `targets` 表）
- 不要修改 `TopologyNode` / `TopologyEdge` 的 TypeScript interface（使用既有的 `data: Record<string, unknown>` 傳遞新欄位）
- 不要修改 WebSocket 連線邏輯或事件格式（僅在 `graph.updated` 的 `data` 中追加欄位）
- 不要為攻擊路徑新增獨立的 REST API endpoint — 路徑資料僅透過 WebSocket 即時推送
- 不要引入 `d3-force` 作為獨立依賴 — 使用 `react-force-graph-2d` 內建的 d3-force

---

## 參考資料（References）

- 相關 ADR：ADR-036（攻擊圖譜規則外部化與路徑最佳化）
- 現有類似實作：
  - `backend/app/services/attack_graph_engine.py` — `compute_recommended_path()` Dijkstra 實作，`rebuild()` WebSocket broadcast
  - `backend/app/models/attack_graph.py` — `AttackGraph.recommended_path: list[str]`，節點 ID 格式 `{technique_id}::{target_id}`
  - `frontend/src/components/topology/NetworkTopology.tsx` — 現行拓撲元件，D3 force 參數、edge 渲染回調
  - `frontend/src/components/topology/TopologyLegend.tsx` — 圖例元件
  - `frontend/src/app/warroom/page.tsx` — WarRoom 頁面，WebSocket 訂閱模式
  - `backend/app/routers/targets.py` — `get_topology()` endpoint，目前未回傳 `network_segment`
- 關鍵檔案修改清單：
  - `backend/app/services/attack_graph_engine.py`（broadcast payload 擴充）
  - `backend/app/routers/targets.py`（topology node data 加入 `network_segment`）
  - `frontend/src/components/topology/NetworkTopology.tsx`（force 參數、攻擊路徑渲染、子網分組）
  - `frontend/src/components/topology/TopologyLegend.tsx`（新增攻擊路徑圖例）
  - `frontend/src/app/warroom/page.tsx`（`graph.updated` 訂閱、`recommendedPath` state）
  - `frontend/messages/en.json`（`Legend.attackPath` 翻譯）
  - `frontend/messages/zh-TW.json`（`Legend.attackPath` 翻譯）



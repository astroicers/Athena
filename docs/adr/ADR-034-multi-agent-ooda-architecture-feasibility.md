# [ADR-034]: Multi-Agent OODA Architecture Feasibility

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-07 |
| **決策者** | Athena 架構團隊 |

---

## 背景（Context）

Athena 目前的攻擊執行架構是「單腦多手」模式：

1. **單一 LLM 決策**：每輪 OODA 循環中，`OrientEngine` 呼叫一次 Opus LLM 產生 3 個戰術建議
2. **規則式決策**：`DecisionEngine` 基於風險閾值和自動化模式篩選出 `parallel_tasks[]`
3. **並行工具執行**：`SwarmExecutor` 用 `asyncio.gather` 並行執行多個工具呼叫（nmap、web-scanner 等），但每個 task **無 AI 推理能力**

這意味著：
- 每個 task 執行失敗時只能等下一輪 OODA（30 秒後）才能重新推理
- 所有 task 的策略來自同一次 LLM 呼叫，無法針對個別目標做深度探索
- 命名為 "AgentSwarm"（ADR-027），但實質是 **task parallelism**，不是 multi-agent AI

**問題：** 是否應該將架構改為真正的 Multi-Agent（每個 Agent 有獨立 OODA loop 和 LLM 推理能力）？

**額外限制：** 目前 LLM 服務僅透過 `claude login` (OAuth) 提供，非付費 API Key。

---

## 架構衝突分析

深入程式碼審查後，發現以下 **10 個硬性架構衝突**阻礙真正 Multi-Agent 實作：

### 衝突 1（致命）：SQLite 單 Writer

**檔案：** `backend/app/database.py`

SQLite WAL mode 只允許一個 writer + 多個 reader。`busy_timeout=5000ms` 意味著第二個 writer 等超過 5 秒就失敗：

```python
await db.execute("PRAGMA journal_mode = WAL;")
await db.execute("PRAGMA busy_timeout = 5000;")
```

5 個 Agent 同時寫入 `technique_executions`、`facts`、`attack_graph_nodes` → 4 個排隊，超時則 task 失敗。**這是必然發生的問題，非偶發。**

**無法在現有架構修補** — 需要替換為 PostgreSQL（影響 100+ SQL 語句）。

### 衝突 2（致命）：OODAController 單一 Phase 狀態

**檔案：** `backend/app/services/ooda_controller.py:88`

```python
await db.execute(
    "UPDATE operations SET current_ooda_phase = 'observe' ...",
)
```

`current_ooda_phase` 是 `operations` 表上的單一欄位。Agent A 在 Orient、Agent B 在 Observe → 欄位互相覆蓋 → 前端顯示錯誤狀態。

**可修補**：改為 per-agent phase tracking table。

### 衝突 3（致命）：iteration_number 競爭條件

**檔案：** `backend/app/services/ooda_controller.py:71-78`

```python
cursor = await db.execute(
    "SELECT COALESCE(MAX(iteration_number), 0) + 1 AS next_num ..."
)
ooda_id = str(uuid.uuid4())
await db.execute("INSERT INTO ooda_iterations ...")
```

兩個 Agent 同時 SELECT → 拿到相同 `next_num` → 同時 INSERT → UNIQUE 約束衝突或邏輯錯亂。

**可修補**：改用 DB-level sequence 或 UUID 排序。

### 衝突 4（硬擋）：APScheduler max_instances=1

**檔案：** `backend/app/services/ooda_scheduler.py:87-94`

```python
_scheduler.add_job(
    _run_cycle,
    max_instances=1,  # 同一時間只能跑一個 OODA cycle
)
```

直接阻止同一 operation 的多個 OODA cycle 並行。真正 Multi-Agent 需要每個 Agent 獨立觸發 loop。

**可修補**：移除 APScheduler，改為 Coordinator 分派 + Agent 自行 loop。

### 衝突 5（高）：AttackGraphEngine DELETE-then-INSERT

**檔案：** `backend/app/services/attack_graph_engine.py:164-182`

```python
await db.execute("DELETE FROM attack_graph_edges WHERE operation_id = ?")
await db.execute("DELETE FROM attack_graph_nodes WHERE operation_id = ?")
await db.commit()
graph = self._build_graph_in_memory(...)
await self._persist_graph(db, graph)
```

無鎖。兩個 Agent 同時 rebuild → Agent A 的 INSERT 被 Agent B 的 DELETE 抹掉。

**可修補**：加 advisory lock 或改為差量更新（incremental update + version column）。

### 衝突 6（高）：WebSocketManager 無同步原語

**檔案：** `backend/app/ws_manager.py:44-62`

```python
connections = self._connections.get(operation_id, set()).copy()  # 非原子
for ws in connections:
    await ws.send_text(message)
```

`self._connections` 是普通 dict，多個 Agent 同時 broadcast + connect/disconnect → dict 在迭代中被修改。

**可修補**：加 `asyncio.Lock`。

### 衝突 7（高）：SwarmExecutor 共享單一 DB 連線

**檔案：** `backend/app/services/agent_swarm.py:76-82`

```python
async def execute_swarm(self, db: aiosqlite.Connection, ...):
    results = await asyncio.gather(
        *(self._execute_single(db, ...) for st in swarm_tasks),
    )
```

所有並行 task 共用同一個 `db` 物件。aiosqlite 底層單線程 writer queue → 並行寫入實際序列化。

**可修補**：每個 Agent 用獨立 DB 連線（但在 SQLite 下仍受衝突 1 限制）。

### 衝突 8（中）：FactCollector TOCTOU 去重

**檔案：** `backend/app/services/fact_collector.py:32-81`

先 SELECT 所有 facts 到記憶體 `existing` set，再逐一 INSERT。兩個 Agent 同時做 → 都認為 fact 不存在 → 都 INSERT → UNIQUE 約束失敗，transaction rollback。

**可修補**：改用 `INSERT OR IGNORE`。

### 衝突 9（中）：全域 Singleton 無 namespace 隔離

| Singleton | 衝突點 |
|-----------|--------|
| `ws_manager` | Agent A broadcast `phase=observe`，Agent B broadcast `phase=decide` → 前端混亂 |
| `MCPClientManager._instance` | Agent A 的 MCP 呼叫失敗觸發 circuit breaker → Agent B 也被擋 |
| `node_summarizer._cache` | 無並發控制的 LRU cache |

**可修補**：加 `agent_id` namespace 或 per-agent instance。

### 衝突 10（中）：OAuth Rate Limit 無保護

**檔案：** `backend/app/services/llm_client.py`

`claude login` 的 inference 配額依帳戶方案。5 個 Agent 並行呼叫 Opus/Sonnet → 觸發 429。LLMClient 中無任何 throttle、semaphore 或 retry-after 處理。

**可修補**：加全域 `asyncio.Semaphore` + retry-after 邏輯。

---

### 衝突嚴重度總覽

| # | 衝突 | 嚴重度 | 能否在現有架構修補？ |
|---|------|--------|----------------------|
| 1 | SQLite 單 Writer | **致命** | **不能** — 需換 PostgreSQL |
| 2 | 單一 phase 狀態 | **致命** | 可以 — per-agent phase table |
| 3 | iteration_number 競爭 | **致命** | 可以 — DB sequence / UUID |
| 4 | APScheduler max_instances=1 | **硬擋** | 可以 — 改架構 |
| 5 | AttackGraph DELETE-rebuild | **高** | 可以 — advisory lock |
| 6 | WebSocket 無鎖 | **高** | 可以 — asyncio.Lock |
| 7 | 共享 DB 連線 | **高** | 可以 — 獨立連線 |
| 8 | FactCollector TOCTOU | **中** | 可以 — INSERT OR IGNORE |
| 9 | Singleton 無隔離 | **中** | 可以 — namespace |
| 10 | OAuth rate limit | **中** | 可以 — semaphore |

**結論：衝突 1（SQLite 單 Writer）是唯一無法在現有架構修補的。** 其餘 9 個都可透過加鎖、改表結構、或調整設計解決。

---

## 評估選項（Options Considered）

### 選項 A：ReAct per Task（不碰致命衝突）

在現有 SwarmExecutor 的每個 task 內加入 Haiku 驅動的 mini ReAct loop（觀察→思考→重試），讓每個任務有 2-3 步自主應變能力。

```
Coordinator (Opus, 1 次呼叫) → parallel_tasks[]
  → Task 1: 執行 → [失敗] → Haiku 判斷 → 調整參數 → 重試
  → Task 2: 執行 → [成功] → 完成
  → Task 3: 執行 → [失敗] → Haiku 判斷 → abort
```

- **優點**：零架構衝突（不碰 #1-#6），僅改 `agent_swarm.py`；OAuth 友好（Haiku 配額寬鬆）
- **缺點**：本質是「更聰明的工具執行」，不是真正 Multi-Agent；每個 task 只有 2-3 步自主性，無策略視野
- **風險**：Haiku 推理能力有限，複雜場景可能做出錯誤判斷

### 選項 B：PostgreSQL + 真正 Multi-Agent（解決全部衝突）

替換 SQLite 為 PostgreSQL，解決全部 10 個衝突，讓每個 Agent 跑獨立 mini-OODA。

```
Coordinator (Opus) → 制定戰略，分派任務
  → ReconAgent (Sonnet): 獨立 mini-OODA (observe→orient→act)
  → ExploitAgent (Sonnet): 獨立 mini-OODA
  → LateralAgent (Sonnet): 獨立 mini-OODA
  → 結果回報 Coordinator → 下一輪大 OODA
```

**必做改動：**

| 步驟 | 說明 |
|------|------|
| SQLite → PostgreSQL | 替換 aiosqlite → asyncpg，改寫 100+ SQL，新增 docker-compose postgres |
| Per-Agent OODA | 新增 `agent_ooda_iterations` 表，每個 Agent 獨立 phase 狀態 |
| Agent 調度器 | 取消 APScheduler trigger，Coordinator 分派 Agent task，Agent 自行 loop |
| AttackGraph 版本化 | rebuild 改為 incremental update + optimistic locking |
| WebSocket 加鎖 | `asyncio.Lock` 保護 `_connections` dict |
| LLM Rate Limiter | 全域 `asyncio.Semaphore` + retry-after |
| Agent 通訊層 | 共享 facts table + event bus（PG LISTEN/NOTIFY） |

- **優點**：真正的 Multi-Agent；專業分工；即時應變；更像真實紅隊；PostgreSQL 的 LISTEN/NOTIFY 天然支援 Agent 通訊
- **缺點**：資料層大幅重寫（100+ SQL）；需要新增 PostgreSQL 容器；架構複雜度大增
- **風險**：OAuth rate limit 可能限制 Agent 數量；並發 Sonnet 呼叫成本較高；debug 和可重現性降低

### 選項 C：分階段演進（A → B）

Phase 1 先做選項 A（快速見效），Phase 2 換 PostgreSQL 後升級為選項 B。

```
Phase 1: ReAct per Task — Haiku 驅動的 task 自主性
Phase 2: PostgreSQL migration — 解決致命衝突 #1
Phase 3: 專業分工 Agent — Sonnet 驅動的 mini-OODA
```

- **優點**：漸進式風險；Phase 1 立即可用
- **缺點**：Phase 1 的 ReAct 設計可能在 Phase 3 被棄用；兩階段遷移增加總工作量
- **風險**：Phase 2 的 PostgreSQL 遷移可能引入回歸問題

---

## 決策（Decision）

> **暫不決定（Proposed）。** 待以下條件之一成立後重新評估：

1. **多目標並行攻擊需求明確** — 實際運行中觀察到 30 秒 OODA 間隔不足以應對多目標場景
2. **LLM 服務升級** — 從 OAuth 升級為付費 API Key，解除 rate limit 限制
3. **SQLite 寫入瓶頸被觀察到** — SwarmExecutor 的 5 個並行 task 出現 `SQLITE_BUSY` 超時

---

## 後果（Consequences）

**若選擇選項 A（ReAct per Task）：**
- 正面：task 層級自主性提升，失敗場景可自動重試
- 負面：仍非真正 Multi-Agent，架構天花板不變

**若選擇選項 B（PostgreSQL + Multi-Agent）：**
- 正面：架構天花板打開，可擴展至真正的自主 Agent 系統
- 負面：100+ SQL 改寫；新增 PostgreSQL 依賴；維運複雜度上升
- 技術債：SQLite 相關的測試 fixture 全部需要重寫

**若維持現狀：**
- 正面：零風險，零工作量
- 負面：SwarmExecutor 命名為 "AgentSwarm" 但實質是 task parallelism，可能造成認知混淆

**後續追蹤：**
- [ ] 監控 SwarmExecutor 在實際運行中的 `SQLITE_BUSY` 頻率
- [ ] 評估 OAuth inference 配額是否足以支撐 ReAct per Task 的 Haiku 呼叫量
- [ ] 收集使用者對攻擊自主性的回饋需求

---

## 成功指標（Success Metrics）

> 因為本 ADR 為 Proposed 狀態，以下為各選項的驗證指標：

| 指標 | 選項 A 目標 | 選項 B 目標 | 驗證方式 |
|------|------------|------------|----------|
| Task 成功率提升 | > 20% improvement | > 40% improvement | 比較 ReAct 前後的 swarm_tasks 成功率 |
| OODA cycle 延遲 | < 5s 額外延遲 | < 10s 額外延遲（含 Agent 協調） | APM 監控 |
| LLM 呼叫成本 | < 2× 現有 | < 5× 現有 | API usage dashboard |
| 並發寫入錯誤率 | N/A | 0 deadlock / 0 SQLITE_BUSY | Error log 監控 |

> **重新評估觸發條件：** SwarmExecutor 連續 3 次出現 SQLITE_BUSY 超時，或使用者明確要求多目標並行深度探索。

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：
  - ADR-027：OODA 並行探索 Agent 架構（Accepted）— 定義了現有 SwarmExecutor 設計
  - ADR-028：攻擊路徑圖引擎（Accepted）— AttackGraphEngine 設計
  - SPEC-030：AgentSwarm OODA 並行任務排程 — SwarmExecutor 實作規格
  - SPEC-031：AttackGraph 攻擊路徑圖引擎 — 攻擊圖實作規格

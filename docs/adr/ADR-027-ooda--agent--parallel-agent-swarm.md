# [ADR-027]: OODA 並行探索 Agent 架構 (Parallel Agent Swarm)

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

### 問題陳述

Athena 的 OODA loop 核心控制器 (`OODAController.trigger_cycle()`) 在 Act 階段採用**嚴格的序列執行模型**：每個 OODA cycle 只呼叫一次 `EngineRouter.execute()`，意即每 30 秒（`OODA_LOOP_INTERVAL_SEC`）的 cycle interval 中，僅能對**單一目標執行單一技術**。這在以下作戰場景中造成嚴重瓶頸：

1. **多目標並行測試**：當 operation 中有 N 個 target 需要同時進行偵查或滲透時，目前必須等待 N 個 OODA cycle 依序完成，每個 cycle 30 秒，N 個目標需要 N × 30s 才能完成首輪測試。
2. **同目標多技術探索**：Orient 階段（`OrientEngine`）可能推薦多個候選技術（`options` 陣列），但 Decide 階段（`DecisionEngine`）只能選出一個 `recommended_technique_id` 來執行。其餘候選技術必須等待後續 cycle。
3. **子網段並行偵查**：Recon 階段對不同 subnet 的 nmap scan 是天然可並行的，但目前 `FactCollector` 的收集邏輯也是序列化的。
4. **整體 cycle 延遲累積**：30 秒 interval + 序列執行 = 在多目標環境中，完成一輪全面偵查可能需要數十分鐘甚至數小時。

### 現有架構分析

目前相關元件的執行流程：

```
APScheduler (30s interval)
  └─ OODAController.trigger_cycle()
       ├─ [1] Observe: FactCollector.collect()          ← 序列
       ├─ [2] Orient:  OrientEngine.analyze()           ← 序列，LLM 呼叫
       ├─ [3] Decide:  DecisionEngine.evaluate()        ← 序列，單一技術決策
       ├─ [4] Act:     EngineRouter.execute()            ← 序列，單一執行
       └─ [5] C5ISR:   C5ISRMapper.update()             ← 序列
```

關鍵瓶頸在 Act 階段（第 4 步）。`OODAController` 第 142-151 行顯示，Act 階段僅在 `decision.get("auto_approved")` 為 True 時呼叫一次 `self._router.execute()`，參數綁定到單一 `technique_id` 與 `target_id`。

然而，Athena backend 已經具備以下 async 基礎設施：

- **asyncio + aiosqlite**：全非同步 I/O，天然支援 task 並行
- **MCPClientManager**：已實現 circuit breaker、parallel server connections、health check background task
- **EngineRouter**：支援 MCP / SSH / C2 / Metasploit 四種執行引擎，各自獨立
- **APScheduler**：AsyncIOScheduler 支援 concurrent job execution

### 業界參考：XBOW 多 Agent 架構

XBOW 在自動化漏洞發現領域採用的 multi-agent 架構提供了重要啟發：

| 角色 | XBOW 實現 | Athena 對應 |
|------|-----------|-------------|
| **Coordinator** | 持久化編排引擎，維護全域環境感知 | `OODAController` + `OrientEngine` |
| **Sandbox Agents** | 數千個短生命週期、獨立運作的 worker，每個 agent 探索特定目標，完成任務後即銷毀（防止累積偏差或 context 退化） | 本 ADR 提議的 parallel task swarm |
| **Validators** | 確定性驗證系統，確認可利用性 | `FactCollector` + C5ISR 驗證 |

XBOW 的核心設計哲學：

- **短生命週期**（Short-lived）：每個 worker 完成任務後立即銷毀，避免 context pollution
- **獨立失敗**（Independent failure）：單一 worker 的失敗不影響整體作戰
- **結果聚合**（Result aggregation）：Coordinator 收集所有 worker 結果後才進入下一個決策循環

這些原則可以直接映射到 Python asyncio 的 `TaskGroup` 模型。

---

## 評估選項（Options Considered）

### 選項 A：asyncio TaskGroup 並行分派

在 `OODAController.trigger_cycle()` 的 Act 階段使用 Python 3.11+ `asyncio.TaskGroup` 將多個技術執行任務並行分派為 async task，在同一 process 內並發執行。

**設計概要**：

```python
async with asyncio.TaskGroup() as tg:
    for task_spec in parallel_tasks[:MAX_PARALLEL_TASKS]:
        tg.create_task(
            self._router.execute(db, **task_spec),
            name=f"act-{task_spec['technique_id']}-{task_spec['target_id'][:8]}"
        )
```

- **優點**：
  - **最小改動量**：僅需修改 `OODAController` 的 Act 階段邏輯，不增加新的 infrastructure 依賴
  - **Python 原生**：利用 Python 3.11+ 內建的 `TaskGroup`，語義清晰，error handling 由 `ExceptionGroup` 標準化處理
  - **與現有架構一致**：Athena backend 已經是 async-first（aiosqlite, asyncssh, httpx），TaskGroup 自然融入
  - **零部署複雜度**：不需要額外的 message broker 或 worker process
  - **可漸進採用**：可以先在 Act 階段引入，後續逐步擴展到 Observe 階段
  - **Debug 友善**：所有 task 在同一 process，共享 logging context，stack trace 完整
- **缺點**：
  - **單進程瓶頸**：受限於 GIL（雖然 async I/O 不受 GIL 影響，但 LLM response parsing 等 CPU-bound 工作仍受限）
  - **Memory-bound**：所有 task 共享同一 process 記憶體空間，大量併發可能導致 OOM
  - **無法跨主機水平擴展**：Athena 在單節點部署模式下足夠，但未來如果需要分散式多節點執行則需重構
- **風險**：
  - **Task isolation**：單一 task 的未捕獲例外可能中斷整個 TaskGroup。需要精確的 `ExceptionGroup` handling，確保 partial failure 不影響已完成的 task 結果
  - **DB 並發寫入**：aiosqlite 預設 serialized writes，多個 task 並發寫入可能造成 lock contention。需評估是否需要 WAL mode 或 write batching
  - **WebSocket 廣播順序**：多個 execution.update 事件同時廣播，前端需能處理亂序到達

### 選項 B：Celery 任務佇列

引入 Celery + Redis（或 RabbitMQ）作為分散式任務佇列，將每個技術執行包裝為 Celery task 分發到 worker pool。

**設計概要**：

```python
from celery import group
task_group = group(
    execute_technique.s(technique_id=t, target_id=tgt, engine=eng)
    for t, tgt, eng in parallel_tasks
)
result = task_group.apply_async()
```

- **優點**：
  - **真正分散式**：worker 可分佈在多個 node，突破單進程限制
  - **成熟的 ecosystem**：retry、rate limiting、priority queue、monitoring（Flower）
  - **水平擴展**：增加 worker node 即可線性提升吞吐量
  - **故障隔離**：worker crash 不影響主 process，Celery 自動 restart
- **缺點**：
  - **重大架構變更**：需要引入 Redis/RabbitMQ 依賴，增加 Docker Compose 複雜度
  - **部署複雜度大增**：從目前的 2-container（backend + frontend）變為 4+ container
  - **Serialization overhead**：aiosqlite Connection 無法 serialize 傳遞給 worker，需要重新設計 DB 存取層
  - **開發體驗降低**：本地開發需要啟動 Redis + Celery worker
  - **與 async 架構衝突**：Celery 是 sync-first，需要 `asgiref.sync_to_async` 橋接或使用 Celery 的實驗性 async 支援
- **風險**：
  - **Overkill for current scale**：目前單一 Athena instance 的並發需求在 5-20 concurrent tasks 等級，Celery 的 overhead 遠超收益
  - **Operational burden**：Redis/RabbitMQ 需要額外的 monitoring、backup、failover 策略
  - **Debugging 複雜度**：跨 process 的 distributed tracing 比 in-process 困難許多

### 選項 C：MCP 並行呼叫（擴展現有 MCPClientManager）

利用現有的 `MCPClientManager` 並行連線池，將多個技術執行同時分派到不同 MCP tool server。

**設計概要**：

```python
tasks = [
    mcp_manager.call_tool(server, tool, args)
    for server, tool, args in parallel_mcp_tasks
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

- **優點**：
  - **利用現有架構**：`MCPClientManager` 已實現 circuit breaker、health check、auto-reconnect
  - **天然隔離**：每個 MCP server 是獨立 process/container，故障完全隔離
  - **已驗證的穩定性**：production 環境已經在使用 MCP parallel connections
- **缺點**：
  - **僅適用於 MCP 執行引擎**：SSH direct execution、C2 engine、Metasploit RPC 等非 MCP 路徑無法受益
  - **受限於 MCP server 數量**：並行度取決於可用的 MCP server instance 數量
  - **不解決 Decide 階段瓶頸**：仍然只有一個決策輸出，只是執行層可以並行
- **風險**：
  - **架構偏斜**：僅優化 MCP 路徑會導致不同執行引擎之間的效能差異越來越大
  - **未來遷移成本**：如果後續需要統一並行模型，MCP-only 的方案需要重構

---

## 決策（Decision）

我們選擇**選項 A — asyncio TaskGroup 並行分派**，輔以選項 C 的 MCP 並行能力作為 MCP 路徑的自然延伸。

### 核心理由

1. **最小 blast radius**：僅修改 `OODAController` 和 `DecisionEngine` 兩個元件，不引入新依賴
2. **與 async-first 架構一致**：Athena backend 已全面使用 asyncio，TaskGroup 是最自然的並行原語
3. **漸進式採用**：Phase 1 先在 Act 階段引入並行，Phase 2 再擴展到 Observe 階段的並行偵查
4. **XBOW 原則映射**：asyncio Task 天然就是「短生命週期 worker」— 建立、執行、收集結果、銷毀

### 設計原則（借鑑 XBOW）

| 原則 | 實現方式 |
|------|----------|
| **Short-lived tasks** | 每個 parallel task 設定 `asyncio.timeout()`，逾時即取消銷毀。Task 完成後不保留任何 state |
| **Error isolation** | `ExceptionGroup` handling 確保單一 task 失敗不影響其他 task。失敗的 task 結果標記為 `status: "failed"` 並記錄至 `technique_executions` |
| **Result aggregation** | `OODAController` 收集所有 parallel task 結果後，才進入 C5ISR update 和下一輪 Observe |
| **Configurable concurrency** | 新增 `MAX_PARALLEL_TASKS` 設定（預設值：5），透過 `asyncio.Semaphore` 控制並發上限 |
| **Coordinator awareness** | `OODAController` 維持 Coordinator 角色，所有 parallel task 的分配由 Decide 階段統一決策 |

### 架構變更概要

#### 1. `DecisionEngine.evaluate()` — 多決策輸出

目前 `DecisionEngine.evaluate()` 回傳單一決策（一個 `technique_id` + `target_id`）。修改後支援回傳**決策陣列**：

```python
# 現行：單一決策
{"technique_id": "T1059.001", "target_id": "...", "auto_approved": True}

# 新增：多決策輸出（backward-compatible）
{
    "technique_id": "T1059.001",       # 主決策（backward compat）
    "target_id": "...",
    "auto_approved": True,
    "parallel_tasks": [                 # 新增欄位
        {"technique_id": "T1059.001", "target_id": "target-A", "engine": "mcp_ssh"},
        {"technique_id": "T1046",     "target_id": "target-B", "engine": "mcp_ssh"},
        {"technique_id": "T1018",     "target_id": "target-C", "engine": "mcp"},
    ]
}
```

**Backward compatibility**：若 `parallel_tasks` 欄位不存在，Act 階段回退到原有的單一執行路徑。

#### 2. `OODAController.trigger_cycle()` — Act 階段並行分派

```python
# ── 4. ACT (Parallel) ──
await self._update_phase(db, operation_id, ooda_id, OODAPhase.ACT)

parallel_tasks = decision.get("parallel_tasks", [])
if not parallel_tasks and decision.get("auto_approved"):
    # Backward-compatible: 單一執行
    parallel_tasks = [{
        "technique_id": decision["technique_id"],
        "target_id": decision["target_id"],
        "engine": decision.get("engine", "ssh"),
    }]

semaphore = asyncio.Semaphore(settings.MAX_PARALLEL_TASKS)
execution_results = []

async def _guarded_execute(task_spec: dict) -> dict:
    """單一 task wrapper — 隔離例外、限制並發。"""
    async with semaphore:
        try:
            async with asyncio.timeout(settings.PARALLEL_TASK_TIMEOUT_SEC):
                return await self._router.execute(
                    db,
                    technique_id=task_spec["technique_id"],
                    target_id=task_spec["target_id"],
                    engine=task_spec.get("engine", "ssh"),
                    operation_id=operation_id,
                    ooda_iteration_id=ooda_id,
                )
        except TimeoutError:
            return {
                "technique_id": task_spec["technique_id"],
                "target_id": task_spec["target_id"],
                "status": "failed",
                "error": "Task timeout exceeded",
            }
        except Exception as exc:
            return {
                "technique_id": task_spec["technique_id"],
                "target_id": task_spec["target_id"],
                "status": "failed",
                "error": str(exc),
            }

try:
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(
                _guarded_execute(spec),
                name=f"act-{spec['technique_id']}-{spec['target_id'][:8]}"
            )
            for spec in parallel_tasks
        ]
    execution_results = [t.result() for t in tasks]
except ExceptionGroup as eg:
    # 收集已完成的結果 + 記錄失敗
    for t in tasks:
        if t.done() and not t.cancelled():
            try:
                execution_results.append(t.result())
            except Exception:
                pass
    logger.warning("OODA[%s] Act phase partial failure: %s", ooda_id[:8], eg)
```

#### 3. 新增 Settings 欄位

```python
# config.py 新增
MAX_PARALLEL_TASKS: int = 5           # 同時並行的最大 task 數量
PARALLEL_TASK_TIMEOUT_SEC: int = 120  # 單一 parallel task 的 timeout
```

#### 4. DB 並發寫入策略

aiosqlite 底層使用單一 writer thread，多個 concurrent task 寫入 `technique_executions` 時可能產生 lock contention。策略：

- 啟用 **WAL（Write-Ahead Logging）mode**：允許並發讀取 + 序列化寫入，降低 lock 等待時間
- 每個 task 的 DB 寫入（INSERT execution record、UPDATE status）使用獨立 transaction
- Critical section（如 `operations` 表的 counter 更新）使用 `BEGIN IMMEDIATE` 確保原子性

#### 5. WebSocket 廣播增強

新增 `execution.batch_update` 事件類型，允許前端一次性接收多個 execution 狀態更新：

```python
await self._ws.broadcast(operation_id, "execution.batch_update", {
    "results": [
        {"id": r["execution_id"], "technique_id": r["technique_id"],
         "status": r["status"], "engine": r["engine"]}
        for r in execution_results
    ]
})
```

### 不在本 ADR 範圍內（明確排除）

- **Observe 階段並行化**：屬於 Phase 2，待 Act 並行化驗證穩定後再實施
- **分散式 worker 架構**（Celery 等）：目前 scale 不需要，未來如需支援多節點部署再另開 ADR
- **LLM 並行呼叫**：Orient 階段的 PentestGPT 呼叫目前是序列的，但因 LLM API rate limit 限制，並行化收益有限
- **前端 UI 變更**：War Room dashboard 需要支援多 execution 進度顯示，但屬於前端 spec 範疇

---

## 後果（Consequences）

**正面影響：**

- **Act 階段吞吐量提升**：多目標場景下，5 個 target 的首輪執行時間從 5 × 30s = 150s 降至 ~30s（單一 cycle 內並行完成）
- **OODA 循環效率倍增**：每個 cycle 可以產出更多 facts，加速 Orient 階段的態勢感知收斂
- **作戰節奏（tempo）提升**：更接近 XBOW 的「swarm exploration」模式，快速覆蓋攻擊面
- **Backward-compatible**：`parallel_tasks` 為可選欄位，不提供時回退到原有的單一執行邏輯，現有 integration test 無需修改
- **為 Phase 2 鋪路**：TaskGroup 模式可以自然擴展到 Observe 階段的並行偵查

**負面影響 / 技術債：**

- **DB 寫入複雜度增加**：WAL mode + 並發 transaction 需要額外的測試覆蓋，特別是 edge case（concurrent counter update、deadlock detection）
- **Error handling 複雜度**：`ExceptionGroup` 處理邏輯比單一 try/except 更複雜，需要確保所有 partial failure 場景都有覆蓋
- **Logging 可讀性**：多個 task 的 log 交錯輸出，可能降低 debug 體驗。需要在 log message 中加入 task identifier（`act-{technique}-{target}`）
- **測試複雜度**：需要撰寫 concurrent execution 的測試，包含 race condition、timeout、partial failure 等場景
- **`ooda_iterations` 表結構**：目前 `technique_execution_id` 是單一欄位，並行執行後需要改為一對多關聯（新增 `ooda_iteration_executions` junction table 或改用 JSON 陣列）

**後續追蹤：**

- [ ] Phase 1：修改 `DecisionEngine` 支援 `parallel_tasks` 輸出
- [ ] Phase 1：修改 `OODAController` Act 階段使用 `TaskGroup` 並行分派
- [ ] Phase 1：新增 `MAX_PARALLEL_TASKS` 和 `PARALLEL_TASK_TIMEOUT_SEC` 設定
- [ ] Phase 1：啟用 SQLite WAL mode，驗證並發寫入穩定性
- [ ] Phase 1：新增 `ooda_iteration_executions` junction table（或 JSON 欄位）
- [ ] Phase 1：撰寫 parallel execution 的 unit test 和 integration test
- [ ] Phase 1：新增 `execution.batch_update` WebSocket 事件
- [ ] Phase 2（未來）：Observe 階段並行偵查（parallel nmap、parallel OSINT）
- [ ] Phase 2（未來）：前端 War Room 多 execution 進度顯示

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Act 階段耗時（多目標場景） | 較序列執行減少 ≥ 60%（5 targets: 150s → ≤ 60s） | Benchmark：5 target operation，比較 parallel vs. sequential 的 Act phase wall time | 實作完成時 |
| 錯誤隔離率 | 單一 task 失敗時，其餘 task 成功率 100% | 故障注入測試：mock 其中 1 個 EngineRouter.execute() raise exception，驗證其餘 task 正常完成 | 實作完成時 |
| Backward compatibility | 無 `parallel_tasks` 時行為不變 | 現有 integration test 全數通過，無修改 | 實作完成時 |
| 測試通過率 | 100%（含新增 parallel test） | `make test` | 實作完成時 |
| DB 並發寫入穩定性 | 0 deadlock / 0 data corruption | 壓力測試：20 concurrent task 寫入 technique_executions，驗證資料一致性 | 實作完成時 |
| 單一 task timeout | 100% 遵守 `PARALLEL_TASK_TIMEOUT_SEC` | Timeout 測試：mock slow execution，驗證 task 在 timeout 內被取消 | 實作完成時 |
| OODA cycle 覆蓋率 | 每 cycle 可執行 ≥ 3 個不同 technique（多目標場景） | 監控 `ooda_iterations` 表的 parallel execution count | 部署後 1 週 |

> **重新評估條件**：若單進程 memory 使用超過 2GB（MAX_PARALLEL_TASKS=5 時）或 SQLite WAL mode 在高並發下出現 persistent lock contention（> 500ms wait），應重新評估是否需要遷移至選項 B（Celery）或引入 PostgreSQL。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 參考：
  - **ADR-004**（`semi-auto-with-manual-override`）：`DecisionEngine` 的 risk threshold 規則仍然適用於每個 parallel task，不因並行而繞過審批機制
  - **ADR-024**（`mcp-architecture-and-tool-server-integration`）：MCP 路徑的 parallel task 可以直接利用 `MCPClientManager` 現有的 circuit breaker 和 connection pool
  - **XBOW Agent Architecture**：Coordinator / Sandbox Agent / Validator 三層架構的設計哲學
  - **Python asyncio.TaskGroup 文件**：https://docs.python.org/3/library/asyncio-task.html#task-groups
  - **SQLite WAL mode 文件**：https://www.sqlite.org/wal.html
  - **Python ExceptionGroup PEP 654**：https://peps.python.org/pep-0654/

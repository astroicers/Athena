# SPEC-030：AgentSwarm OODA 並行任務排程

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-030 |
| **狀態** | Accepted |
| **版本** | 1.0.0 |
| **作者** | Athena Contributors |
| **建立日期** | 2026-03-06 |
| **關聯 ADR** | ADR-027（OODA 並行探索 Agent 架構 Parallel Agent Swarm） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 將 OODA Act 階段從「單一 technique 序列執行」升級為「多 technique 有界並行執行」，使 DecisionEngine 能在一次 Decide 中產出多項可平行執行的任務（parallel_tasks），由新建的 SwarmExecutor 透過 `asyncio.TaskGroup` + `asyncio.Semaphore` 在 Act 階段並行調度，並將所有結果聚合後回饋至下一次 Observe。此功能對 operation 指揮官有價值——縮短單次 OODA 迭代耗時、提升多目標環境的偵測與滲透效率。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `operation_id` | `str` (UUID) | OODAController.trigger_cycle() | 必須為現存 active/planning 狀態的 operation |
| `recommendation` | `dict` | OrientEngine.analyze() 輸出 | 包含 `options: list[TacticalOption]`，每個 option 含 `technique_id`, `risk_level`, `recommended_engine` |
| `decision.parallel_tasks` | `list[dict]` | DecisionEngine.evaluate() 新輸出 | 0~N 筆 auto_approved tasks；每筆含 `technique_id`, `target_id`, `engine`, `risk_level` |
| `MAX_PARALLEL_TASKS` | `int` | `config.Settings` | 預設 5，範圍 1~20 |
| `PARALLEL_TASK_TIMEOUT_SEC` | `int` | `config.Settings` | 預設 120，範圍 10~600 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `backend/app/services/agent_swarm.py` — SwarmExecutor

```python
"""AgentSwarm — bounded-concurrency parallel task executor for OODA Act phase."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.services.engine_router import EngineRouter
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


@dataclass
class SwarmTask:
    """Single unit of parallel execution within the Act phase."""
    task_id: str
    technique_id: str
    target_id: str
    engine: str
    status: str = "pending"          # pending | running | completed | failed | timeout
    result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class SwarmResult:
    """Aggregated result of all parallel tasks in one Act phase."""
    ooda_iteration_id: str
    total: int
    completed: int = 0
    failed: int = 0
    timed_out: int = 0
    tasks: list[SwarmTask] = field(default_factory=list)

    @property
    def all_failed(self) -> bool:
        return self.total > 0 and self.completed == 0

    @property
    def partial_success(self) -> bool:
        return 0 < self.completed < self.total

    @property
    def act_summary(self) -> str:
        return (
            f"Swarm: {self.completed}/{self.total} succeeded, "
            f"{self.failed} failed, {self.timed_out} timed out"
        )


class SwarmExecutor:
    """
    Bounded-concurrency parallel executor for the OODA Act phase.

    Design principles (ADR-027, inspired by XBOW):
    1. Short-lived tasks: each task has individual timeout, destroyed after completion
    2. Error isolation: ExceptionGroup handling prevents cascade failures
    3. Result aggregation: collect all results before returning to OODAController
    4. Configurable concurrency: Semaphore-bounded (MAX_PARALLEL_TASKS)
    5. Coordinator awareness: OODAController remains the single coordinator
    """

    def __init__(
        self,
        engine_router: EngineRouter,
        ws_manager: WebSocketManager,
    ):
        self._router = engine_router
        self._ws = ws_manager
        self._semaphore = asyncio.Semaphore(settings.MAX_PARALLEL_TASKS)

    async def execute_swarm(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        ooda_iteration_id: str,
        parallel_tasks: list[dict],
    ) -> SwarmResult:
        """
        Execute multiple tasks in parallel with bounded concurrency.

        Steps:
        1. Create SwarmTask records in DB (status=pending)
        2. Broadcast execution.batch_update with initial state
        3. Launch tasks via asyncio.TaskGroup + Semaphore
        4. Handle ExceptionGroup — individual failures do NOT cancel siblings
        5. Aggregate results into SwarmResult
        6. Broadcast final execution.batch_update
        7. Return SwarmResult to OODAController for act_summary

        Each individual task:
        a. Acquire semaphore slot
        b. Set status=running, broadcast progress
        c. Call EngineRouter.execute() with asyncio.timeout()
        d. On success: status=completed, store result
        e. On timeout: status=timeout, record error
        f. On exception: status=failed, record error
        g. Release semaphore slot (guaranteed via try/finally)
        """
        swarm_result = SwarmResult(
            ooda_iteration_id=ooda_iteration_id,
            total=len(parallel_tasks),
        )

        if not parallel_tasks:
            return swarm_result

        swarm_tasks: list[SwarmTask] = []
        for task_spec in parallel_tasks:
            st = SwarmTask(
                task_id=str(uuid.uuid4()),
                technique_id=task_spec["technique_id"],
                target_id=task_spec["target_id"],
                engine=task_spec.get("engine", "ssh"),
            )
            swarm_tasks.append(st)

        # Insert swarm_tasks records into DB
        now = datetime.now(timezone.utc).isoformat()
        for st in swarm_tasks:
            await db.execute(
                "INSERT INTO swarm_tasks "
                "(id, ooda_iteration_id, operation_id, technique_id, target_id, "
                "engine, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                (st.task_id, ooda_iteration_id, operation_id,
                 st.technique_id, st.target_id, st.engine, now),
            )
        await db.commit()

        # Broadcast initial batch state
        await self._broadcast_batch(operation_id, swarm_tasks)

        # Execute with TaskGroup — each task is independently wrapped
        completed_tasks: list[SwarmTask] = []
        try:
            async with asyncio.TaskGroup() as tg:
                for st in swarm_tasks:
                    tg.create_task(
                        self._execute_single(
                            db, operation_id, ooda_iteration_id, st
                        )
                    )
        except* asyncio.TimeoutError:
            # Handled per-task; this catches any leaked timeouts
            logger.warning("SwarmExecutor: TaskGroup caught leaked TimeoutError")
        except* Exception as eg:
            # Log all exceptions from the group but do not re-raise
            for exc in eg.exceptions:
                logger.error(
                    "SwarmExecutor: unhandled task exception: %s", exc,
                    exc_info=exc,
                )

        # Aggregate results
        for st in swarm_tasks:
            swarm_result.tasks.append(st)
            if st.status == "completed":
                swarm_result.completed += 1
            elif st.status == "timeout":
                swarm_result.timed_out += 1
            elif st.status == "failed":
                swarm_result.failed += 1

        # Update all swarm_task records with final status
        for st in swarm_tasks:
            await db.execute(
                "UPDATE swarm_tasks SET status = ?, error = ?, "
                "started_at = ?, completed_at = ? WHERE id = ?",
                (st.status, st.error,
                 st.started_at.isoformat() if st.started_at else None,
                 st.completed_at.isoformat() if st.completed_at else None,
                 st.task_id),
            )
        await db.commit()

        # Broadcast final batch state
        await self._broadcast_batch(operation_id, swarm_tasks)

        return swarm_result

    async def _execute_single(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        ooda_iteration_id: str,
        task: SwarmTask,
    ) -> None:
        """Execute a single task with semaphore guard and per-task timeout."""
        async with self._semaphore:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            await db.execute(
                "UPDATE swarm_tasks SET status = 'running', started_at = ? WHERE id = ?",
                (task.started_at.isoformat(), task.task_id),
            )
            await db.commit()

            try:
                async with asyncio.timeout(settings.PARALLEL_TASK_TIMEOUT_SEC):
                    result = await self._router.execute(
                        db,
                        technique_id=task.technique_id,
                        target_id=task.target_id,
                        engine=task.engine,
                        operation_id=operation_id,
                        ooda_iteration_id=ooda_iteration_id,
                    )
                task.result = result
                task.status = (
                    "completed" if result.get("status") == "success" else "failed"
                )
                if result.get("error"):
                    task.error = result["error"]
            except TimeoutError:
                task.status = "timeout"
                task.error = (
                    f"Task timed out after {settings.PARALLEL_TASK_TIMEOUT_SEC}s"
                )
                logger.warning(
                    "SwarmTask %s timed out: %s on %s",
                    task.task_id, task.technique_id, task.target_id,
                )
            except Exception as exc:
                task.status = "failed"
                task.error = f"{type(exc).__name__}: {exc}"
                logger.error(
                    "SwarmTask %s failed: %s", task.task_id, exc, exc_info=True,
                )
            finally:
                task.completed_at = datetime.now(timezone.utc)

    async def _broadcast_batch(
        self, operation_id: str, tasks: list[SwarmTask]
    ) -> None:
        """Broadcast execution.batch_update WebSocket event."""
        try:
            await self._ws.broadcast(
                operation_id,
                "execution.batch_update",
                {
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "technique_id": t.technique_id,
                            "target_id": t.target_id,
                            "engine": t.engine,
                            "status": t.status,
                            "error": t.error,
                        }
                        for t in tasks
                    ]
                },
            )
        except Exception:
            pass  # fire-and-forget per SPEC-007
```

### 2. `backend/app/config.py` — 新增 Settings 欄位

```python
# AgentSwarm (ADR-027)
MAX_PARALLEL_TASKS: int = 5           # Semaphore bound, range 1-20
PARALLEL_TASK_TIMEOUT_SEC: int = 120  # Per-task timeout, range 10-600
```

### 3. `backend/app/models/api_schemas.py` — SwarmTask / SwarmBatchResponse

```python
# ---------------------------------------------------------------------------
# AgentSwarm (SPEC-030)
# ---------------------------------------------------------------------------

class SwarmTaskSchema(BaseModel):
    task_id: str
    technique_id: str
    target_id: str
    engine: str
    status: str          # pending | running | completed | failed | timeout
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class SwarmBatchResponse(BaseModel):
    ooda_iteration_id: str
    total: int
    completed: int
    failed: int
    timed_out: int
    tasks: list[SwarmTaskSchema]
```

### 4. `backend/app/services/decision_engine.py` — parallel_tasks 輸出

`DecisionEngine.evaluate()` 新增邏輯：當 `recommendation.options` 包含多個 auto_approved 的 technique 且各自對應不同 target 時，產出 `parallel_tasks` list。

```python
async def evaluate(
    self, db: aiosqlite.Connection, operation_id: str, recommendation: dict
) -> dict:
    # ... existing single-decision logic remains unchanged ...
    # 現有 single decision 邏輯不變，作為 parallel_tasks[0] 或空 list 的 fallback

    # NEW: build parallel_tasks from all auto-approvable options
    parallel_tasks = []
    for opt in options:
        opt_risk = RiskLevel(opt.get("risk_level", "medium"))
        opt_level = _RISK_ORDER.get(opt_risk, 1)

        # Apply same auto-approval rules as single decision
        if automation_mode == AutomationMode.MANUAL:
            continue
        if opt_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            continue
        if opt_level > threshold_level:
            continue

        # Determine target for this option
        opt_target = opt.get("target_id") or target_id
        if not opt_target:
            continue

        parallel_tasks.append({
            "technique_id": opt.get("technique_id"),
            "target_id": opt_target,
            "engine": opt.get("recommended_engine", "ssh"),
            "risk_level": opt_risk.value,
        })

    # Deduplicate: same (technique_id, target_id) pair
    seen = set()
    deduped = []
    for pt in parallel_tasks:
        key = (pt["technique_id"], pt["target_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(pt)

    return {
        **base,
        "auto_approved": ...,          # existing field
        "needs_confirmation": ...,     # existing field
        "reason": ...,                 # existing field
        "parallel_tasks": deduped,     # NEW: list of auto-approved tasks
    }
```

### 5. `backend/app/services/ooda_controller.py` — Act 階段改造

```python
# ── 4. ACT ──
await self._update_phase(db, operation_id, ooda_id, OODAPhase.ACT)
execution_result = None
act_summary = ""

parallel_tasks = decision.get("parallel_tasks", [])

if parallel_tasks and len(parallel_tasks) > 1:
    # ── SWARM PATH: multiple parallel tasks ──
    logger.info(
        "OODA[%s] Act phase — swarm executing %d parallel tasks",
        ooda_id[:8], len(parallel_tasks),
    )
    swarm_result = await self._swarm.execute_swarm(
        db, operation_id, ooda_id, parallel_tasks,
    )
    act_summary = swarm_result.act_summary

    # Post-Act: update targets, agents, counters for each successful task
    for st in swarm_result.tasks:
        if st.status == "completed" and st.result:
            execution_result = st.result  # keep last for MCP enrichment
            if st.result.get("status") == "success":
                await self._handle_successful_execution(
                    db, operation_id, ooda_id, next_num, st, decision,
                )

    if swarm_result.all_failed:
        await self._write_log(db, operation_id, "error",
            f"OODA #{next_num} Act: all {swarm_result.total} swarm tasks failed")
    elif swarm_result.partial_success:
        await self._write_log(db, operation_id, "warning",
            f"OODA #{next_num} Act: {swarm_result.act_summary}")
    else:
        await self._write_log(db, operation_id, "success",
            f"OODA #{next_num} Act: {swarm_result.act_summary}")

elif decision.get("auto_approved") and decision.get("technique_id") and decision.get("target_id"):
    # ── SINGLE PATH: existing behavior (unchanged) ──
    # ... existing single-execution code ...

else:
    # ── MANUAL APPROVAL PATH: existing behavior (unchanged) ──
    # ... existing manual-approval code ...
```

### 6. `backend/app/database.py` — 新增 swarm_tasks table

```sql
CREATE TABLE IF NOT EXISTS swarm_tasks (
    id TEXT PRIMARY KEY,
    ooda_iteration_id TEXT REFERENCES ooda_iterations(id) ON DELETE CASCADE,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    technique_id TEXT NOT NULL,
    target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
    engine TEXT DEFAULT 'ssh',
    status TEXT DEFAULT 'pending',
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 7. `backend/tests/test_agent_swarm.py` — 測試套件

```python
"""Tests for AgentSwarm parallel task executor (SPEC-030)."""

import asyncio
import pytest
import aiosqlite

from app.services.agent_swarm import SwarmExecutor, SwarmTask, SwarmResult


class TestSwarmExecutor:
    """Unit tests for SwarmExecutor."""

    async def test_empty_parallel_tasks_returns_zero_result(self, ...):
        """parallel_tasks=[] → SwarmResult with total=0."""

    async def test_single_task_executes_normally(self, ...):
        """Single task behaves identically to legacy single execution path."""

    async def test_multiple_tasks_execute_in_parallel(self, ...):
        """3 tasks start concurrently (verified by timing < serial sum)."""

    async def test_semaphore_bounds_concurrency(self, ...):
        """MAX_PARALLEL_TASKS=2 with 5 tasks → max 2 concurrent at any time."""

    async def test_task_timeout_does_not_cancel_siblings(self, ...):
        """One task times out; other tasks complete successfully."""

    async def test_task_exception_does_not_cancel_siblings(self, ...):
        """One task raises RuntimeError; other tasks complete successfully."""

    async def test_all_tasks_fail_sets_all_failed(self, ...):
        """When every task fails → SwarmResult.all_failed == True."""

    async def test_partial_success_detected(self, ...):
        """2/3 succeed → SwarmResult.partial_success == True."""

    async def test_task_timeout_status_recorded(self, ...):
        """Timed-out task has status='timeout' and error message."""

    async def test_swarm_tasks_persisted_to_db(self, ...):
        """All SwarmTask records are INSERT-ed and UPDATE-d in swarm_tasks table."""

    async def test_batch_update_websocket_events(self, ...):
        """execution.batch_update broadcast at start and end of swarm."""

    async def test_db_concurrent_writes_wal_mode(self, ...):
        """Multiple parallel DB writes do not raise OperationalError (WAL mode)."""

    async def test_swarm_result_act_summary_format(self, ...):
        """act_summary follows 'Swarm: N/M succeeded, F failed, T timed out' format."""


class TestDecisionEngineParallelTasks:
    """Tests for DecisionEngine.evaluate() parallel_tasks output."""

    async def test_multiple_low_risk_options_produce_parallel_tasks(self, ...):
        """3 LOW risk options → parallel_tasks contains 3 entries."""

    async def test_high_risk_options_excluded_from_parallel_tasks(self, ...):
        """HIGH/CRITICAL options never appear in parallel_tasks."""

    async def test_manual_mode_produces_empty_parallel_tasks(self, ...):
        """automation_mode=manual → parallel_tasks=[]."""

    async def test_duplicate_technique_target_deduped(self, ...):
        """Same (technique_id, target_id) pair appears only once."""

    async def test_above_threshold_options_excluded(self, ...):
        """MEDIUM risk with LOW threshold → excluded from parallel_tasks."""


class TestOODAControllerSwarmIntegration:
    """Integration tests for OODAController Act phase with SwarmExecutor."""

    async def test_swarm_path_triggered_when_multiple_parallel_tasks(self, ...):
        """parallel_tasks with 2+ entries → swarm executor called."""

    async def test_single_path_fallback_when_one_or_zero_tasks(self, ...):
        """parallel_tasks with 0-1 entries → legacy single path."""

    async def test_successful_swarm_updates_operation_counters(self, ...):
        """techniques_executed incremented by number of successful swarm tasks."""

    async def test_all_failed_swarm_logs_error(self, ...):
        """All tasks failed → log severity='error'."""

    async def test_c5isr_update_runs_after_swarm_completion(self, ...):
        """C5ISR update phase runs once after all swarm tasks complete."""
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| 所有 parallel_tasks 失敗 | SwarmResult.all_failed=True；OODAController 記錄 severity=error log；C5ISR Cyber 域 health 下降；下一次 Observe 收集失敗事實 |
| 部分 task 失敗 | SwarmResult.partial_success=True；成功的 task 正常收集 facts 並更新 target；失敗的 task 記錄 error；severity=warning log |
| 單一 task timeout | 該 task status=timeout，error 記錄超時秒數；其餘 task 不受影響（ExceptionGroup 隔離） |
| Semaphore 耗盡 | 超過 MAX_PARALLEL_TASKS 的 task 排隊等待，不會失敗；整體完成時間延長但無錯誤 |
| DB 寫入競爭 | SQLite WAL mode 允許並行讀寫；每個 task 獨立 commit；若偶發 `SQLITE_BUSY`，aiosqlite 內建重試處理（busy_timeout=5000） |
| EngineRouter.execute() 拋出未預期異常 | `_execute_single` 的 except Exception 捕獲，task status=failed，不影響 TaskGroup 內其他 task |
| parallel_tasks 為空 list | SwarmExecutor 直接回傳空 SwarmResult（total=0），OODAController fallback 至 single path 或 manual approval path |
| DecisionEngine 回傳無 parallel_tasks 欄位 | `decision.get("parallel_tasks", [])` 安全取得空 list，走既有 single path |
| operation 在 Act 執行中被 pause/abort | 各 task 的 EngineRouter.execute() 在下一個 await 點自然檢查；已完成的 task 結果保留 |
| WebSocket broadcast 失敗 | fire-and-forget（per SPEC-007），不阻塞 swarm 執行 |

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| technique_executions 表一次迭代產生多筆記錄 | swarm 並行執行多個 task | Attack Path Timeline（SPEC-021） | 時間軸上同一迭代顯示多個並行執行點；`started_at` 接近但 `completed_at` 各異 |
| facts 表並行插入多筆 | 多 task 同時收集 fact | FactCollector.collect()（SPEC-007） | dedup 邏輯（trait+value set）仍生效；無重複 fact |
| techniques_executed 計數器單次增加 N | swarm 中 N 個 task 成功 | WarRoom Dashboard 顯示 | 計數器 = 成功 task 數量（非固定 +1） |
| 多個 target 同時被標記 is_compromised | 多 target task 均成功 | Topology 視圖（SPEC-026） | topology 一次刷新多個 compromised 節點 |
| 多個 agent 同時 activate | 成功 task 觸發 agent activate | C5ISR Control 域 health | `alive_agents / total_agents` 比例跳升 |
| act_summary 改為 swarm 格式字串 | swarm path 執行 | OODA Timeline（前端） | 前端純文字顯示不影響渲染；內容格式 "Swarm: N/M succeeded..." |
| 新 swarm_tasks table 建立 | 應用啟動時 CREATE TABLE | Database migration | `SELECT * FROM swarm_tasks` 可查詢 |
| execution.batch_update WS 新事件 | swarm 開始/結束時 | 前端 WebSocket handler | 前端 graceful ignore 未知事件；或新增 handler 處理 |
| decision dict 新增 parallel_tasks 欄位 | DecisionEngine.evaluate() 回傳 | 讀取 decision 的下游程式碼 | `.get("parallel_tasks", [])` 向後相容，無 KeyError |
| OODA cycle 可能超過 30s interval | swarm 執行耗時 > 30s | APScheduler 排程 | `max_instances=1` 保護不重複觸發 |

---

## ⚠️ 邊界條件（Edge Cases）

### E1：所有 parallel_tasks 失敗（All Tasks Fail）
- SwarmResult: `total=N, completed=0, failed=F, timed_out=T` 且 `all_failed=True`
- OODAController 記錄 `severity=error` log
- 不更新 `targets.is_compromised`、不 activate agents
- `act_summary` 仍寫入 `ooda_iterations`，格式為 `"Swarm: 0/N succeeded, F failed, T timed out"`
- C5ISR Cyber 域 health 在後續 update 中下降（因 `success/total` 比降低）
- 下一次 Observe 收集所有失敗的 execution 記錄，Orient 可據此調整策略

### E2：部分成功部分失敗（Partial Failure）
- 成功的 task 正常走 `_handle_successful_execution` path（更新 target、activate agent、increment counter）
- 失敗的 task 僅記錄 error 到 `swarm_tasks` 和 `technique_executions`
- Log severity=warning
- Orient 下次分析時可看到哪些 technique 成功、哪些失敗，據此調整推薦

### E3：單一 task 超時（Individual Task Timeout）
- `asyncio.timeout(PARALLEL_TASK_TIMEOUT_SEC)` 觸發 `TimeoutError`
- 該 task 的 `status="timeout"`，`error="Task timed out after 120s"`
- `_execute_single` 的 finally block 確保 `completed_at` 被設定
- Semaphore slot 在 finally 中釋放（`async with self._semaphore` 確保）
- 其餘 task 不受影響——`TaskGroup` + `except*` 隔離錯誤

### E4：Semaphore 耗盡（Concurrency Saturation）
- `MAX_PARALLEL_TASKS=5` 且 `parallel_tasks` 含 10 筆 → 前 5 筆立即執行，後 5 筆排隊
- `asyncio.Semaphore.acquire()` 是公平排隊（FIFO），不會 starvation
- 排隊中的 task 的 `PARALLEL_TASK_TIMEOUT_SEC` **包含**等待 semaphore 的時間
- 若排隊 + 執行超過 timeout → task status=timeout（設計決策：timeout 從 task 建立時算起，而非從 semaphore 獲取時算起）

### E5：DB 併發寫入競爭（SQLite Write Contention）
- SQLite WAL mode 允許多個 reader 和一個 writer 並行
- 多個 `_execute_single` 同時 `await db.commit()` 時，aiosqlite 序列化寫入
- 若偶發 `sqlite3.OperationalError: database is locked`，aiosqlite 內建 `busy_timeout`（預設 5000ms）自動重試
- 必須確認 `database.py` 的 connection 建立時設定 `PRAGMA journal_mode=WAL` 和 `PRAGMA busy_timeout=5000`
- 每個 task 各自 commit，不使用跨 task 的 transaction（避免長事務鎖）

### E6：同一 target 被多個 task 同時操作
- 可能發生的衝突：兩個 task 都嘗試 `UPDATE targets SET is_compromised = 1`
- SQLite WAL mode 下此為安全操作（idempotent UPDATE）
- `facts` 表的 dedup 邏輯在 `FactCollector.collect_from_result()` 中基於 `(trait, value)` 判斷，並行插入同一 fact 可能產生重複——需在 INSERT 前檢查或使用 `INSERT OR IGNORE`

### E7：OODA 循環在 swarm 執行中被手動推進（Commander Override）
- `advance_phase()` 可能在 swarm 執行中被呼叫
- swarm 中已啟動的 task 繼續執行直到完成/超時——不強制取消
- `ooda_iterations.phase` 被推進到下一階段，但 swarm 結果仍會寫回 DB
- 設計取捨：不實作 mid-swarm cancellation（避免複雜度），V1 scope

### E8：DecisionEngine 回傳 parallel_tasks 含重複 (technique_id, target_id)
- `evaluate()` 內建 dedup 邏輯（seen set）
- 即使繞過 dedup，SwarmExecutor 不做額外檢查——同一 technique 對同一 target 執行兩次在安全測試場景下是合法的（例如重試）
- `technique_executions` 表允許重複的 (technique_id, target_id) 組合（每筆有獨立 `id`）

### E9：parallel_tasks 中某 task 的 target 不存在
- `EngineRouter.execute()` 內部在查找 target IP 時回傳 None
- MCP/SSH 路徑會回傳 `status=failed, error="No credentials for target ..."`
- SwarmTask 記錄 `status=failed`，不影響其他 task

### E10：Swarm 執行時間超過 OODA_LOOP_INTERVAL_SEC（30s）
- APScheduler 的 OODA trigger 有 `max_instances=1`，同一 operation 不會重複觸發
- 若 swarm 耗時 120s，下一次 OODA 循環在上一次完成後才開始
- 不需額外鎖機制

### ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|---------|---------|---------|----------|
| `git revert <commit>` 回退所有程式碼變更 | `technique_executions` 和 `facts` 保留完整（由 EngineRouter 正常寫入） | `make test` 全數通過；OODAController Act 階段回到 single-execution path | 否（需手動驗證） |
| `DROP TABLE IF EXISTS swarm_tasks` | swarm_tasks 記錄遺失，但不影響歷史 OODA 迭代查詢 | DB 中無 swarm_tasks table | 否（需手動驗證） |
| 確認 `DecisionEngine.evaluate()` 回傳結構不含 `parallel_tasks` | 無 — 新欄位為 additive，下游使用 `.get("parallel_tasks", [])` | 下游 code path 走 single/manual path | 是 |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參照 |
|----|------|------|---------|---------|
| P1 | 正向 | 3 個 LOW risk task 送入 SwarmExecutor | 3 個 task 並行執行，SwarmResult.completed=3 | Scenario: 多任務並行執行成功 |
| P2 | 正向 | DecisionEngine 回傳 3 個 auto-approved LOW risk option | parallel_tasks 含 3 筆，各有 technique_id/target_id/engine | Scenario: DecisionEngine 產出 parallel_tasks |
| P3 | 正向 | OODAController Act 階段收到 parallel_tasks 長度 > 1 | 走 swarm path，act_summary 為 swarm 格式 | Scenario: 多任務並行執行成功 |
| N1 | 負向 | parallel_tasks 為空 list | SwarmExecutor 回傳空 SwarmResult（total=0），走 single path | Scenario: 空任務與降級安全處理 |
| N2 | 負向 | 所有 parallel_tasks 失敗 | SwarmResult.all_failed=True，log severity=error | Scenario: 任務失敗隔離與聚合 |
| N3 | 負向 | DecisionEngine 在 MANUAL mode | parallel_tasks=[]，不產出並行任務 | Scenario: DecisionEngine 產出 parallel_tasks |
| B1 | 邊界 | 單一 task 超時（PARALLEL_TASK_TIMEOUT_SEC 到期） | 該 task status=timeout，其餘 task 不受影響 | Scenario: 任務失敗隔離與聚合 |
| B2 | 邊界 | MAX_PARALLEL_TASKS=2 且 5 個 task | 前 2 個立即執行，後 3 個排隊等待 semaphore | Scenario: 多任務並行執行成功 |
| B3 | 邊界 | 同一 (technique_id, target_id) 重複 | DecisionEngine dedup 後僅保留 1 筆 | Scenario: DecisionEngine 產出 parallel_tasks |
| B4 | 邊界 | 並行 5 個 task 同時寫入 DB | 無 OperationalError（WAL mode + busy_timeout） | Scenario: 多任務並行執行成功 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: AgentSwarm OODA 並行任務排程
  Background:
    Given 一個 active operation 存在
    And OODAController 已初始化並注入 SwarmExecutor
    And MAX_PARALLEL_TASKS 設為 5
    And PARALLEL_TASK_TIMEOUT_SEC 設為 120

  Scenario: 多任務並行執行成功
    Given OrientEngine 回傳 3 個 LOW risk tactical options 對應不同 target
    And DecisionEngine 產出 parallel_tasks 含 3 筆 auto-approved task
    When OODAController 進入 Act 階段
    Then SwarmExecutor 以 asyncio.TaskGroup 並行執行 3 個 task
    And 所有 task 透過 EngineRouter.execute() 執行
    And SwarmResult.completed 為 3，failed 為 0
    And ooda_iterations.act_summary 為 "Swarm: 3/3 succeeded, 0 failed, 0 timed out"
    And execution.batch_update WebSocket 事件在開始和結束時各廣播一次
    And swarm_tasks 表包含 3 筆記錄且 status 均為 completed

  Scenario: 任務失敗隔離與聚合
    Given parallel_tasks 含 3 筆 task
    And 其中 1 筆的 EngineRouter.execute() 將拋出 RuntimeError
    And 其中 1 筆將超過 PARALLEL_TASK_TIMEOUT_SEC
    When SwarmExecutor.execute_swarm() 執行完成
    Then SwarmResult.completed 為 1，failed 為 1，timed_out 為 1
    And 失敗的 task 不導致其他 task 被取消（ExceptionGroup 隔離）
    And OODAController 記錄 severity=warning log
    And 成功的 task 正確更新 targets.is_compromised 和 techniques_executed

  Scenario: DecisionEngine 產出 parallel_tasks
    Given recommendation.options 含 5 個 tactical option
    And 3 個為 LOW risk，1 個為 HIGH risk，1 個為 CRITICAL risk
    And automation_mode 非 MANUAL
    When DecisionEngine.evaluate() 執行
    Then parallel_tasks 僅含 3 筆 LOW risk option
    And HIGH 和 CRITICAL risk option 不出現在 parallel_tasks 中
    And 同一 (technique_id, target_id) 不重複

  Scenario: 空任務與降級安全處理
    Given decision 回傳不含 parallel_tasks 欄位
    When OODAController 進入 Act 階段
    Then decision.get("parallel_tasks", []) 回傳空 list
    And OODAController 走既有 single-execution path
    And 行為與未加入 AgentSwarm 前完全一致
```

---

## 🔗 追溯性（Traceability）

| 追溯項目 | 檔案路徑 | 狀態 |
|---------|---------|------|
| SwarmExecutor 主類別 | `backend/app/services/agent_swarm.py` | 已實作 |
| Config 設定（MAX_PARALLEL_TASKS 等） | `backend/app/config.py` | 已實作 |
| API Schema（SwarmTaskSchema 等） | `backend/app/models/schemas/attack.py` | 已實作 |
| DecisionEngine parallel_tasks | `backend/app/services/decision_engine.py` | （待確認） |
| OODAController Act 階段整合 | `backend/app/services/ooda_controller.py` | 已實作 |
| EngineRouter 依賴 | `backend/app/services/engine_router.py` | 已實作（既有） |
| Database swarm_tasks table | `backend/app/database.py` | （待確認） |
| OODA 路由 | `backend/app/routers/ooda.py` | 已實作 |
| OODA 排程 | `backend/app/services/ooda_scheduler.py` | 已實作 |
| 單元測試 | `backend/tests/test_agent_swarm.py` | 已實作 |
| 前端 OODA 時間軸 | `frontend/src/components/ooda/OODATimeline.tsx` | 已實作 |
| 前端 WarRoom 頁面 | `frontend/src/app/warroom/page.tsx` | 已實作 |
| E2E 測試 | （待實作） | （待實作） |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

| 面向 | 指標/日誌 | 說明 |
|------|----------|------|
| **Metrics** | `swarm_tasks_total{status}` | 各 task 最終狀態計數（counter，label: completed/failed/timeout） |
| **Metrics** | `swarm_execution_duration_seconds` | 整個 swarm 執行耗時（histogram） |
| **Metrics** | `swarm_task_duration_seconds{engine}` | 單一 task 執行耗時（histogram，label: ssh/mcp/...） |
| **Metrics** | `swarm_semaphore_wait_seconds` | task 等待 semaphore 的時間（histogram） |
| **Metrics** | `swarm_concurrency_gauge` | 當前並行執行中的 task 數量（gauge） |
| **Logging** | `INFO: OODA[{id}] Act phase — swarm executing {N} parallel tasks` | swarm 啟動日誌 |
| **Logging** | `WARNING: SwarmTask {id} timed out: {technique} on {target}` | 單一 task 超時日誌 |
| **Logging** | `ERROR: SwarmTask {id} failed: {error}` | 單一 task 失敗日誌 |
| **Logging** | `INFO: Swarm: {completed}/{total} succeeded, {failed} failed, {timed_out} timed out` | swarm 完成摘要日誌 |
| **WebSocket** | `execution.batch_update` | swarm 開始/結束時推送所有 task 狀態至前端 |
| **DB** | `swarm_tasks` table | 持久化每個 task 的狀態、啟動/完成時間、錯誤訊息 |
| **Health** | `MAX_PARALLEL_TASKS` / `PARALLEL_TASK_TIMEOUT_SEC` config | 可透過環境變數調整並行度和超時，無需重新部署 |

---

## ✅ 驗收標準（Done When）

### 核心功能
- [ ] `backend/app/services/agent_swarm.py` 存在且包含 `SwarmExecutor` class 及 `SwarmTask`/`SwarmResult` dataclass
- [ ] `SwarmExecutor.execute_swarm()` 使用 `asyncio.TaskGroup` + `asyncio.Semaphore(MAX_PARALLEL_TASKS)` 實現有界並行
- [ ] 每個 task 有獨立 `asyncio.timeout(PARALLEL_TASK_TIMEOUT_SEC)` 保護
- [ ] 單一 task 的 TimeoutError / Exception 不導致其他 task 被取消（ExceptionGroup 隔離）

### 資料模型
- [ ] `backend/app/database.py` 包含 `CREATE TABLE swarm_tasks` 且 schema 與 SPEC 一致
- [ ] `backend/app/models/api_schemas.py` 包含 `SwarmTaskSchema` 和 `SwarmBatchResponse`
- [ ] `backend/app/config.py` 包含 `MAX_PARALLEL_TASKS: int = 5` 和 `PARALLEL_TASK_TIMEOUT_SEC: int = 120`

### DecisionEngine 改造
- [ ] `DecisionEngine.evaluate()` 回傳 dict 包含 `parallel_tasks: list[dict]` 欄位
- [ ] `parallel_tasks` 只包含通過 auto-approval 規則的 option（CRITICAL/HIGH 排除、MANUAL mode 空 list）
- [ ] 同 `(technique_id, target_id)` 不重複出現
- [ ] 無 parallel_tasks 時回傳空 list `[]`（不是 None）

### OODAController 整合
- [ ] `OODAController.__init__` 接受 `SwarmExecutor` 依賴注入
- [ ] Act 階段：`parallel_tasks` 長度 > 1 時走 swarm path；0~1 時走既有 single path
- [ ] Swarm path 完成後正確更新 `ooda_iterations.act_summary`
- [ ] 每個成功 task 正確更新 `targets.is_compromised`、activate agent、increment `techniques_executed`
- [ ] C5ISR update 在所有 swarm tasks 完成後執行一次（不是每個 task 後）
- [ ] `build_ooda_controller()` factory 正確建立 `SwarmExecutor` 並注入

### WebSocket
- [ ] Swarm 開始時 broadcast `execution.batch_update`（所有 task 的初始 pending 狀態）
- [ ] Swarm 結束時 broadcast `execution.batch_update`（所有 task 的最終狀態）
- [ ] 各 task 獨立的 `execution.update` 仍由 `EngineRouter._finalize_execution()` 正常發送

### DB 並行安全
- [ ] `database.py` connection 設定 `PRAGMA journal_mode=WAL`
- [ ] `database.py` connection 設定 `PRAGMA busy_timeout=5000`
- [ ] 並行 5 個 task 同時寫入 DB 不產生 `OperationalError`（整合測試驗證）

### 測試
- [ ] `make test-filter FILTER=test_agent_swarm` 全數通過
- [ ] 測試覆蓋：空 task list、單一 task、多 task 並行、task timeout、task exception、all fail、partial success、semaphore saturation、DB 併發寫入
- [ ] `make lint` 無 error
- [ ] 既有 `test_initial_access_engine.py`、`test_spec_008_clients.py` 等不受影響（回歸測試通過）

### 文件
- [ ] 已更新 `CHANGELOG.md`
- [ ] 已更新 `docs/architecture.md`（若存在，新增 SwarmExecutor 至服務架構圖）

---

## 🚫 禁止事項（Out of Scope）

- **不要修改 EngineRouter.execute() 的簽名或回傳格式** — SwarmExecutor 作為 caller 使用既有介面，不改變 EngineRouter 內部邏輯
- **不要實作 mid-swarm cancellation** — V1 scope 不支援在 swarm 執行中取消個別 task；commander override 推進 phase 時，已啟動的 task 自然完成
- **不要引入外部 task queue（Celery / Redis / RQ）** — ADR-027 明確選擇 asyncio TaskGroup（Option A），不使用外部 queue
- **不要修改 APScheduler 的 OODA 觸發機制** — `max_instances=1` 已保護並行循環衝突
- **不要實作 swarm task 的持久化重啟（crash recovery）** — task 為 short-lived，process crash 後下一次 OODA 循環自然重新評估
- **不要修改前端 WebSocket handler** — 前端對未知事件類型已有 graceful ignore；`execution.batch_update` handler 為獨立前端 SPEC scope
- **不要為 DecisionEngine 加入跨目標路徑規劃（attack graph traversal）** — SPEC-031 scope
- **不要修改 OrientEngine 的 prompt 或 LLM 呼叫** — Orient 階段不受 Act 階段並行化影響
- **不要把 `swarm_tasks` 的資料暴露在 REST API** — V1 不新增 API endpoint；swarm 狀態透過 WebSocket `execution.batch_update` 推送

---

## 📎 參考資料（References）

- ADR-027：AgentSwarm 並行 Act 階段執行（asyncio TaskGroup 方案）
- SPEC-007：[OODA 循環引擎](./SPEC-007-ooda-loop-engine.md)（既有 OODAController 規格）
- SPEC-008：[執行引擎客戶端](./SPEC-008-execution-engine-clients.md)（EngineRouter 依賴）
- SPEC-021：[Attack Path Timeline](./SPEC-021-attack-path-timeline.md)（受並行執行影響的時間軸）
- SPEC-026：[Attack Situation Diagram](./SPEC-026-attack-situation-diagram.md)（受多目標同時 compromise 影響的 topology）
- XBOW 架構：短命任務 + 錯誤隔離 + 結果聚合 設計模式
- Python asyncio.TaskGroup：https://docs.python.org/3.12/library/asyncio-task.html#asyncio.TaskGroup
- Python ExceptionGroup：https://docs.python.org/3.12/library/exceptions.html#ExceptionGroup
- SQLite WAL mode：https://www.sqlite.org/wal.html
- 現有程式碼：
  - `backend/app/services/ooda_controller.py` — OODAController.trigger_cycle() Act 階段
  - `backend/app/services/engine_router.py` — EngineRouter.execute()
  - `backend/app/services/decision_engine.py` — DecisionEngine.evaluate()
  - `backend/app/config.py` — Settings class
  - `backend/app/models/api_schemas.py` — API schema 定義
  - `backend/app/database.py` — CREATE TABLE statements


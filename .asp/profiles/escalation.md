# Escalation Profile — P0-P3 嚴重度路由

<!-- requires: global_core -->
<!-- optional: multi_agent, autonomous_dev, pipeline -->
<!-- conflicts: (none) -->

適用：agent 無法繼續時的分級升級。取代散佈各 profile 的 PAUSE_AND_REPORT()。
載入條件：`mode: multi-agent` 或 `autonomous: enabled` 時自動載入

> **設計原則**：
> - 靈感來自 agency-agents 的 P0-P3 severity routing
> - 安全漏洞和 lint warning 不該走同一條升級路線
> - 所有升級產生 ESCALATION 交接單（結構化，可追蹤）

---

## 嚴重度定義

| 等級 | 名稱 | 判定條件 | 回應行動 | 處理者 |
|------|------|----------|----------|--------|
| **P0** | 緊急 | 安全漏洞、資料遺失風險、生產環境中斷 | 立即暫停所有並行軌道 + 通知人類 | Orchestrator + 人類 |
| **P1** | 高 | auto_fix + Orchestrator 重派全耗盡；並行軌道不可解衝突 | 暫停當前軌道，其他軌道繼續 | Orchestrator（嘗試解決）或人類 |
| **P2** | 中 | 單一模組 QA fail 3x；scope 超出；意外依賴 | 重新分派或增援 | Orchestrator |
| **P3** | 低 | Tech debt 累積；文件過期；非阻斷警告 | 記入 backlog | 自動記錄 |

---

## 升級函數

```
FUNCTION escalate(severity, reason, task_id=null, context=null):

  handoff = create_handoff(ESCALATION,
    severity   = severity,
    task_id    = task_id,
    reason     = reason,
    attempted_fixes = context.fix_history IF context ELSE null,
    context_snapshot = context  // 全量傳遞，不摘要
  )

  MATCH severity:

    "P0":
      // ─── 緊急：暫停一切 ───
      IF mode == "multi-agent":
        PAUSE_ALL_TRACKS()
      NOTIFY_HUMAN(handoff)
      LOG("🔴 P0 ESCALATION: {reason}")
      // autopilot 模式：task 標記 failed + exit_reason = "P0_escalation"
      IF autopilot_enabled:
        update_autopilot_state(task_id, status="failed",
          exit_reason="P0_escalation")

    "P1":
      // ─── 高：暫停當前軌道 ───
      IF mode == "multi-agent":
        PAUSE_TRACK(context.track IF context ELSE null)
        LOG("🟡 P1 ESCALATION: Track {context.track} paused")
      IF orchestrator_can_resolve(handoff):
        resolution = orchestrator.resolve(handoff)
        IF resolution.success:
          RESUME_TRACK(context.track IF context ELSE null)
        ELSE:
          NOTIFY_HUMAN(handoff)
      ELSE:
        NOTIFY_HUMAN(handoff)

    "P2":
      // ─── 中：重新分派或增援 ───
      IF can_reassign(context.task IF context ELSE null):
        new_role = select_alternative_agent(context.task)
        reassignment = create_handoff(REASSIGNMENT,
          to_agent = new_role,
          orchestrator_hint = "升級自 P2，前任 {context.from_agent} 失敗")
        LOG("🟠 P2 ESCALATION: Reassigning {task_id} to {new_role}")
      ELSE:
        LOG("🟠 P2 → P1: Cannot reassign, promoting severity")
        escalate(severity="P1", reason=reason, task_id=task_id, context=context)  // 升級到 P1

    "P3":
      // ─── 低：記入 backlog ───
      LOG_TECH_DEBT("P3: {reason}")
      LOG("⚪ P3 ESCALATION: Logged to tech-debt backlog")
```

---

## 觸發點映射

| 觸發來源 | 原有機制 | 新的升級路由 |
|----------|---------|------------|
| `auto_fix_loop` 振盪偵測 | `PAUSE_AND_REPORT(oscillation)` | `escalate(P2)` |
| `auto_fix_loop` 級聯偵測 | `PAUSE_AND_REPORT(cascade)` | `escalate(P2)` |
| `auto_fix_loop` 偷渡偵測 | `PAUSE_AND_REPORT(smuggling)` | `escalate(P1)` — 偷渡較嚴重 |
| `auto_fix_loop` 重試耗盡 | `on_worker_auto_fix_exhausted()` | `escalate(P2)` → Orchestrator 重派 |
| Orchestrator 重派 2 次仍失敗 | `escalate_to_human()` | `escalate(P1)` |
| 安全審查發現漏洞 | （無） | `escalate(P0)` |
| 生產環境事故 | `execute_hotfix()` | `escalate(P0)` |
| 品質門重試 2 次失敗 | （無） | `escalate(P2)` |
| Dev↔QA 迴路模組 3x 失敗 | （無） | `escalate(P2)` |
| 並行軌道不可解衝突 | （無） | `escalate(P1)` |
| Tech debt 累積 | `LOG_TECH_DEBT()` | `escalate(P3)` |

---

## 與其他 Profile 的關係

```
escalation.md
  ├── 取代 autonomous_dev.md 中的 PAUSE_AND_REPORT()
  ├── 取代 multi_agent.md 中的 escalate_to_human()
  ├── 整合 pipeline.md（品質門失敗的升級路由）
  ├── 整合 dev_qa_loop.md（模組級失敗的升級路由）
  └── 整合 autopilot.md（P0 時更新 autopilot state）
```

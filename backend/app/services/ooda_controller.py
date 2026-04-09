# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""OODA loop orchestrator — coordinates Observe -> Orient -> Decide -> Act."""

import logging
import uuid
from datetime import datetime, timezone

import asyncpg

from app.config import settings
from app.database import db_manager
from app.models.enums import OODAPhase
from app.services.agent_swarm import SwarmExecutor
from app.services.c5isr_mapper import C5ISRMapper
from app.services import constraint_engine as ce
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.mcp_client_manager import get_mcp_manager
from app.services.orient_engine import OrientEngine
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


class OODAController:
    """
    OODA cycle orchestrator — manages Observe -> Orient -> Decide -> Act transitions.
    Contains no business logic, only coordinates the 5 specialized services.
    """

    def __init__(
        self,
        fact_collector: FactCollector,
        orient_engine: OrientEngine,
        decision_engine: DecisionEngine,
        engine_router: EngineRouter,
        c5isr_mapper: C5ISRMapper,
        ws_manager: WebSocketManager,
        swarm_executor: SwarmExecutor | None = None,
    ):
        self._fact_collector = fact_collector
        self._orient = orient_engine
        self._decision = decision_engine
        self._router = engine_router
        self._c5isr = c5isr_mapper
        self._ws = ws_manager
        self._swarm = swarm_executor

    async def trigger_cycle(
        self, db: asyncpg.Connection, operation_id: str
    ) -> dict:
        """
        Trigger one complete OODA iteration:
        1. Observe: fact_collector.collect()
        2. Orient:  orient_engine.analyze()
        3. Decide:  decision_engine.evaluate()
        4. Act:     engine_router.execute() (if auto-approved)
        5. Cross:   c5isr_mapper.update()
        """

        # Create new OODA iteration
        row = await db.fetchrow(
            "SELECT COALESCE(MAX(iteration_number), 0) + 1 AS next_num "
            "FROM ooda_iterations WHERE operation_id = $1",
            operation_id,
        )
        next_num = row["next_num"]
        ooda_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await db.execute(
            "INSERT INTO ooda_iterations "
            "(id, operation_id, iteration_number, phase, started_at) "
            "VALUES ($1, $2, $3, 'observe', $4)",
            ooda_id, operation_id, next_num, now,
        )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = 'observe', "
            "ooda_iteration_count = $1 WHERE id = $2",
            next_num, operation_id,
        )

        # Set operation status to active on first cycle
        await self._activate_if_planning(db, operation_id)
        await self._broadcast_phase(operation_id, OODAPhase.OBSERVE)

        # -- 1. OBSERVE --
        logger.info("OODA[%s] Observe phase", ooda_id[:8])
        new_facts = await self._fact_collector.collect(db, operation_id)
        observe_summary = await self._fact_collector.summarize(db, operation_id)
        await db.execute(
            "UPDATE ooda_iterations SET observe_summary = $1 WHERE id = $2",
            observe_summary[:1000], ooda_id,
        )
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Observe: collected {len(new_facts)} new facts")

        # -- 1.1. AUTO-RECON for sparse-intel targets (SPEC-052) --
        # Mission-profile-aware fact threshold: SR=0, CO=2, SP=3, FA=5
        _RECON_FACT_THRESHOLD: dict[str, int] = {
            "SR": 0, "CO": 2, "SP": 3, "FA": 5,
        }
        _RECON_NOISE_COST: int = 2  # nmap scan = 2 noise points (T1595.001 low)

        try:
            op_profile_row = await db.fetchrow(
                "SELECT mission_profile FROM operations WHERE id = $1", operation_id,
            )
            profile_code = (op_profile_row["mission_profile"] if op_profile_row else None) or "SP"
            fact_threshold = _RECON_FACT_THRESHOLD.get(profile_code, 3)

            sparse_targets = await db.fetch(
                """SELECT t.id, t.hostname, t.ip_address
                   FROM targets t
                   LEFT JOIN facts f ON f.source_target_id = t.id
                       AND f.operation_id = $1
                   WHERE t.operation_id = $1 AND t.is_active = TRUE
                   GROUP BY t.id, t.hostname, t.ip_address
                   HAVING COUNT(f.id) < $2""",
                operation_id, fact_threshold + 1,  # < threshold+1 means <= threshold, but we want < threshold
            )

            # Filter to targets strictly below threshold
            # (the SQL HAVING uses < $2 where $2 = threshold, so it's correct)
            # Re-query with exact threshold
            sparse_targets = await db.fetch(
                """SELECT t.id, t.hostname, t.ip_address
                   FROM targets t
                   LEFT JOIN facts f ON f.source_target_id = t.id
                       AND f.operation_id = $1
                   WHERE t.operation_id = $1 AND t.is_active = TRUE
                   GROUP BY t.id, t.hostname, t.ip_address
                   HAVING COUNT(f.id) < $2""",
                operation_id, fact_threshold,
            )

            if sparse_targets:
                # SPEC-052: Check noise budget before scanning
                try:
                    constraints = await ce.evaluate(db, operation_id)
                    noise_remaining = getattr(constraints, "noise_budget_remaining", 999)
                except Exception:
                    noise_remaining = 999  # If constraint engine fails, allow recon

                if noise_remaining < _RECON_NOISE_COST:
                    logger.info(
                        "OODA[%s] Auto-recon deferred: noise budget insufficient "
                        "(remaining=%d, cost=%d, profile=%s)",
                        ooda_id[:8], noise_remaining, _RECON_NOISE_COST, profile_code,
                    )
                    await self._write_log(db, operation_id, "warning",
                        f"OODA #{next_num} Auto-recon deferred: noise budget insufficient")
                else:
                    from app.services.recon_engine import ReconEngine
                    recon = ReconEngine(self._ws)
                    # Mission-profile parallel limit
                    _MAX_RECON_PARALLEL: dict[str, int] = {
                        "SR": 1, "CO": 2, "SP": 3, "FA": 5,
                    }
                    max_targets = _MAX_RECON_PARALLEL.get(profile_code, 3)

                    for st in sparse_targets[:max_targets]:
                        target_addr = st["ip_address"] or st["hostname"]
                        if not target_addr:
                            continue
                        try:
                            recon_result = await recon.scan(
                                db, operation_id, st["id"],
                            )
                            logger.info(
                                "OODA[%s] Auto-recon on %s: %d services found",
                                ooda_id[:8], target_addr,
                                len(recon_result.services) if recon_result else 0,
                            )
                        except Exception as recon_exc:
                            logger.warning(
                                "OODA[%s] Auto-recon failed for %s: %s",
                                ooda_id[:8], target_addr, recon_exc,
                            )

                    # Re-collect facts after auto-recon to include new findings
                    new_facts_2 = await self._fact_collector.collect(db, operation_id)
                    if new_facts_2:
                        observe_summary = await self._fact_collector.summarize(
                            db, operation_id,
                        )
                        await db.execute(
                            "UPDATE ooda_iterations SET observe_summary = $1 WHERE id = $2",
                            observe_summary[:1000], ooda_id,
                        )
                        await self._write_log(db, operation_id, "info",
                            f"OODA #{next_num} Auto-recon: collected {len(new_facts_2)} additional facts")
        except Exception as auto_recon_exc:
            logger.warning("Auto-recon step failed: %s", auto_recon_exc)

        # -- PRE-ORIENT: Evaluate constraints (SPEC-047) --
        op_row = await db.fetchrow(
            "SELECT mission_profile FROM operations WHERE id = $1", operation_id,
        )
        mission_code = (op_row["mission_profile"] if op_row else None) or "SP"
        constraints = await ce.evaluate(db, operation_id, mission_code, ws_manager=self._ws)
        if constraints.warnings or constraints.hard_limits:
            await self._write_log(db, operation_id, "warning",
                f"OODA #{next_num} Constraints: {len(constraints.warnings)} warnings, "
                f"{len(constraints.hard_limits)} hard limits"
                + (f", forced_mode={constraints.forced_mode}" if constraints.forced_mode else ""))
            try:
                await self._ws.broadcast(operation_id, "constraint.active",
                    constraints.model_dump())
            except Exception:
                pass

        # -- 1.5. ATTACK GRAPH REBUILD --
        from app.services.attack_graph_engine import AttackGraphEngine
        graph_engine = AttackGraphEngine(self._ws)
        attack_graph = await graph_engine.rebuild(db, operation_id)
        graph_summary = graph_engine.build_orient_summary(attack_graph)

        # -- 2. ORIENT --
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.ORIENT)
        logger.info("OODA[%s] Orient phase -- calling PentestGPT", ooda_id[:8])
        recommendation = await self._orient.analyze(
            db, operation_id, observe_summary,
            attack_graph_summary=graph_summary,
        )
        if not recommendation:
            await self._write_log(db, operation_id, "warning",
                "Orient phase aborted: LLM unavailable or returned invalid response")
            await db.execute(
                "UPDATE ooda_iterations SET phase = 'orient', completed_at = NOW() WHERE id = $1",
                ooda_id,
            )
            return {"status": "aborted", "reason": "orient_llm_unavailable"}
        orient_summary = recommendation.get("situation_assessment", "")
        await db.execute(
            "UPDATE ooda_iterations SET orient_summary = $1 WHERE id = $2",
            orient_summary[:1000], ooda_id,
        )
        await self._advance_mission_step(db, operation_id, step_index=0, status="completed")
        await self._advance_mission_step(db, operation_id, step_index=1, status="running")
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Orient: {orient_summary[:80]}")

        # -- 3. DECIDE --
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.DECIDE)
        logger.info("OODA[%s] Decide phase", ooda_id[:8])
        decision = await self._decision.evaluate(db, operation_id, recommendation, constraints=constraints)
        decide_summary = decision.get("reason", "")
        await db.execute(
            "UPDATE ooda_iterations SET decide_summary = $1 WHERE id = $2",
            decide_summary[:1000], ooda_id,
        )
        # Broadcast decision result with confidence breakdown and noise/risk levels
        try:
            await self._ws.broadcast(operation_id, "decision.result", {
                "confidence_breakdown": decision.get("confidence_breakdown"),
                "composite_confidence": decision.get("composite_confidence"),
                "noise_level": decision.get("noise_level"),
                "risk_level": decision.get("risk_level"),
                "auto_approved": decision.get("auto_approved"),
                "reason": decide_summary,
            })
        except Exception:
            pass  # fire-and-forget
        await self._advance_mission_step(db, operation_id, step_index=1, status="completed")
        await self._advance_mission_step(db, operation_id, step_index=2, status="running")
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Decide: {decide_summary[:80]}")

        # -- 4. ACT --
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.ACT)
        execution_result = None
        act_summary = ""

        # -- PRE-ACT: OPSEC noise budget pre-check --
        noise_map = {"low": 2, "medium": 5, "high": 8}
        try:
            noise_budget_remaining = getattr(constraints, "noise_budget_remaining", None)
            if noise_budget_remaining is not None and decision.get("technique_id"):
                pre_noise_row = await db.fetchrow(
                    "SELECT noise_level FROM techniques WHERE mitre_id = $1",
                    decision["technique_id"],
                )
                pre_noise_level = (
                    pre_noise_row["noise_level"]
                    if pre_noise_row and pre_noise_row["noise_level"]
                    else "medium"
                )
                noise_points = noise_map.get(pre_noise_level, 5)
                if noise_budget_remaining - noise_points < 0:
                    logger.warning(
                        "OODA[%s] PRE-ACT OPSEC: technique %s noise=%s (%d pts) "
                        "exceeds remaining budget (%d) -- requiring confirmation",
                        ooda_id[:8],
                        decision["technique_id"],
                        pre_noise_level,
                        noise_points,
                        noise_budget_remaining,
                    )
                    decision["needs_confirmation"] = True
                    decision["auto_approved"] = False
                    decision["reason"] = (
                        f"OPSEC noise budget exceeded: technique {decision['technique_id']} "
                        f"costs {noise_points} pts but only {noise_budget_remaining} pts remaining"
                    )
                    await self._write_log(
                        db, operation_id, "warning",
                        f"OODA #{next_num} PRE-ACT OPSEC: noise budget would be exceeded "
                        f"({pre_noise_level}={noise_points} pts, remaining={noise_budget_remaining}) "
                        f"-- requiring commander confirmation",
                    )
        except Exception as pre_opsec_exc:
            logger.warning("PRE-ACT OPSEC check failed: %s", pre_opsec_exc)

        parallel_tasks = decision.get("parallel_tasks", [])

        if self._swarm and parallel_tasks and len(parallel_tasks) > 1:
            # -- SWARM PATH (SPEC-030) --
            logger.info("OODA[%s] Act phase -- swarm executing %d parallel tasks", ooda_id[:8], len(parallel_tasks))
            swarm_result = await self._swarm.execute_swarm(db_manager.pool, operation_id, ooda_id, parallel_tasks)
            act_summary = swarm_result.act_summary

            for st in swarm_result.tasks:
                if st.status == "completed" and st.result and st.result.get("status") == "success":
                    execution_result = st.result
                    # Update target, agent, counters (same as single path success)
                    # Don't downgrade privilege_level if already Root
                    if st.target_id:
                        await db.execute(
                            "UPDATE targets SET is_compromised = TRUE, "
                            "privilege_level = CASE WHEN privilege_level = 'Root' THEN 'Root' ELSE 'User' END, "
                            "access_status = 'active' "
                            "WHERE id = $1 AND operation_id = $2",
                            st.target_id, operation_id,
                        )
                    completed_at_now = datetime.now(timezone.utc)
                    await db.execute(
                        "UPDATE agents SET status = 'alive', last_beacon = $1 "
                        "WHERE operation_id = $2 AND status = 'pending' "
                        "AND ctid = (SELECT ctid FROM agents WHERE operation_id = $2 AND status = 'pending' LIMIT 1)",
                        completed_at_now, operation_id,
                    )
                    await db.execute(
                        "UPDATE operations SET techniques_executed = techniques_executed + 1, "
                        "active_agents = (SELECT COUNT(*) FROM agents WHERE operation_id = $1 AND status = 'alive') "
                        "WHERE id = $1",
                        operation_id,
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
            # -- SINGLE PATH (existing, unchanged) --
            logger.info("OODA[%s] Act phase -- executing %s", ooda_id[:8], decision["technique_id"])
            execution_result = await self._router.execute(
                db,
                technique_id=decision["technique_id"],
                target_id=decision["target_id"],
                engine=decision.get("engine", "ssh"),
                operation_id=operation_id,
                ooda_iteration_id=ooda_id,
            )
            act_summary = (
                f"Executed {decision['technique_id']} via {decision.get('engine', 'ssh')}: "
                f"{execution_result.get('status', 'unknown')}"
            )
            # Link execution to iteration
            if execution_result.get("execution_id"):
                await db.execute(
                    "UPDATE ooda_iterations SET technique_execution_id = $1 WHERE id = $2",
                    execution_result["execution_id"], ooda_id,
                )
            if execution_result and execution_result.get("status") == "success":
                # Mark target as compromised (don't downgrade Root -> User)
                if decision.get("target_id"):
                    await db.execute(
                        "UPDATE targets SET is_compromised = TRUE, "
                        "privilege_level = CASE WHEN privilege_level = 'Root' THEN 'Root' ELSE 'User' END, "
                        "access_status = 'active' "
                        "WHERE id = $1 AND operation_id = $2",
                        decision["target_id"], operation_id,
                    )
                # Activate one pending agent
                completed_at_now = datetime.now(timezone.utc)
                await db.execute(
                    "UPDATE agents SET status = 'alive', last_beacon = $1 "
                    "WHERE operation_id = $2 AND status = 'pending' "
                    "AND ctid = (SELECT ctid FROM agents WHERE operation_id = $2 AND status = 'pending' LIMIT 1)",
                    completed_at_now, operation_id,
                )
                # Advance mission steps
                await self._advance_mission_step(db, operation_id, step_index=2, status="completed")
                await self._advance_mission_step(db, operation_id, step_index=3, status="running")
                # Update operation counters
                await db.execute(
                    "UPDATE operations SET techniques_executed = techniques_executed + 1, "
                    "active_agents = (SELECT COUNT(*) FROM agents WHERE operation_id = $1 AND status = 'alive') "
                    "WHERE id = $1",
                    operation_id,
                )
                await self._write_log(db, operation_id, "success",
                    f"OODA #{next_num} Act: {decision['technique_id']} executed successfully on {decision.get('target_id', 'unknown')}")

                # SPEC-044: Update vulnerability status on successful exploitation
                try:
                    from app.services.vulnerability_manager import VulnerabilityManager
                    vuln_mgr = VulnerabilityManager()
                    # Look up CVEs associated with this technique on this target
                    vuln_cve_rows = await db.fetch(
                        "SELECT DISTINCT cve_id FROM vulnerabilities "
                        "WHERE operation_id = $1 AND target_id = $2 "
                        "AND status IN ('discovered', 'confirmed')",
                        operation_id, decision["target_id"],
                    )
                    for vcr in vuln_cve_rows:
                        await vuln_mgr.mark_exploited_by_cve(
                            db, operation_id, vcr["cve_id"], decision["target_id"],
                        )
                    if vuln_cve_rows:
                        logger.info(
                            "OODA[%s] SPEC-044: marked %d vulnerabilities as exploited on target %s",
                            ooda_id[:8], len(vuln_cve_rows), decision["target_id"],
                        )
                except Exception as vuln_exc:
                    logger.warning("Failed to update vulnerability status: %s", vuln_exc)

            elif execution_result:
                await self._write_log(db, operation_id, "warning",
                    f"OODA #{next_num} Act: {decision['technique_id']} returned {execution_result.get('status', 'unknown')}")
        else:
            # -- MANUAL APPROVAL (existing, unchanged) --
            act_summary = f"Awaiting commander approval: {decision.get('reason', 'manual required')}"
            logger.info("OODA[%s] Act phase -- needs approval: %s", ooda_id[:8], act_summary)
            await self._write_log(db, operation_id, "warning",
                f"OODA #{next_num} Act: awaiting commander approval -- {decision.get('reason', 'manual required')}")

        # Post-Act MCP enrichment
        if execution_result:
            await self._run_mcp_enrichment(db, operation_id, execution_result)

        completed_at = datetime.now(timezone.utc)
        await db.execute(
            "UPDATE ooda_iterations SET act_summary = $1, completed_at = $2 WHERE id = $3",
            act_summary[:1000], completed_at, ooda_id,
        )

        # -- POST-ACT: OPSEC evaluation (SPEC-048) --
        try:
            from app.services import opsec_monitor, threat_level as tl_svc

            exec_success = bool(
                execution_result and execution_result.get("status") == "success"
            )
            tech_noise = "medium"  # default
            if decision.get("technique_id"):
                noise_row = await db.fetchrow(
                    "SELECT noise_level FROM techniques WHERE mitre_id = $1",
                    decision["technique_id"],
                )
                if noise_row and noise_row["noise_level"]:
                    tech_noise = noise_row["noise_level"]

            opsec_status = await opsec_monitor.evaluate_after_act(
                db, operation_id,
                technique_noise=tech_noise,
                target_id=decision.get("target_id"),
                technique_id=decision.get("technique_id"),
                execution_success=exec_success,
            )
            threat = await tl_svc.compute_threat_level(db, operation_id)

            # Broadcast OPSEC alerts if thresholds exceeded
            if opsec_status.detection_risk > 60:
                await self._ws.broadcast(operation_id, "opsec.alert", {
                    "detection_risk": opsec_status.detection_risk,
                    "noise_budget_remaining": opsec_status.noise_budget_remaining,
                })
            if opsec_status.noise_budget_remaining <= 0:
                await self._ws.broadcast(operation_id, "opsec.budget_warning", {
                    "budget_total": opsec_status.noise_budget_total,
                    "budget_used": opsec_status.noise_budget_used,
                })
            await self._ws.broadcast(operation_id, "threat.update", {
                "level": threat.level,
                "components": threat.components,
            })
        except Exception as exc:
            logger.warning("OPSEC post-act evaluation failed: %s", exc)

        # -- 5. C5ISR UPDATE --
        logger.info("OODA[%s] C5ISR update", ooda_id[:8])
        await self._c5isr.update(db, operation_id)
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} complete -- C5ISR domains updated")

        # Update operation success rate
        stats = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success "
            "FROM technique_executions WHERE operation_id = $1",
            operation_id,
        )
        if stats["total"] > 0:
            rate = round(stats["success"] / stats["total"] * 100, 1)
            await db.execute(
                "UPDATE operations SET success_rate = $1 WHERE id = $2",
                rate, operation_id,
            )

        # Broadcast ooda.completed -- after ALL DB updates are committed
        try:
            await self._ws.broadcast(
                operation_id, "ooda.completed",
                {
                    "iteration_id": ooda_id,
                    "iteration_number": next_num,
                    "technique_executed": decision.get("technique_id"),
                    "success": bool(
                        execution_result and execution_result.get("status") == "success"
                    ),
                },
            )
        except Exception:
            pass  # fire-and-forget

        # Return iteration summary
        final = await db.fetchrow(
            "SELECT * FROM ooda_iterations WHERE id = $1", ooda_id,
        )
        return dict(final) if final else {"id": ooda_id}

    async def advance_phase(
        self, db: asyncpg.Connection, operation_id: str, phase: OODAPhase
    ):
        """Manual phase advancement (commander override)."""
        row = await db.fetchrow(
            "SELECT id FROM ooda_iterations WHERE operation_id = $1 "
            "ORDER BY iteration_number DESC LIMIT 1",
            operation_id,
        )
        if row:
            await db.execute(
                "UPDATE ooda_iterations SET phase = $1 WHERE id = $2",
                phase.value, row["id"],
            )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = $1 WHERE id = $2",
            phase.value, operation_id,
        )
        await self._broadcast_phase(operation_id, phase)

    async def get_current(self, db: asyncpg.Connection, operation_id: str) -> dict | None:
        row = await db.fetchrow(
            "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
            "ORDER BY iteration_number DESC LIMIT 1",
            operation_id,
        )
        return dict(row) if row else None

    async def _activate_if_planning(
        self, db: asyncpg.Connection, operation_id: str
    ):
        """Set operation status to 'active' if currently 'planning'."""
        op_row = await db.fetchrow(
            "SELECT status FROM operations WHERE id = $1", operation_id,
        )
        if op_row and op_row["status"] == "planning":
            await db.execute(
                "UPDATE operations SET status = 'active' WHERE id = $1",
                operation_id,
            )

    async def _update_phase(
        self, db: asyncpg.Connection, operation_id: str,
        ooda_id: str, phase: OODAPhase,
    ):
        await db.execute(
            "UPDATE ooda_iterations SET phase = $1 WHERE id = $2",
            phase.value, ooda_id,
        )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = $1 WHERE id = $2",
            phase.value, operation_id,
        )
        await self._broadcast_phase(operation_id, phase)

    async def _broadcast_phase(self, operation_id: str, phase: OODAPhase):
        try:
            await self._ws.broadcast(
                operation_id, "ooda.phase", {"phase": phase.value}
            )
        except Exception:
            pass  # fire-and-forget per SPEC-007

    async def _write_log(
        self, db: asyncpg.Connection, operation_id: str,
        severity: str, message: str,
    ) -> None:
        """Write a log entry and broadcast via WebSocket."""
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await db.execute(
            "INSERT INTO log_entries "
            "(id, operation_id, timestamp, severity, source, message) "
            "VALUES ($1, $2, $3, $4, 'ooda_controller', $5)",
            log_id, operation_id, now, severity, message,
        )
        try:
            await self._ws.broadcast(operation_id, "log.new", {
                "id": log_id, "timestamp": now, "severity": severity,
                "source": "ooda_controller", "message": message,
            })
        except Exception:
            pass  # fire-and-forget

    async def _advance_mission_step(
        self, db: asyncpg.Connection, operation_id: str,
        step_index: int, status: str,
    ) -> None:
        """Update a mission step by its order index (0-based)."""
        now = datetime.now(timezone.utc)
        row = await db.fetchrow(
            "SELECT id FROM mission_steps "
            "WHERE operation_id = $1 ORDER BY step_number "
            "LIMIT 1 OFFSET $2",
            operation_id, step_index,
        )
        if not row:
            return
        step_id = row["id"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]
        if status == "running":
            await db.execute(
                "UPDATE mission_steps SET status = $1, started_at = $2 WHERE id = $3",
                status, now, step_id,
            )
        elif status == "completed":
            await db.execute(
                "UPDATE mission_steps SET status = $1, completed_at = $2 WHERE id = $3",
                status, now, step_id,
            )
        else:
            await db.execute(
                "UPDATE mission_steps SET status = $1 WHERE id = $2",
                status, step_id,
            )

    async def _run_mcp_enrichment(
        self, db, operation_id: str, execution_result: dict
    ) -> None:
        """Post-Act hook: log MCP enrichment opportunity for future chaining."""
        if not settings.MCP_ENABLED:
            return
        if execution_result.get("engine") != "mcp":
            return
        if execution_result.get("status") != "success":
            return
        logger.info(
            "OODA enrichment: MCP execution succeeded for %s -- enrichment pipeline available",
            operation_id,
        )


def build_ooda_controller() -> "OODAController":
    """Factory for creating OODAController without request context (used by scheduler)."""
    from app.clients.c2_client import C2EngineClient
    from app.clients.mock_c2_client import MockC2Client
    from app.ws_manager import ws_manager

    fc = FactCollector(ws_manager)
    orient = OrientEngine(ws_manager)
    decision = DecisionEngine()
    c5isr = C5ISRMapper(ws_manager)

    # Mirror _get_controller() logic: respect MOCK_C2_ENGINE setting
    c2_engine: MockC2Client | C2EngineClient = MockC2Client()
    if not settings.MOCK_C2_ENGINE:
        try:
            c2_engine = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
        except Exception:
            logger.warning("build_ooda_controller: failed to connect to C2 engine, falling back to mock")

    mcp_engine_client = None
    if settings.MCP_ENABLED:
        from app.clients.mcp_engine_client import MCPEngineClient

        mcp_mgr = get_mcp_manager()
        if mcp_mgr is not None:
            mcp_engine_client = MCPEngineClient(mcp_mgr)

    router_svc = EngineRouter(c2_engine, fc, ws_manager, mcp_engine=mcp_engine_client)

    swarm = SwarmExecutor(engine_router=router_svc, ws_manager=ws_manager)

    return OODAController(fc, orient, decision, router_svc, c5isr, ws_manager, swarm_executor=swarm)

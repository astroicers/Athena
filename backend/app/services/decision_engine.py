# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Decide phase — evaluate recommendation against risk thresholds."""

import logging

import asyncpg

from app.models.enums import AutomationMode, NOISE_POINTS, NoiseLevel, RiskLevel
from app.services.kill_chain_enforcer import KillChainEnforcer
from app.services.knowledge_base import get_noise_risk_matrix
from app.services.validation_engine import ValidationEngine

logger = logging.getLogger(__name__)

# Risk level ordering for comparison
_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}

# Noise points per noise_level for budget tracking (NR2)
_NOISE_POINTS = NOISE_POINTS

# Noise x Risk decision matrix per mission profile (NR1)
# True = auto-approvable, False = needs_confirmation, None = needs_manual
def _build_noise_matrix() -> dict[str, dict[tuple[str, str], bool | None]]:
    """Build noise×risk decision matrix from YAML. Key 'low_medium' -> tuple ('low','medium')."""
    raw = get_noise_risk_matrix()
    result: dict[str, dict[tuple[str, str], bool | None]] = {}
    for profile, entries in raw.items():
        result[profile] = {
            tuple(k.split("_", 1)): v
            for k, v in entries.items()
        }
    return result

_NOISE_RISK_MATRIX = _build_noise_matrix()


class DecisionEngine:
    """Decide phase: apply ADR-004 risk threshold rules to PentestGPT recommendation."""

    def __init__(
        self,
        enforcer: "KillChainEnforcer | None" = None,
        validation_engine: "ValidationEngine | None" = None,
    ):
        self._enforcer = enforcer or KillChainEnforcer()
        self._validation_engine = validation_engine or ValidationEngine()

    async def evaluate(
        self, db: asyncpg.Connection, operation_id: str, recommendation: dict,
        constraints=None,
    ) -> dict:
        """
        Decision logic per ADR-004:
        - MANUAL mode        -> always auto_approved=False
        - confidence < 0.5   -> force manual review
        - CRITICAL            -> auto_approved=False, needs_manual=True
        - HIGH                -> auto_approved=False, needs_confirmation=True (HexConfirmModal)
        - MEDIUM above thresh -> auto_approved=False, needs_confirmation=True (queue + approve)
        - MEDIUM within thresh-> auto_approved=True (auto-queue)
        - LOW                 -> auto_approved=True (auto-execute)
        """
        op = await db.fetchrow(
            "SELECT automation_mode, risk_threshold FROM operations WHERE id = $1",
            operation_id,
        )
        if not op:
            return {"error": "operation not found", "auto_approved": False}

        automation_mode = op["automation_mode"] or "semi_auto"
        risk_threshold = op["risk_threshold"] or "medium"

        # Get recommended technique's risk level
        rec_technique_id = recommendation.get("recommended_technique_id", "")
        options = recommendation.get("options", [])
        raw_confidence = recommendation.get("confidence", 0.0)

        # Find the recommended option
        selected_option = None
        for opt in options:
            if opt.get("technique_id") == rec_technique_id:
                selected_option = opt
                break
        if not selected_option and options:
            selected_option = options[0]

        technique_risk = RiskLevel(
            (selected_option or {}).get("risk_level", "medium")
        )
        engine = (selected_option or {}).get("recommended_engine", "ssh")

        # Priority: explicit active target > heuristic fallback
        target_row = await db.fetchrow(
            "SELECT id FROM targets WHERE operation_id = $1 AND is_active = TRUE LIMIT 1",
            operation_id,
        )
        if not target_row:
            # Fall back to original heuristic
            target_row = await db.fetchrow(
                "SELECT id FROM targets WHERE operation_id = $1 ORDER BY is_compromised DESC LIMIT 1",
                operation_id,
            )
        target_id = target_row["id"] if target_row else None

        # -- SPEC-044: Dynamic Validation before composite confidence --
        validation_result = await self._validation_engine.validate(
            db, recommendation, operation_id,
        )
        original_confidence = raw_confidence
        raw_confidence = max(
            0.0, min(1.0, raw_confidence + validation_result.delta),
        )
        recommendation["confidence"] = raw_confidence
        if validation_result.outcome != "skipped":
            logger.info(
                "SPEC-044 validation: outcome=%s, delta=%.2f, "
                "confidence %.2f->%.2f, checks=%s",
                validation_result.outcome, validation_result.delta,
                original_confidence, raw_confidence,
                validation_result.checks,
            )

        # -- Composite confidence (SPEC-040) --
        tactic_id = await self._resolve_tactic_id(
            db, operation_id, rec_technique_id, target_id
        )
        composite, confidence_breakdown = await self._compute_composite_confidence(
            db, operation_id, rec_technique_id, target_id, raw_confidence, tactic_id
        )
        confidence = composite

        # SPEC-047: Apply constraint overrides
        blocked_targets: set[str] = set()
        if constraints is not None:
            if constraints.min_confidence_override is not None:
                # Override the default 0.5 confidence floor
                pass  # Applied below in threshold checks
            blocked_targets = set(constraints.blocked_targets or [])

        # If target is blocked by constraints, reject immediately
        if target_id and target_id in blocked_targets:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "risk_level": technique_risk.value,
                "composite_confidence": composite,
                "confidence_breakdown": confidence_breakdown,
                "validation_result": {
                    "outcome": validation_result.outcome,
                    "checks": validation_result.checks,
                    "delta": validation_result.delta,
                },
                "auto_approved": False,
                "needs_confirmation": False,
                "needs_manual": True,
                "reason": "Target blocked by C5ISR constraints",
                "parallel_tasks": [],
            }

        # Effective confidence floor from constraints
        min_confidence_floor = 0.5
        if constraints is not None and constraints.min_confidence_override is not None:
            min_confidence_floor = constraints.min_confidence_override

        # -- NR1: Noise×Risk cross-matrix check --
        technique_noise = await self._get_technique_noise_level(db, rec_technique_id)
        mission_code = await self._get_mission_code(db, operation_id)
        matrix = _NOISE_RISK_MATRIX.get(mission_code, _NOISE_RISK_MATRIX["SP"])
        nr_decision = matrix.get(
            (technique_noise, technique_risk.value), False
        )
        noise_points = _NOISE_POINTS.get(technique_noise, 5)

        # -- NR2: Noise budget enforcement --
        noise_budget_remaining = 999  # default unlimited
        if constraints is not None:
            noise_budget_remaining = constraints.noise_budget_remaining

        if noise_budget_remaining <= 0:
            logger.warning(
                "Noise budget exhausted for operation %s — blocking auto-approve",
                operation_id,
            )
            return {
                **{
                    "technique_id": rec_technique_id,
                    "target_id": target_id,
                    "engine": engine,
                    "risk_level": technique_risk.value,
                    "noise_level": technique_noise,
                    "composite_confidence": composite,
                    "confidence_breakdown": confidence_breakdown,
                    "validation_result": {
                        "outcome": validation_result.outcome,
                        "checks": validation_result.checks,
                        "delta": validation_result.delta,
                    },
                },
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "reason": "Noise budget exhausted — requires commander approval to proceed",
                "parallel_tasks": [],
            }

        if noise_budget_remaining < noise_points:
            logger.warning(
                "Noise budget low (%d remaining, technique needs %d) for %s",
                noise_budget_remaining, noise_points, operation_id,
            )
            # Don't block but force confirmation
            nr_decision = False

        # NR1: Apply matrix decision override
        if nr_decision is None:
            return {
                **{
                    "technique_id": rec_technique_id,
                    "target_id": target_id,
                    "engine": engine,
                    "risk_level": technique_risk.value,
                    "noise_level": technique_noise,
                    "composite_confidence": composite,
                    "confidence_breakdown": confidence_breakdown,
                    "validation_result": {
                        "outcome": validation_result.outcome,
                        "checks": validation_result.checks,
                        "delta": validation_result.delta,
                    },
                },
                "auto_approved": False,
                "needs_confirmation": False,
                "needs_manual": True,
                "reason": (
                    f"Noise×Risk matrix ({mission_code}): "
                    f"noise={technique_noise}, risk={technique_risk.value} "
                    f"— requires manual authorization"
                ),
                "parallel_tasks": [],
            }

        # Semi-auto: apply risk threshold rules
        tech_level = _RISK_ORDER.get(technique_risk, 1)
        threshold_level = _RISK_ORDER.get(RiskLevel(risk_threshold), 1)

        # Build parallel_tasks from all auto-approvable options (SPEC-030)
        parallel_tasks: list[dict] = []
        if automation_mode != AutomationMode.MANUAL and confidence >= min_confidence_floor:
            for opt in options:
                opt_risk = RiskLevel(opt.get("risk_level", "medium"))
                opt_level = _RISK_ORDER.get(opt_risk, 1)
                if opt_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                    continue
                if opt_level > threshold_level:
                    continue
                opt_target = opt.get("target_id") or target_id
                if not opt_target:
                    continue
                # SPEC-047: Skip blocked targets
                if opt_target in blocked_targets:
                    continue
                parallel_tasks.append({
                    "technique_id": opt.get("technique_id"),
                    "target_id": opt_target,
                    "engine": opt.get("recommended_engine", "ssh"),
                    "risk_level": opt_risk.value,
                })
            # Deduplicate
            seen: set[tuple[str, str]] = set()
            deduped: list[dict] = []
            for pt in parallel_tasks:
                key = (pt["technique_id"], pt["target_id"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(pt)
            parallel_tasks = deduped

            # SPEC-058: Prerequisite filter — remove credential/exploit tasks
            # when recon task is in the same batch (recon must complete first
            # to provide service.open_port facts for InitialAccessEngine)
            _RECON_TECHNIQUES = {"T1046", "T1018", "T1595"}
            _RECON_DEPENDENT_PREFIXES = ("T1110", "T1078", "T1190")
            has_recon = any(
                t["technique_id"] in _RECON_TECHNIQUES for t in parallel_tasks
            )
            if has_recon:
                before_count = len(parallel_tasks)
                parallel_tasks = [
                    t for t in parallel_tasks
                    if not t["technique_id"].startswith(_RECON_DEPENDENT_PREFIXES)
                ]
                removed = before_count - len(parallel_tasks)
                if removed:
                    logger.warning(
                        "SPEC-058: removed %d recon-dependent tasks from parallel batch "
                        "(recon must complete first)", removed,
                    )

        base = {
            "technique_id": rec_technique_id,
            "target_id": target_id,
            "engine": engine,
            "risk_level": technique_risk.value,
            "noise_level": technique_noise,
            "composite_confidence": composite,
            "confidence_breakdown": confidence_breakdown,
            "validation_result": {
                "outcome": validation_result.outcome,
                "checks": validation_result.checks,
                "delta": validation_result.delta,
            },
        }

        # MANUAL mode -> always require human approval
        if automation_mode == AutomationMode.MANUAL:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "reason": "Manual mode -- all decisions require commander approval",
                "parallel_tasks": [],
            }

        # Low confidence -> force manual (threshold from constraints or default 0.5)
        # Exception: auto_full mode bypasses confidence floor — fully autonomous
        if confidence < min_confidence_floor and automation_mode != AutomationMode.AUTO_FULL:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "reason": f"Low confidence ({confidence:.0%}, floor={min_confidence_floor:.0%}) -- requires manual review",
                "parallel_tasks": [],
            }

        # CRITICAL -> always manual
        if technique_risk == RiskLevel.CRITICAL:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "reason": "Critical risk -- requires manual authorization",
                "parallel_tasks": [],
            }

        # HIGH -> auto-approve if threshold allows, otherwise HexConfirmModal
        if technique_risk == RiskLevel.HIGH:
            if threshold_level >= _RISK_ORDER.get(RiskLevel.HIGH, 2):
                pass  # Fall through to normal matrix/auto-approve logic below
            else:
                return {
                    **base,
                    "auto_approved": False,
                    "needs_confirmation": True,
                    "needs_manual": False,
                    "reason": "High risk -- requires HexConfirmModal confirmation",
                    "parallel_tasks": [],
                }

        # Threshold bypass: if technique risk is within the operator's accepted
        # threshold, auto-approve without consulting the NR1 matrix.
        # CRITICAL is already handled above (always manual).
        if tech_level <= threshold_level:
            return {
                **base,
                "auto_approved": True,
                "needs_confirmation": False,
                "needs_manual": False,
                "reason": f"Risk ({technique_risk.value}) within threshold ({risk_threshold})",
                "parallel_tasks": parallel_tasks,
            }

        # NR1: Matrix says needs_confirmation — override auto-approve
        if nr_decision is False:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "reason": (
                    f"Noise×Risk matrix ({mission_code}): "
                    f"noise={technique_noise}, risk={technique_risk.value} "
                    f"— requires confirmation"
                ),
                "parallel_tasks": [],
            }

        # Above threshold (e.g. MEDIUM when threshold is LOW) -> needs commander approval
        return {
            **base,
            "auto_approved": False,
            "needs_confirmation": True,
            "needs_manual": False,
            "reason": (
                f"Risk ({technique_risk.value}) exceeds threshold ({risk_threshold})"
                " -- requires commander approval"
            ),
            "parallel_tasks": [],
        }

    # -- Composite confidence helpers (SPEC-040) --

    async def _compute_composite_confidence(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        technique_id: str,
        target_id: str | None,
        raw_confidence: float,
        tactic_id: str | None,
    ) -> tuple[float, dict]:
        """Five-source composite confidence + Kill Chain penalty (SPEC-048)."""
        raw_confidence = max(0.0, min(1.0, raw_confidence))

        hist_rate = await self._get_historical_success_rate(db, technique_id)
        graph_conf = await self._get_graph_node_confidence(
            db, operation_id, technique_id, target_id
        )
        target_score = await self._get_target_state_score(db, target_id)

        # SPEC-048: OPSEC confidence factor
        try:
            from app.services.opsec_monitor import (
                compute_opsec_confidence_factor,
                compute_status as _opsec_status,
            )
            _ost = await _opsec_status(db, operation_id)
            opsec_factor = compute_opsec_confidence_factor(_ost.detection_risk)
        except Exception:
            opsec_factor = 1.0  # graceful degradation

        kc_result = await self._enforcer.evaluate_skip(
            db, operation_id, tactic_id, target_id
        )

        composite = (
            0.25 * raw_confidence
            + 0.25 * hist_rate
            + 0.20 * graph_conf
            + 0.15 * target_score
            + 0.15 * opsec_factor
            - kc_result.penalty
        )
        composite = max(0.0, min(1.0, composite))

        breakdown = {
            "llm": raw_confidence,
            "historical": hist_rate,
            "graph": graph_conf,
            "target_state": target_score,
            "opsec_factor": opsec_factor,
            "kc_penalty": kc_result.penalty,
        }
        return composite, breakdown

    async def _get_historical_success_rate(
        self, db: asyncpg.Connection, technique_id: str
    ) -> float:
        """Query success rate from technique_executions for the given technique."""
        row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes "
            "FROM technique_executions WHERE technique_id = $1",
            technique_id,
        )
        total = row["total"] if isinstance(row, dict) else row[0]
        successes = row["successes"] if isinstance(row, dict) else row[1]
        if not total:
            return 0.5  # No history -> neutral
        return (successes or 0) / total

    async def _get_graph_node_confidence(
        self, db: asyncpg.Connection,
        operation_id: str, technique_id: str, target_id: str | None,
    ) -> float:
        """Read node confidence from attack_graph_nodes."""
        if not target_id:
            return 0.5
        row = await db.fetchrow(
            "SELECT confidence FROM attack_graph_nodes "
            "WHERE operation_id = $1 AND technique_id = $2 AND target_id = $3 "
            "ORDER BY updated_at DESC LIMIT 1",
            operation_id, technique_id, target_id,
        )
        if not row:
            return 0.5
        return row["confidence"] if isinstance(row, dict) else row[0]

    async def _get_target_state_score(
        self, db: asyncpg.Connection, target_id: str | None,
    ) -> float:
        """Compute target state score from targets + facts tables."""
        if not target_id:
            return 0.5
        row = await db.fetchrow(
            "SELECT is_compromised, privilege_level, access_status "
            "FROM targets WHERE id = $1",
            target_id,
        )
        if not row:
            return 0.5

        is_compromised = row["is_compromised"] if isinstance(row, dict) else row[0]
        privilege = (
            (row["privilege_level"] if isinstance(row, dict) else row[1]) or ""
        )
        access_status = (
            (row["access_status"] if isinstance(row, dict) else row[2]) or ""
        )

        score = 0.5
        if is_compromised:
            score += 0.2
        if privilege.lower() in ("root", "system", "administrator"):
            score += 0.15
        if access_status == "lost":
            score -= 0.1

        # EDR detection from facts table
        edr_row = await db.fetchrow(
            "SELECT COUNT(*) FROM facts "
            "WHERE source_target_id = $1 AND trait IN ('host.edr', 'host.av')",
            target_id,
        )
        edr_count = edr_row[0] if edr_row else 0
        if edr_count > 0:
            score -= 0.2

        return max(0.0, min(1.0, score))

    async def _get_technique_noise_level(
        self, db: asyncpg.Connection, technique_id: str,
    ) -> str:
        """Look up noise_level from techniques table, default 'medium'."""
        row = await db.fetchrow(
            "SELECT noise_level FROM techniques WHERE id = $1",
            technique_id,
        )
        if row and row["noise_level"]:
            return row["noise_level"]
        return "medium"

    async def _get_mission_code(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> str:
        """Look up mission_profile from operations table, default 'SP'."""
        row = await db.fetchrow(
            "SELECT mission_profile FROM operations WHERE id = $1",
            operation_id,
        )
        if row and row["mission_profile"]:
            return row["mission_profile"]
        return "SP"

    async def _resolve_tactic_id(
        self, db: asyncpg.Connection,
        operation_id: str, technique_id: str, target_id: str | None,
    ) -> str | None:
        """Resolve tactic_id from attack_graph_nodes, falling back to _RULE_BY_TECHNIQUE."""
        if target_id:
            row = await db.fetchrow(
                "SELECT tactic_id FROM attack_graph_nodes "
                "WHERE operation_id = $1 AND technique_id = $2 AND target_id = $3 "
                "LIMIT 1",
                operation_id, technique_id, target_id,
            )
            if row:
                return row["tactic_id"] if isinstance(row, dict) else row[0]
        # Fallback to static rule table
        from app.services.attack_graph_engine import _RULE_BY_TECHNIQUE  # noqa: PLC0415
        rule = _RULE_BY_TECHNIQUE.get(technique_id)
        return rule.tactic_id if rule else None

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Decide phase — evaluate recommendation against risk thresholds."""

import logging

import aiosqlite

from app.models.enums import AutomationMode, RiskLevel

logger = logging.getLogger(__name__)

# Risk level ordering for comparison
_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


class DecisionEngine:
    """Decide phase: apply ADR-004 risk threshold rules to PentestGPT recommendation."""

    async def evaluate(
        self, db: aiosqlite.Connection, operation_id: str, recommendation: dict
    ) -> dict:
        """
        Decision logic per ADR-004:
        - MANUAL mode        → always auto_approved=False
        - confidence < 0.5   → force manual review
        - CRITICAL            → auto_approved=False, needs_manual=True
        - HIGH                → auto_approved=False, needs_confirmation=True (HexConfirmModal)
        - MEDIUM above thresh → auto_approved=False, needs_confirmation=True (queue + approve)
        - MEDIUM within thresh→ auto_approved=True (auto-queue)
        - LOW                 → auto_approved=True (auto-execute)
        """
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT automation_mode, risk_threshold FROM operations WHERE id = ?",
            (operation_id,),
        )
        op = await cursor.fetchone()
        if not op:
            return {"error": "operation not found", "auto_approved": False}

        automation_mode = op["automation_mode"] or "semi_auto"
        risk_threshold = op["risk_threshold"] or "medium"

        # Get recommended technique's risk level
        rec_technique_id = recommendation.get("recommended_technique_id", "")
        options = recommendation.get("options", [])
        confidence = recommendation.get("confidence", 0.0)

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
        cursor = await db.execute(
            "SELECT id FROM targets WHERE operation_id = ? AND is_active = 1 LIMIT 1",
            (operation_id,),
        )
        target_row = await cursor.fetchone()
        if not target_row:
            # Fall back to original heuristic
            cursor = await db.execute(
                "SELECT id FROM targets WHERE operation_id = ? ORDER BY is_compromised DESC LIMIT 1",
                (operation_id,),
            )
            target_row = await cursor.fetchone()
        target_id = target_row["id"] if target_row else None

        # Semi-auto: apply risk threshold rules
        tech_level = _RISK_ORDER.get(technique_risk, 1)
        threshold_level = _RISK_ORDER.get(RiskLevel(risk_threshold), 1)

        # Build parallel_tasks from all auto-approvable options (SPEC-030)
        parallel_tasks: list[dict] = []
        if automation_mode != AutomationMode.MANUAL and confidence >= 0.5:
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

        base = {
            "technique_id": rec_technique_id,
            "target_id": target_id,
            "engine": engine,
            "risk_level": technique_risk.value,
        }

        # MANUAL mode → always require human approval
        if automation_mode == AutomationMode.MANUAL:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "reason": "Manual mode — all decisions require commander approval",
                "parallel_tasks": [],
            }

        # Low confidence → force manual
        if confidence < 0.5:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "reason": f"Low confidence ({confidence:.0%}) — requires manual review",
                "parallel_tasks": [],
            }

        # CRITICAL → always manual
        if technique_risk == RiskLevel.CRITICAL:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "reason": "Critical risk — requires manual authorization",
                "parallel_tasks": [],
            }

        # HIGH → HexConfirmModal confirmation
        if technique_risk == RiskLevel.HIGH:
            return {
                **base,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "reason": "High risk — requires HexConfirmModal confirmation",
                "parallel_tasks": [],
            }

        # Within threshold → auto-approve
        if tech_level <= threshold_level:
            return {
                **base,
                "auto_approved": True,
                "needs_confirmation": False,
                "needs_manual": False,
                "reason": f"Risk ({technique_risk.value}) within threshold ({risk_threshold})",
                "parallel_tasks": parallel_tasks,
            }

        # Above threshold (e.g. MEDIUM when threshold is LOW) → needs commander approval
        return {
            **base,
            "auto_approved": False,
            "needs_confirmation": True,
            "needs_manual": False,
            "reason": (
                f"Risk ({technique_risk.value}) exceeds threshold ({risk_threshold})"
                " — requires commander approval"
            ),
            "parallel_tasks": [],
        }

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
        - LOW (< threshold)  → auto_approve=True
        - MEDIUM             → auto_approve=True, needs_queue=True
        - HIGH               → auto_approve=False, needs_confirm=True
        - CRITICAL           → auto_approve=False, needs_manual=True
        - MANUAL mode        → always auto_approved=False
        - confidence < 0.5   → force manual review
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
        engine = (selected_option or {}).get("recommended_engine", "caldera")

        # Find target — use first available compromised or first target
        cursor = await db.execute(
            "SELECT id FROM targets WHERE operation_id = ? ORDER BY is_compromised DESC LIMIT 1",
            (operation_id,),
        )
        target_row = await cursor.fetchone()
        target_id = target_row["id"] if target_row else None

        # MANUAL mode → always require human approval
        if automation_mode == AutomationMode.MANUAL:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "risk_level": technique_risk.value,
                "reason": "Manual mode — all decisions require commander approval",
            }

        # Low confidence → force manual
        if confidence < 0.5:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "risk_level": technique_risk.value,
                "reason": f"Low confidence ({confidence:.0%}) — requires manual review",
            }

        # Semi-auto: apply risk threshold rules
        tech_level = _RISK_ORDER.get(technique_risk, 1)
        threshold_level = _RISK_ORDER.get(RiskLevel(risk_threshold), 1)

        if technique_risk == RiskLevel.CRITICAL:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": True,
                "risk_level": technique_risk.value,
                "reason": "Critical risk — requires manual authorization",
            }

        if technique_risk == RiskLevel.HIGH:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "auto_approved": False,
                "needs_confirmation": True,
                "needs_manual": False,
                "risk_level": technique_risk.value,
                "reason": "High risk — requires HexConfirmModal confirmation",
            }

        if tech_level <= threshold_level:
            return {
                "technique_id": rec_technique_id,
                "target_id": target_id,
                "engine": engine,
                "auto_approved": True,
                "needs_confirmation": False,
                "needs_manual": False,
                "risk_level": technique_risk.value,
                "reason": f"Risk ({technique_risk.value}) within threshold ({risk_threshold})",
            }

        # MEDIUM above threshold
        return {
            "technique_id": rec_technique_id,
            "target_id": target_id,
            "engine": engine,
            "auto_approved": True,
            "needs_confirmation": False,
            "needs_manual": False,
            "risk_level": technique_risk.value,
            "reason": f"Medium risk — auto-approved with queue",
        }

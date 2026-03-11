# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Constraint Engine — reads C5ISR health + OPSEC state → OperationalConstraints.

Called at the start of each OODA cycle to produce constraints that govern
Orient, Decide, and ACT phases.  See ADR-040 for design rationale.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from app.models.constraint import (
    ConstraintLimit,
    ConstraintWarning,
    OperationalConstraints,
)
from app.services.mission_profile_loader import get_profile

logger = logging.getLogger(__name__)

# ── Per-domain reaction rules ──────────────────────────────────────────────
# Each entry maps domain → (warning_reaction_fn, critical_reaction_fn).
# Functions mutate the OperationalConstraints in-place.

_C5ISR_DOMAINS = ("command", "control", "comms", "computers", "cyber", "isr")


def _react_command_warning(c: OperationalConstraints, health: float) -> None:
    c.orient_max_options = min(c.orient_max_options, 2)
    c.warnings.append(ConstraintWarning(
        domain="command", health_pct=health,
        message="Command health degraded — Orient options reduced to 2",
    ))


def _react_command_critical(c: OperationalConstraints, health: float) -> None:
    c.orient_max_options = 1
    c.hard_limits.append(ConstraintLimit(
        domain="command", health_pct=health,
        rule="orient_single_option",
        effect={"orient_max_options": 1, "medium_risk_auto_approve": True},
        suggested_action="Review and accept/reject pending recommendations to restore decision throughput",
    ))


def _react_control_warning(c: OperationalConstraints, health: float) -> None:
    c.warnings.append(ConstraintWarning(
        domain="control", health_pct=health,
        message="Control health degraded — prioritise persistence/recovery techniques",
    ))


def _react_control_critical(c: OperationalConstraints, health: float) -> None:
    c.forced_mode = "recovery"
    c.hard_limits.append(ConstraintLimit(
        domain="control", health_pct=health,
        rule="forced_recovery_mode",
        effect={"forced_mode": "recovery", "block_lost_targets": True},
        suggested_action="Re-establish access to lost targets via persistence or new initial access",
    ))


def _react_comms_warning(c: OperationalConstraints, health: float) -> None:
    c.warnings.append(ConstraintWarning(
        domain="comms", health_pct=health,
        message="Comms health degraded — excluding unavailable engines",
    ))


def _react_comms_critical(c: OperationalConstraints, health: float) -> None:
    c.max_parallel_override = 1
    c.hard_limits.append(ConstraintLimit(
        domain="comms", health_pct=health,
        rule="single_execution_mode",
        effect={"max_parallel": 1},
        suggested_action="Check MCP server connectivity and restart failed engine containers",
    ))


def _react_computers_warning(c: OperationalConstraints, health: float) -> None:
    c.warnings.append(ConstraintWarning(
        domain="computers", health_pct=health,
        message="Penetration rate stalled — deprioritising failed targets",
    ))


def _react_computers_critical(c: OperationalConstraints, health: float) -> None:
    c.forced_mode = c.forced_mode or "recon_first"
    c.hard_limits.append(ConstraintLimit(
        domain="computers", health_pct=health,
        rule="recon_first_mode",
        effect={"forced_mode": "recon_first"},
        suggested_action="Run recon on new targets or try alternative attack vectors on failed targets",
    ))


def _react_cyber_warning(c: OperationalConstraints, health: float) -> None:
    if c.min_confidence_override is None:
        c.min_confidence_override = 0.0
    c.min_confidence_override = max(c.min_confidence_override, 0.15)
    c.warnings.append(ConstraintWarning(
        domain="cyber", health_pct=health,
        message="Cyber efficiency degraded — min_confidence raised by 0.15",
    ))


def _react_cyber_critical(c: OperationalConstraints, health: float) -> None:
    c.min_confidence_override = 0.75
    c.hard_limits.append(ConstraintLimit(
        domain="cyber", health_pct=health,
        rule="high_confidence_only",
        effect={"min_confidence": 0.75},
        suggested_action="Focus on high-confidence techniques; review failed executions for root cause",
    ))


def _react_isr_warning(c: OperationalConstraints, health: float) -> None:
    c.warnings.append(ConstraintWarning(
        domain="isr", health_pct=health,
        message="ISR coverage low — targets with sparse intel get confidence penalty",
    ))


def _react_isr_critical(c: OperationalConstraints, health: float) -> None:
    c.hard_limits.append(ConstraintLimit(
        domain="isr", health_pct=health,
        rule="block_low_intel_targets",
        effect={"min_facts_per_target": 3},
        suggested_action="Run recon/OSINT on blocked targets to collect at least 3 intelligence facts",
    ))


_WARNING_REACTIONS = {
    "command": _react_command_warning,
    "control": _react_control_warning,
    "comms": _react_comms_warning,
    "computers": _react_computers_warning,
    "cyber": _react_cyber_warning,
    "isr": _react_isr_warning,
}

_CRITICAL_REACTIONS = {
    "command": _react_command_critical,
    "control": _react_control_critical,
    "comms": _react_comms_critical,
    "computers": _react_computers_critical,
    "cyber": _react_cyber_critical,
    "isr": _react_isr_critical,
}


async def evaluate(
    db: asyncpg.Connection,
    operation_id: str,
    mission_code: str = "SP",
    ws_manager: Any | None = None,
) -> OperationalConstraints:
    """Produce OperationalConstraints for the current OODA cycle.

    Steps:
    1. Load mission profile thresholds
    2. Read current C5ISR domain health
    3. Read active overrides (skip overridden domains)
    4. Compare health vs thresholds → fire reactions
    5. Read OPSEC noise budget status
    """
    profile = get_profile(mission_code)
    thresholds = profile.get("c5isr_thresholds", {})
    constraints = OperationalConstraints(
        orient_max_options=profile.get("orient_max_options", 3),
        noise_budget_remaining=profile.get("noise_budget_10min", 50),
    )

    # 1. Read C5ISR domain health
    rows = await db.fetch(
        "SELECT domain, health_pct FROM c5isr_statuses WHERE operation_id = $1",
        operation_id,
    )
    domain_health: dict[str, float] = {r["domain"]: float(r["health_pct"] or 100) for r in rows}

    # 2. Read active overrides (single-round, stored in event_store)
    override_rows = await db.fetch(
        """SELECT payload->>'domain' AS domain
           FROM event_store
           WHERE operation_id = $1
             AND event_type = 'constraint.override'
             AND created_at > NOW() - INTERVAL '10 minutes'
           ORDER BY created_at DESC""",
        operation_id,
    )
    active_overrides = {r["domain"] for r in override_rows if r["domain"]}
    constraints.active_overrides = list(active_overrides)

    # Detect recently-expired overrides (expired in last 2 minutes) and broadcast
    if ws_manager is not None:
        try:
            expired_rows = await db.fetch(
                """SELECT DISTINCT payload->>'domain' AS domain
                   FROM event_store
                   WHERE operation_id = $1
                     AND event_type = 'constraint.override'
                     AND created_at <= NOW() - INTERVAL '10 minutes'
                     AND created_at > NOW() - INTERVAL '12 minutes'""",
                operation_id,
            )
            expired_domains = {r["domain"] for r in expired_rows if r["domain"]}
            newly_expired = expired_domains - active_overrides
            if newly_expired:
                await ws_manager.broadcast(
                    operation_id, "constraint.override_expired",
                    {"domains": list(newly_expired)},
                )
        except Exception as exc:
            logger.warning("Failed to check expired overrides: %s", exc)

    # 3. Check each domain against thresholds
    for domain in _C5ISR_DOMAINS:
        health = domain_health.get(domain, 100.0)
        domain_thresholds = thresholds.get(domain, {})
        warning_threshold = domain_thresholds.get("warning", 50)
        critical_threshold = domain_thresholds.get("critical", 25)

        if domain in active_overrides:
            logger.info(
                "Domain %s overridden for operation %s (health=%.1f)",
                domain, operation_id, health,
            )
            continue

        if health <= critical_threshold:
            fn = _CRITICAL_REACTIONS.get(domain)
            if fn:
                fn(constraints, health)
        elif health <= warning_threshold:
            fn = _WARNING_REACTIONS.get(domain)
            if fn:
                fn(constraints, health)

    # 4. ISR critical: block targets with insufficient facts
    if any(hl.rule == "block_low_intel_targets" for hl in constraints.hard_limits):
        sparse_rows = await db.fetch(
            """SELECT t.id FROM targets t
               LEFT JOIN facts f ON f.target_id = t.id AND f.operation_id = $1
               WHERE t.operation_id = $1
               GROUP BY t.id
               HAVING COUNT(f.id) < 3""",
            operation_id,
        )
        constraints.blocked_targets.extend(r["id"] for r in sparse_rows)

    # 5. Control critical: block lost-access targets
    if constraints.is_recovery_mode:
        lost_rows = await db.fetch(
            "SELECT id FROM targets WHERE operation_id = $1 AND access_status = 'lost'",
            operation_id,
        )
        constraints.blocked_targets.extend(r["id"] for r in lost_rows)

    # 6. OPSEC noise budget
    noise_row = await db.fetchrow(
        """SELECT COALESCE(SUM(noise_points), 0) AS total_noise
           FROM opsec_events
           WHERE operation_id = $1
             AND created_at > NOW() - INTERVAL '10 minutes'""",
        operation_id,
    )
    if noise_row:
        budget_total = profile.get("noise_budget_10min", 50)
        used = int(noise_row["total_noise"])
        if budget_total > 0:
            constraints.noise_budget_remaining = max(0, budget_total - used)
        else:
            constraints.noise_budget_remaining = 999  # unlimited

    logger.info(
        "Constraints for %s (%s): %d warnings, %d hard_limits, blocked=%d targets",
        operation_id, mission_code,
        len(constraints.warnings), len(constraints.hard_limits),
        len(constraints.blocked_targets),
    )
    return constraints

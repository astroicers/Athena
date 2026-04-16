# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""OPSEC Monitor — tracks noise, exposure, artifacts, and detection risk.

Called after each ACT phase to evaluate the operation's OPSEC posture.
See ADR-040 §D6 for design rationale.
"""

from __future__ import annotations

import logging
import math
from typing import Any
from uuid import uuid4

import asyncpg

from app.models.opsec import OPSECEvent, OPSECStatus
from app.models.enums import NOISE_POINTS
from app.services.mission_profile_loader import get_profile

logger = logging.getLogger(__name__)

# ── Noise point values per noise_level ────────────────────────────────────
_NOISE_POINTS = NOISE_POINTS

# ── Detection risk weights ────────────────────────────────────────────────
_W_NOISE = 0.35
_W_DWELL = 0.25
_W_EXPOSURE = 0.25
_W_ARTIFACT = 0.15


async def record_event(
    db: asyncpg.Connection,
    operation_id: str,
    event_type: str,
    *,
    severity: str = "warning",
    detail: dict[str, Any] | None = None,
    target_id: str | None = None,
    technique_id: str | None = None,
    noise_points: int = 0,
) -> str:
    """Insert an OPSEC event and return its ID."""
    event_id = str(uuid4())
    import json
    await db.execute(
        """INSERT INTO opsec_events
           (id, operation_id, event_type, severity, detail, target_id, technique_id, noise_points)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        event_id, operation_id, event_type, severity,
        json.dumps(detail or {}),
        target_id, technique_id, noise_points,
    )
    return event_id


async def evaluate_after_act(
    db: asyncpg.Connection,
    operation_id: str,
    technique_noise: str = "medium",
    target_id: str | None = None,
    technique_id: str | None = None,
    execution_success: bool = True,
) -> OPSECStatus:
    """Evaluate OPSEC state after an ACT execution.

    1. Record noise from the execution
    2. Check for burst patterns
    3. Calculate composite detection_risk
    4. Return aggregated OPSECStatus
    """
    noise_pts = _NOISE_POINTS.get(technique_noise, 3)

    # Record the execution noise
    await record_event(
        db, operation_id, "execution_noise",
        severity="info" if technique_noise == "low" else "warning",
        detail={"noise_level": technique_noise, "success": execution_success},
        target_id=target_id,
        technique_id=technique_id,
        noise_points=noise_pts,
    )

    # Check for burst (>5 ops in 10 min)
    burst_count = await db.fetchval(
        """SELECT COUNT(*) FROM opsec_events
           WHERE operation_id = $1 AND created_at > NOW() - INTERVAL '10 minutes'""",
        operation_id,
    )
    if burst_count and burst_count > 5:
        await record_event(
            db, operation_id, "burst",
            severity="warning",
            detail={"ops_in_10min": burst_count},
            noise_points=1,
        )

    # Record auth failure events
    if not execution_success:
        await record_event(
            db, operation_id, "auth_failure",
            severity="warning",
            detail={"technique_id": technique_id},
            target_id=target_id,
            noise_points=1,
        )

    return await compute_status(db, operation_id)


async def compute_status(
    db: asyncpg.Connection,
    operation_id: str,
) -> OPSECStatus:
    """Calculate the full OPSEC status from stored events."""

    # 1. Noise score (10-min sliding window)
    noise_row = await db.fetchrow(
        """SELECT COALESCE(SUM(noise_points), 0) AS total,
                  COUNT(*) AS event_count
           FROM opsec_events
           WHERE operation_id = $1 AND created_at > NOW() - INTERVAL '10 minutes'""",
        operation_id,
    )
    total_noise = int(noise_row["total"]) if noise_row else 0
    noise_score = min(100.0, total_noise * 2.0)  # scale: 50 pts = 100%

    # 2. Dwell time score
    dwell_row = await db.fetchrow(
        """SELECT MIN(te.started_at) AS first_access
           FROM technique_executions te
           WHERE te.operation_id = $1 AND te.status = 'success'""",
        operation_id,
    )
    dwell_minutes = 0.0
    if dwell_row and dwell_row["first_access"]:
        dwell_row2 = await db.fetchrow(
            "SELECT EXTRACT(EPOCH FROM NOW() - $1) / 60.0 AS mins",
            dwell_row["first_access"],
        )
        dwell_minutes = float(dwell_row2["mins"]) if dwell_row2 else 0.0
    # Normalize: 0 min=0%, 120 min=100%
    dwell_score = min(100.0, (dwell_minutes / 120.0) * 100.0)

    # 3. Exposure count
    exposure_row = await db.fetchrow(
        """SELECT COUNT(*) AS cnt FROM opsec_events
           WHERE operation_id = $1
             AND event_type IN ('auth_failure', 'high_noise', 'burst', 'detection')""",
        operation_id,
    )
    exposure_count = int(exposure_row["cnt"]) if exposure_row else 0
    exposure_score = min(100.0, exposure_count * 10.0)

    # 4. Artifact footprint (estimate from technique types)
    artifact_row = await db.fetchrow(
        """SELECT COUNT(*) AS cnt FROM technique_executions te
           JOIN techniques t ON t.mitre_id = te.technique_id
           WHERE te.operation_id = $1 AND te.status = 'success'
             AND t.tactic IN ('Persistence', 'Defense Evasion')""",
        operation_id,
    )
    artifact_count = int(artifact_row["cnt"]) if artifact_row else 0
    artifact_score = min(100.0, artifact_count * 20.0)

    # 5. Composite detection risk
    detection_risk = (
        _W_NOISE * noise_score
        + _W_DWELL * dwell_score
        + _W_EXPOSURE * exposure_score
        + _W_ARTIFACT * artifact_score
    )

    # Get mission profile for budget info
    op_row = await db.fetchrow(
        "SELECT mission_profile FROM operations WHERE id = $1", operation_id,
    )
    mission_code = op_row["mission_profile"] if op_row and op_row["mission_profile"] else "SP"
    profile = get_profile(mission_code)
    budget_total = profile.get("noise_budget_10min", 50)
    budget_remaining = max(0, budget_total - total_noise) if budget_total > 0 else 999

    # Recent events
    recent_rows = await db.fetch(
        """SELECT id, event_type, severity, noise_points, created_at
           FROM opsec_events
           WHERE operation_id = $1
           ORDER BY created_at DESC LIMIT 10""",
        operation_id,
    )

    return OPSECStatus(
        operation_id=operation_id,
        noise_score=round(noise_score, 1),
        dwell_time_score=round(dwell_score, 1),
        exposure_count=exposure_count,
        artifact_footprint=round(artifact_score, 1),
        detection_risk=round(detection_risk, 1),
        noise_budget_total=budget_total,
        noise_budget_used=total_noise,
        noise_budget_remaining=budget_remaining,
        recent_events=[
            OPSECEvent(
                id=r["id"],
                operation_id=operation_id,
                event_type=r["event_type"],
                severity=r["severity"],
                noise_points=r["noise_points"] or 0,
                created_at=r["created_at"],
            )
            for r in recent_rows
        ],
    )


def compute_opsec_penalty(detection_risk: float) -> float:
    """Return the C5ISR health multiplier based on detection_risk.

    >60 → 0.85, >80 → 0.70
    """
    if detection_risk > 80:
        return 0.70
    if detection_risk > 60:
        return 0.85
    return 1.0


def compute_opsec_confidence_factor(detection_risk: float) -> float:
    """Return the opsec_factor for composite confidence scoring.

    risk<30 → 1.0, 30-60 → 0.7, 60-80 → 0.4, >80 → 0.1
    """
    if detection_risk > 80:
        return 0.1
    if detection_risk > 60:
        return 0.4
    if detection_risk > 30:
        return 0.7
    return 1.0

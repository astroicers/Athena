# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Threat Level Computer — real-time threat_level for operations.

threat_level = weighted(
    opsec_noise * 0.35 +
    auth_failures * 0.25 +
    detection_events * 0.25 +
    dwell_exposure * 0.15
)

Triggered after each OPSEC event + C5ISR update.
"""

from __future__ import annotations

import logging

import asyncpg

from app.models.opsec import ThreatLevel

logger = logging.getLogger(__name__)


async def compute_threat_level(
    db: asyncpg.Connection,
    operation_id: str,
) -> ThreatLevel:
    """Compute and store the current threat_level for an operation."""

    # 1. OPSEC noise (10-min window)
    noise_row = await db.fetchrow(
        """SELECT COALESCE(SUM(noise_points), 0) AS total
           FROM opsec_events
           WHERE operation_id = $1 AND created_at > NOW() - INTERVAL '10 minutes'""",
        operation_id,
    )
    noise_total = int(noise_row["total"]) if noise_row else 0
    noise_factor = min(1.0, noise_total / 50.0)

    # 2. Auth failures (all time)
    auth_row = await db.fetchrow(
        """SELECT COUNT(*) AS cnt FROM opsec_events
           WHERE operation_id = $1 AND event_type = 'auth_failure'""",
        operation_id,
    )
    auth_count = int(auth_row["cnt"]) if auth_row else 0
    auth_factor = min(1.0, auth_count / 20.0)

    # 3. Detection events
    detect_row = await db.fetchrow(
        """SELECT COUNT(*) AS cnt FROM opsec_events
           WHERE operation_id = $1 AND event_type = 'detection'""",
        operation_id,
    )
    detect_count = int(detect_row["cnt"]) if detect_row else 0
    detect_factor = min(1.0, detect_count / 5.0)

    # 4. Dwell exposure
    dwell_row = await db.fetchrow(
        """SELECT EXTRACT(EPOCH FROM NOW() - MIN(te.started_at)) / 3600.0 AS hours
           FROM technique_executions te
           WHERE te.operation_id = $1 AND te.status = 'success'""",
        operation_id,
    )
    dwell_hours = float(dwell_row["hours"]) if dwell_row and dwell_row["hours"] else 0.0
    dwell_factor = min(1.0, dwell_hours / 24.0)

    # Composite
    level = (
        0.35 * noise_factor
        + 0.25 * auth_factor
        + 0.25 * detect_factor
        + 0.15 * dwell_factor
    )
    level = round(min(1.0, max(0.0, level)), 3)

    # Update operations table
    await db.execute(
        "UPDATE operations SET threat_level = $1 WHERE id = $2",
        level, operation_id,
    )

    return ThreatLevel(
        operation_id=operation_id,
        level=level,
        components={
            "opsec_noise": round(noise_factor, 3),
            "auth_failures": round(auth_factor, 3),
            "detection_events": round(detect_factor, 3),
            "dwell_exposure": round(dwell_factor, 3),
        },
    )

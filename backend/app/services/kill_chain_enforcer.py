# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Kill Chain Enforcer — skip-stage penalty calculator.

SPEC-040 / ADR-037 Option C: penalise recommendations that skip required
Kill Chain stages, reducing composite confidence to trigger manual review.
"""

import logging
from dataclasses import dataclass, field

import asyncpg

logger = logging.getLogger(__name__)

# Kill Chain stages mapped to MITRE ATT&CK tactics
_KILL_CHAIN_STAGES: list[tuple[int, str, str, bool]] = [
    # (stage, tactic_id, name, required)
    (0,  "TA0043", "Reconnaissance",        True),
    (1,  "TA0042", "Resource Development",  False),
    (2,  "TA0001", "Initial Access",        True),
    (3,  "TA0002", "Execution",             True),
    (4,  "TA0003", "Persistence",           False),
    (5,  "TA0004", "Privilege Escalation",  True),
    (6,  "TA0005", "Defense Evasion",       False),
    (7,  "TA0006", "Credential Access",     True),
    (8,  "TA0007", "Discovery",             True),
    (9,  "TA0008", "Lateral Movement",      True),
    (10, "TA0009", "Collection",            True),
    (11, "TA0011", "Command and Control",   False),
    (12, "TA0010", "Exfiltration",          True),
    (13, "TA0040", "Impact",               True),
]

_TACTIC_TO_STAGE: dict[str, int] = {t[1]: t[0] for t in _KILL_CHAIN_STAGES}
_TACTIC_TO_NAME: dict[str, str] = {t[1]: t[2] for t in _KILL_CHAIN_STAGES}
_TACTIC_REQUIRED: dict[str, bool] = {t[1]: t[3] for t in _KILL_CHAIN_STAGES}

_PENALTY_PER_SKIP = 0.05
_MAX_PENALTY = 0.25


@dataclass
class KillChainPenalty:
    penalty: float = 0.0
    skipped_stages: list[str] = field(default_factory=list)
    warning: str | None = None


class KillChainEnforcer:
    """Calculate confidence penalty when a recommendation skips required Kill Chain stages."""

    async def evaluate_skip(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        tactic_id: str | None,
        target_id: str | None,
    ) -> KillChainPenalty:
        """Evaluate whether the recommended tactic skips required predecessor stages.

        Steps:
        1. Query completed tactics for this operation + target
        2. Identify required stages before the recommended tactic that are incomplete
        3. Calculate penalty (0.05 per skipped required stage, max 0.25)
        """
        if tactic_id is None or tactic_id not in _TACTIC_TO_STAGE:
            return KillChainPenalty()

        current_stage = _TACTIC_TO_STAGE[tactic_id]

        completed_tactics = await self._get_completed_tactics(
            db, operation_id, target_id
        )

        skipped: list[str] = []
        for stage, tid, name, required in _KILL_CHAIN_STAGES:
            if stage >= current_stage:
                break
            if not required:
                continue
            if tid not in completed_tactics:
                skipped.append(f"{tid} ({name})")

        penalty = min(len(skipped) * _PENALTY_PER_SKIP, _MAX_PENALTY)

        warning = None
        if skipped:
            tactic_name = _TACTIC_TO_NAME.get(tactic_id, "?")
            warning = (
                f"Kill Chain skip warning: recommending {tactic_id} ({tactic_name}) "
                f"but required stages not completed: {', '.join(skipped)}. "
                f"Confidence penalty: -{penalty:.2f}"
            )
            logger.warning(warning)

        return KillChainPenalty(
            penalty=penalty, skipped_stages=skipped, warning=warning
        )

    async def _get_completed_tactics(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str | None,
    ) -> set[str]:
        """Query successfully executed tactics for an operation + target.

        JOINs technique_executions with attack_graph_nodes to resolve
        technique_id -> tactic_id mapping.
        """
        if not target_id:
            rows = await db.fetch(
                "SELECT DISTINCT agn.tactic_id "
                "FROM technique_executions te "
                "JOIN attack_graph_nodes agn "
                "  ON te.technique_id = agn.technique_id "
                "  AND te.operation_id = agn.operation_id "
                "WHERE te.operation_id = $1 AND te.status = 'success'",
                operation_id,
            )
        else:
            rows = await db.fetch(
                "SELECT DISTINCT agn.tactic_id "
                "FROM technique_executions te "
                "JOIN attack_graph_nodes agn "
                "  ON te.technique_id = agn.technique_id "
                "  AND te.operation_id = agn.operation_id "
                "  AND te.target_id = agn.target_id "
                "WHERE te.operation_id = $1 AND te.target_id = $2 "
                "AND te.status = 'success'",
                operation_id, target_id,
            )
        completed_tactics = {r["tactic_id"] for r in rows}

        # Fallback: direct check for known recon technique IDs
        # (covers cases where attack_graph_nodes doesn't have T1046)
        recon_rows = await db.fetch(
            "SELECT 1 FROM technique_executions "
            "WHERE operation_id = $1 AND status = 'success' "
            "AND technique_id = ANY($2::text[])",
            operation_id, ["T1046", "T1595", "T1595.001", "T1590"],
        )
        if recon_rows:
            completed_tactics.add("TA0043")

        return completed_tactics

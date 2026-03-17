# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Agent capability matching for C2 execution engine selection.

Selects the best-fit alive agent on a target based on technique platform
requirements and agent privilege level (SYSTEM > Admin > User).

SPEC-022 / ADR-021
"""

import logging

import asyncpg

logger = logging.getLogger(__name__)

# Privilege rank — higher is better
_PRIVILEGE_RANK: dict[str, int] = {
    "system": 3,
    "admin": 2,
    "user": 1,
}


class AgentCapabilityMatcher:
    """Match a C2 agent to a technique based on platform + privilege."""

    async def select_agent_for_technique(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        technique_id: str,
    ) -> str | None:
        """Return the paw of the best-fit alive agent, or None.

        Selection rules (in order):
        1. Agent must be alive and on the correct target/operation.
        2. Agent platform must match technique platform (from technique_playbooks).
           If no playbook entry exists for the technique, platform filter is skipped.
        3. Among matching agents, prefer highest privilege (SYSTEM > Admin > User).
        """
        required_platform = await self._technique_platform(db, technique_id)

        if required_platform:
            rows = await db.fetch(
                "SELECT paw, privilege FROM agents "
                "WHERE host_id = $1 AND operation_id = $2 AND status = 'alive' "
                "AND LOWER(platform) = LOWER($3)",
                target_id, operation_id, required_platform,
            )
        else:
            rows = await db.fetch(
                "SELECT paw, privilege FROM agents "
                "WHERE host_id = $1 AND operation_id = $2 AND status = 'alive'",
                target_id, operation_id,
            )

        if not rows:
            return None

        def _rank(row) -> int:
            return _PRIVILEGE_RANK.get((row["privilege"] or "").lower(), 0)

        best = max(rows, key=_rank)
        return best["paw"]

    async def _technique_platform(
        self, db: asyncpg.Connection, technique_id: str
    ) -> str | None:
        """Return canonical platform ('windows' or 'linux') for technique, or None.

        If a technique has playbooks for multiple platforms, returns the
        lexicographically first platform (ORDER BY platform ensures stability).
        """
        row = await db.fetchrow(
            "SELECT DISTINCT LOWER(platform) AS platform "
            "FROM technique_playbooks WHERE mitre_id = $1 ORDER BY platform LIMIT 1",
            technique_id,
        )
        return row["platform"] if row else None

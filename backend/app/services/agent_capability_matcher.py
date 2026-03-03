# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Agent capability matching for C2 execution engine selection.

Selects the best-fit alive agent on a target based on technique platform
requirements and agent privilege level (SYSTEM > Admin > User).

SPEC-022 / ADR-021
"""

import logging

import aiosqlite

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
        db: aiosqlite.Connection,
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
        db.row_factory = aiosqlite.Row

        required_platform = await self._technique_platform(db, technique_id)

        if required_platform:
            cursor = await db.execute(
                "SELECT paw, privilege FROM agents "
                "WHERE host_id = ? AND operation_id = ? AND status = 'alive' "
                "AND LOWER(platform) = LOWER(?)",
                (target_id, operation_id, required_platform),
            )
        else:
            cursor = await db.execute(
                "SELECT paw, privilege FROM agents "
                "WHERE host_id = ? AND operation_id = ? AND status = 'alive'",
                (target_id, operation_id),
            )

        rows = await cursor.fetchall()
        if not rows:
            return None

        def _rank(row: aiosqlite.Row) -> int:
            return _PRIVILEGE_RANK.get((row["privilege"] or "").lower(), 0)

        best = max(rows, key=_rank)
        return best["paw"]

    async def _technique_platform(
        self, db: aiosqlite.Connection, technique_id: str
    ) -> str | None:
        """Return canonical platform ('windows' or 'linux') for technique, or None.

        If a technique has playbooks for multiple platforms, returns the
        lexicographically first platform (ORDER BY platform ensures stability).
        """
        cursor = await db.execute(
            "SELECT DISTINCT LOWER(platform) AS platform "
            "FROM technique_playbooks WHERE mitre_id = ? ORDER BY platform LIMIT 1",
            (technique_id,),
        )
        row = await cursor.fetchone()
        return row["platform"] if row else None

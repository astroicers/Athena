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

"""Act phase — route execution to C2 engine, DirectSSH, or Adaptive engine."""

import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.clients import BaseEngineClient, ExecutionResult
from app.config import settings
from app.services.fact_collector import FactCollector
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


class EngineRouter:
    """Act phase: route technique execution to the appropriate engine."""

    def __init__(
        self,
        c2_engine: BaseEngineClient,
        adaptive_engine: BaseEngineClient | None,
        fact_collector: FactCollector,
        ws_manager: WebSocketManager,
    ):
        self._c2_engine = c2_engine
        self._adaptive_engine = adaptive_engine
        self._fact_collector = fact_collector
        self._ws = ws_manager

    async def execute(
        self, db: aiosqlite.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """
        Execute a technique via the selected engine:
        1. Create TechniqueExecution record (status=running)
        2. Call C2EngineClient / DirectSSHEngine / AiEngineClient
        3. Update status (success/failed)
        4. Extract facts from result
        5. Push WebSocket execution.update event

        Quad-track routing (controlled by settings.EXECUTION_ENGINE):
        - "persistent_ssh": Use PersistentSSHChannelEngine (pooled sessions; Phase D)
        - "ssh"    : Use DirectSSHEngine with credential.ssh fact from DB
        - "caldera": Use C2EngineClient (requires alive agent; original path)
        - "mock"   : Use MockC2Client (MOCK_C2_ENGINE=true legacy path)
        """
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Get the technique's caldera_ability_id
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT mitre_id, caldera_ability_id FROM techniques WHERE mitre_id = ?",
            (technique_id,),
        )
        tech_row = await cursor.fetchone()
        ability_id = (tech_row["caldera_ability_id"] if tech_row else None) or technique_id

        # ── Metasploit route: exploit=true CVE fact → highest priority ────────
        # Check BEFORE SSH/Caldera routing (ADR-019)
        service = await self._has_exploitable_service(db, operation_id, target_id)
        if service:
            target_ip = await self._get_target_ip(db, target_id)
            if target_ip is None:
                logger.error(
                    "Cannot resolve IP for target %s — aborting Metasploit route",
                    target_id,
                )
            else:
                return await self._execute_metasploit(
                    db, exec_id, now, technique_id, target_id, operation_id,
                    ooda_iteration_id, service, target_ip, engine,
                )

        # ── Engine selection ──────────────────────────────────────────────────
        # Determine effective mode:
        #   EXECUTION_ENGINE="ssh"    → SSH path (no agent required)
        #   EXECUTION_ENGINE="caldera"→ Caldera path (alive agent required)
        #   EXECUTION_ENGINE="mock"   → mock path
        #   MOCK_C2_ENGINE=True         → treated as "mock" for backward compat
        #     UNLESS EXECUTION_ENGINE is explicitly "caldera" or "ssh"
        effective_mode = settings.EXECUTION_ENGINE  # "ssh" | "persistent_ssh" | "caldera" | "mock"
        if settings.MOCK_C2_ENGINE and effective_mode not in ("caldera", "ssh", "persistent_ssh"):
            # Legacy MOCK_C2_ENGINE=True overrides to mock when engine is ambiguous
            effective_mode = "mock"

        if effective_mode == "persistent_ssh":
            return await self._execute_persistent_ssh(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id,
            )
        elif effective_mode == "ssh":
            return await self._execute_ssh(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id,
            )
        elif effective_mode == "mock":
            return await self._execute_caldera(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id, require_agent=False,
            )
        else:
            # "caldera" mode — original path with alive-agent requirement
            return await self._execute_caldera(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id, require_agent=True,
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _execute_ssh(
        self,
        db: aiosqlite.Connection,
        exec_id: str,
        now: str,
        ability_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        ooda_iteration_id: str | None,
    ) -> dict:
        """SSH execution path — look up credential.ssh fact and call DirectSSHEngine."""
        # Look up SSH credentials from the facts table
        cursor = await db.execute(
            "SELECT value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? AND trait = 'credential.ssh' "
            "ORDER BY score DESC LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cursor.fetchone()

        if not cred_row:
            logger.warning(
                "No SSH credentials for target %s in operation %s", target_id, operation_id
            )
            return {
                "execution_id": exec_id,
                "technique_id": technique_id,
                "target_id": target_id,
                "engine": engine,
                "status": "failed",
                "result_summary": None,
                "facts_collected_count": 0,
                "error": f"No SSH credentials for target {target_id}",
            }

        credential_string = cred_row["value"]

        # Create execution record
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, engine, now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": engine,
        })

        # Import here to avoid circular imports at module load time
        from app.clients.direct_ssh_client import DirectSSHEngine  # noqa: PLC0415
        ssh_engine = DirectSSHEngine()
        result: ExecutionResult = await ssh_engine.execute(ability_id, credential_string)

        return await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )

    async def _execute_persistent_ssh(
        self,
        db: aiosqlite.Connection,
        exec_id: str,
        now: str,
        ability_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        ooda_iteration_id: str | None,
    ) -> dict:
        """Persistent SSH execution path — reuses session pool across techniques."""
        cursor = await db.execute(
            "SELECT value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? AND trait = 'credential.ssh' "
            "ORDER BY score DESC LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cursor.fetchone()

        if not cred_row:
            logger.warning(
                "No SSH credentials for target %s in operation %s", target_id, operation_id
            )
            return {
                "execution_id": exec_id,
                "technique_id": technique_id,
                "target_id": target_id,
                "engine": engine,
                "status": "failed",
                "result_summary": None,
                "facts_collected_count": 0,
                "error": f"No SSH credentials for target {target_id}",
            }

        credential_string = cred_row["value"]

        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, engine, now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": engine,
        })

        from app.clients.persistent_ssh_client import PersistentSSHChannelEngine  # noqa: PLC0415
        # PersistentSSHChannelEngine holds no per-instance state beyond operation_id.
        # The connection pool (_SESSION_POOL) is module-level, so creating a new instance
        # here reuses any existing SSH session for this operation.
        persistent_engine = PersistentSSHChannelEngine(operation_id=operation_id)
        result: ExecutionResult = await persistent_engine.execute(ability_id, credential_string)

        return await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )

    async def _execute_caldera(
        self,
        db: aiosqlite.Connection,
        exec_id: str,
        now: str,
        ability_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        ooda_iteration_id: str | None,
        *,
        require_agent: bool,
    ) -> dict:
        """C2 engine / mock execution path."""
        agent_paw: str | None = None

        if require_agent:
            # Get agent paw for the target — C2 engine needs the agent's paw, not hostname
            cursor = await db.execute(
                "SELECT paw FROM agents WHERE host_id = ? AND operation_id = ? "
                "AND status = 'alive' LIMIT 1",
                (target_id, operation_id),
            )
            agent_row = await cursor.fetchone()
            if not agent_row:
                logger.warning(
                    "No alive agent on target %s for operation %s", target_id, operation_id
                )
                return {
                    "execution_id": exec_id,
                    "technique_id": technique_id,
                    "target_id": target_id,
                    "engine": engine,
                    "status": "failed",
                    "result_summary": None,
                    "facts_collected_count": 0,
                    "error": f"No alive agent on target {target_id}",
                }
            agent_paw = agent_row["paw"]

        # Create execution record
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, engine, now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": engine,
        })

        # Select and call engine
        client = self._select_client(engine)
        result: ExecutionResult = await client.execute(ability_id, agent_paw)

        return await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )

    async def _finalize_execution(
        self,
        db: aiosqlite.Connection,
        exec_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        result: ExecutionResult,
    ) -> dict:
        """Update DB, collect facts, and broadcast the final execution.update event."""
        completed_at = datetime.now(timezone.utc).isoformat()
        status = "success" if result.success else "failed"
        facts_count = len(result.facts)

        await db.execute(
            "UPDATE technique_executions SET status = ?, result_summary = ?, "
            "facts_collected_count = ?, completed_at = ?, error_message = ? "
            "WHERE id = ?",
            (status, result.output, facts_count, completed_at,
             result.error, exec_id),
        )

        # [I-1] Only increment techniques_executed on success
        if result.success:
            await db.execute(
                "UPDATE operations SET techniques_executed = techniques_executed + 1 "
                "WHERE id = ?",
                (operation_id,),
            )
        await db.commit()

        # Extract facts from result
        if result.facts:
            await self._fact_collector.collect_from_result(
                db, operation_id, technique_id, target_id, result.facts
            )

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": status, "engine": engine,
            "facts_collected": facts_count,
        })

        return {
            "execution_id": exec_id,
            "technique_id": technique_id,
            "target_id": target_id,
            "engine": engine,
            "status": status,
            "result_summary": result.output,
            "facts_collected_count": facts_count,
            "error": result.error,
        }

    # ── Metasploit helpers ────────────────────────────────────────────────────

    async def _has_exploitable_service(
        self, db: aiosqlite.Connection, operation_id: str, target_id: str
    ) -> "str | None":
        """Return service name from vuln.cve fact with exploit=true, else None."""
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT value FROM facts
               WHERE operation_id = ? AND source_target_id = ?
               AND trait = 'vuln.cve' AND value LIKE '%exploit=true%'
               ORDER BY score DESC
               LIMIT 1""",
            (operation_id, target_id),
        )
        row = await cursor.fetchone()
        if row:
            # format: CVE-xxx:service:product:cvss=N:exploit=true
            parts = row["value"].split(":")
            return parts[1] if len(parts) > 1 else None
        return None

    async def _get_target_ip(
        self, db: aiosqlite.Connection, target_id: str
    ) -> "str | None":
        """Resolve target IP from targets table. Returns None if target not found."""
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ip_address FROM targets WHERE id = ?",
            (target_id,),
        )
        row = await cursor.fetchone()
        return row["ip_address"] if row else None

    async def _execute_metasploit(
        self,
        db: aiosqlite.Connection,
        exec_id: str,
        now: str,
        technique_id: str,
        target_id: str,
        operation_id: str,
        ooda_iteration_id: "str | None",
        service_name: str,
        target_ip: str,
        engine: str,
    ) -> dict:
        """Execute technique via MetasploitRPCEngine (ADR-019)."""
        from app.clients.metasploit_client import MetasploitRPCEngine  # noqa: PLC0415

        started_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO technique_executions
               (id, technique_id, target_id, operation_id, status, engine, started_at)
               VALUES (?, ?, ?, ?, 'running', 'metasploit', ?)""",
            (exec_id, technique_id, target_id, operation_id, started_at),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "metasploit",
        })

        msf_engine = MetasploitRPCEngine()
        method = msf_engine.get_exploit_for_service(service_name)
        if method is None:
            result_dict: dict = {
                "status": "failed",
                "reason": f"no exploit method for service: {service_name}",
                "engine": "metasploit",
                "output": "",
            }
        else:
            result_dict = await method(target_ip)

        status = result_dict.get("status", "failed")
        output = result_dict.get("output", result_dict.get("reason", ""))
        msf_engine_label = result_dict.get("engine", "metasploit")

        completed_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """UPDATE technique_executions
               SET status = ?, result_summary = ?,
                   facts_collected_count = 0, completed_at = ?,
                   error_message = ?
               WHERE id = ?""",
            (
                result_dict["status"],
                result_dict.get("output", ""),
                completed_at,
                result_dict.get("reason") if result_dict["status"] != "success" else None,
                exec_id,
            ),
        )
        if status == "success":
            await db.execute(
                "UPDATE operations SET techniques_executed = techniques_executed + 1 "
                "WHERE id = ?",
                (operation_id,),
            )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": status, "engine": msf_engine_label,
        })

        return {
            "execution_id": exec_id,
            "technique_id": technique_id,
            "target_id": target_id,
            "engine": msf_engine_label,
            "status": status,
            "result_summary": output,
            "facts_collected_count": 0,
            "error": result_dict.get("reason"),
        }

    # ── Engine / client selection ─────────────────────────────────────────────

    def select_engine(
        self, technique_id: str, context: dict,
        gpt_recommendation: str | None = None,
    ) -> str:
        """
        Engine selection logic per ADR-006 priority order:
        1. High-confidence AI recommendation → trust its engine choice
        2. C2 engine has corresponding ability → C2 engine
        3. Unknown environment + Adaptive engine available → Adaptive engine
        4. High stealth requirement + Adaptive engine available → Adaptive engine
        5. Default → Caldera
        """
        # Priority 1: Trust high-confidence PentestGPT recommendation
        if gpt_recommendation and gpt_recommendation in ("caldera", "shannon"):
            if gpt_recommendation == "shannon" and self._adaptive_engine:
                return "shannon"
            return "caldera"

        # Priority 2: Caldera has ability for this technique (always true for known MITRE IDs)
        # In POC, C2 engine is assumed to have all standard MITRE abilities
        # A production version would check c2_engine.list_abilities()

        # Priority 3: Unknown environment → Adaptive engine
        if context.get("environment") == "unknown" and self._adaptive_engine:
            return "shannon"

        # Priority 4: High stealth requirement → Adaptive engine
        if context.get("stealth_level") == "maximum" and self._adaptive_engine:
            return "shannon"

        # Priority 5: Default → C2 engine
        return "caldera"

    def _select_client(self, engine: str) -> BaseEngineClient:
        if engine == "shannon" and self._adaptive_engine:
            return self._adaptive_engine
        return self._c2_engine

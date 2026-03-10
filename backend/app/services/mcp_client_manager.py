# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""MCP Client Manager — manages connections to external MCP tool servers.

Features:
- Circuit breaker (CLOSED → OPEN → HALF_OPEN) per server
- Periodic health check with auto-reconnect
- Tool registry auto-sync (connect → enable, disconnect → soft-delete)
- Transport mode: stdio / http / auto
- Structured MCP_AUDIT logging
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — set during app lifespan, used by engines
_instance: "MCPClientManager | None" = None


def get_mcp_manager() -> "MCPClientManager | None":
    """Return the global MCPClientManager instance, or None if MCP disabled."""
    return _instance


def set_mcp_manager(manager: "MCPClientManager | None") -> None:
    """Set the global MCPClientManager instance (called from app lifespan)."""
    global _instance
    _instance = manager


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    backoff_exponent: int = 0

    def record_failure(self, max_retries: int) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= max_retries and self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.backoff_exponent = min(self.backoff_exponent + 1, 6)

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.backoff_exponent = 0

    def cooldown_elapsed(self, base_interval: float) -> bool:
        cooldown = min(base_interval * (2 ** self.backoff_exponent), 60.0)
        return (time.monotonic() - self.last_failure_time) >= cooldown

    def should_allow_request(self, base_interval: float) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.cooldown_elapsed(base_interval):
            self.state = CircuitState.HALF_OPEN
            return True
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MCPServerConfig:
    """Parsed config for a single MCP server from mcp_servers.json."""

    name: str
    transport: str  # "stdio" | "http"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    http_url: str | None = None  # separate HTTP endpoint for auto mode
    enabled: bool = True
    description: str = ""
    tool_prefix: str = ""


@dataclass
class MCPToolInfo:
    """Discovered tool from an MCP server."""

    server_name: str
    tool_name: str
    description: str
    input_schema: dict


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Default MITRE ATT&CK + category metadata for auto-discovered MCP tools
# ---------------------------------------------------------------------------

_MCP_TOOL_METADATA: dict[str, dict[str, Any]] = {
    # osint-recon
    "osint-recon_dns_resolve":                    {"category": "reconnaissance",        "mitre": ["T1018", "T1596.001"]},
    # vuln-lookup
    "vuln-lookup_banner_to_cpe":                  {"category": "vulnerability_scanning", "mitre": ["T1592.002"]},
    # credential-checker
    "credential-checker_rdp_credential_check":    {"category": "credential_access",     "mitre": ["T1110.001", "T1021.001"]},
    "credential-checker_winrm_credential_check":  {"category": "credential_access",     "mitre": ["T1110.001", "T1021.006"]},
    # attack-executor
    "attack-executor_execute_technique":          {"category": "execution",             "mitre": ["T1059.004"]},
    "attack-executor_close_sessions":             {"category": "execution",             "mitre": ["T1059.004"]},
    # web-scanner
    "web-scanner_web_http_probe":                 {"category": "reconnaissance",        "mitre": ["T1595.002"]},
    "web-scanner_web_vuln_scan":                  {"category": "vulnerability_scanning", "mitre": ["T1595.002", "T1190"]},
    "web-scanner_web_dir_enum":                   {"category": "reconnaissance",        "mitre": ["T1595.003"]},
    "web-scanner_web_screenshot":                 {"category": "reconnaissance",        "mitre": ["T1592.004"]},
    # api-fuzzer
    "api-fuzzer_api_schema_detect":               {"category": "reconnaissance",        "mitre": ["T1595.002"]},
    "api-fuzzer_api_endpoint_enum":               {"category": "reconnaissance",        "mitre": ["T1595.002"]},
    "api-fuzzer_api_auth_test":                   {"category": "credential_access",     "mitre": ["T1110", "T1550"]},
    "api-fuzzer_api_param_fuzz":                  {"category": "vulnerability_scanning", "mitre": ["T1190"]},
}

# Manager
# ---------------------------------------------------------------------------

class MCPClientManager:
    """Manages connections to multiple MCP servers.

    Lifecycle:
        startup()  -> load config, connect, discover tools, sync registry, start health task
        shutdown() -> cancel health task, disconnect all sessions
    """

    def __init__(self, ws_manager=None) -> None:
        self._configs: dict[str, MCPServerConfig] = {}
        self._sessions: dict[str, Any] = {}  # name -> ClientSession
        self._transports: dict[str, Any] = {}  # name -> transport context manager
        self._tools: dict[str, list[MCPToolInfo]] = {}  # name -> discovered tools
        self._tool_index: dict[str, MCPToolInfo] = {}  # "server:tool" -> info
        self._breakers: dict[str, CircuitBreakerState] = {}
        self._ws = ws_manager
        self._health_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Load mcp_servers.json and schedule connections via background health check.

        Connections are deferred to the periodic health check task to avoid
        blocking app startup and to isolate connection errors (the MCP SDK's
        streamablehttp_client can spawn internal tasks that raise RuntimeError
        on failure, which would crash the lifespan if run synchronously).
        """
        config_path = Path(settings.MCP_SERVERS_FILE)
        if not config_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent.parent
            config_path = project_root / config_path

        if not config_path.exists():
            logger.warning("MCP servers file not found: %s", config_path)
            return

        raw = json.loads(config_path.read_text())
        for name, cfg in raw.get("servers", {}).items():
            server_cfg = MCPServerConfig(
                name=name,
                transport=cfg["transport"],
                command=cfg.get("command"),
                args=cfg.get("args", []),
                env=cfg.get("env", {}),
                url=cfg.get("url"),
                http_url=cfg.get("http_url"),
                enabled=cfg.get("enabled", True),
                description=cfg.get("description", ""),
                tool_prefix=cfg.get("tool_prefix", ""),
            )
            self._configs[name] = server_cfg
            self._breakers[name] = CircuitBreakerState()

        logger.info("MCP: loaded %d server configs — connections deferred to background", len(self._configs))

        # Start periodic health check (handles initial connections)
        self._health_task = asyncio.create_task(self._periodic_health_check())

    async def shutdown(self) -> None:
        """Cancel health task and disconnect all active MCP sessions."""
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        for name in list(self._sessions.keys()):
            await self._disconnect(name)

    # ------------------------------------------------------------------
    # Connection (with transport mode selection)
    # ------------------------------------------------------------------

    async def _connect(self, config: MCPServerConfig) -> None:
        """Establish connection with timeout and circuit breaker integration."""
        breaker = self._breakers.get(config.name, CircuitBreakerState())
        try:
            await asyncio.wait_for(
                self._connect_inner(config),
                timeout=float(settings.MCP_TOOL_TIMEOUT_SEC),
            )
            breaker.record_success()
            logger.info(
                "MCP_AUDIT event=connect server=%s transport=%s tools=%d circuit=%s",
                config.name,
                self._get_effective_transport(config),
                len(self._tools.get(config.name, [])),
                breaker.state.value,
            )
            # Sync tools to DB
            await self._sync_tools_to_db(config.name)
        except Exception:
            breaker.record_failure(settings.MCP_MAX_RETRIES)
            logger.exception(
                "MCP_AUDIT event=connect_failed server=%s circuit=%s failures=%d",
                config.name, breaker.state.value, breaker.failure_count,
            )

    def _get_effective_transport(self, config: MCPServerConfig) -> str:
        """Determine which transport to use based on MCP_TRANSPORT_MODE."""
        mode = getattr(settings, "MCP_TRANSPORT_MODE", "auto")
        if mode == "http":
            return "http"
        if mode == "stdio":
            return "stdio"
        # auto: prefer HTTP if http_url is configured
        if config.http_url or (config.transport == "http" and config.url):
            return "http"
        return "stdio"

    async def _connect_inner(self, config: MCPServerConfig) -> None:
        """Establish transport and session for a single MCP server."""
        effective_transport = self._get_effective_transport(config)

        if effective_transport == "http":
            http_url = config.http_url or config.url
            if not http_url:
                raise ValueError(f"No HTTP URL for server '{config.name}'")

            # Probe HTTP availability in auto mode
            mode = getattr(settings, "MCP_TRANSPORT_MODE", "auto")
            if mode == "auto":
                if not await self._probe_http(http_url):
                    # Fallback to stdio in auto mode
                    if config.command:
                        await self._connect_stdio(config)
                        return
                    raise ConnectionError(
                        f"HTTP unreachable and no stdio command for '{config.name}'"
                    )

            await self._connect_http(config, http_url)
        else:
            await self._connect_stdio(config)

    async def _connect_stdio(self, config: MCPServerConfig) -> None:
        """Connect via stdio transport."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )
        transport_ctx = stdio_client(params)
        streams = await transport_ctx.__aenter__()
        read_stream, write_stream = streams[0], streams[1]

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        self._transports[config.name] = transport_ctx
        self._sessions[config.name] = session
        await self._discover_tools(config.name, session)

    async def _connect_http(self, config: MCPServerConfig, url: str) -> None:
        """Connect via HTTP (streamable-http) transport."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        transport_ctx = streamablehttp_client(url=url)
        try:
            streams = await transport_ctx.__aenter__()
            read_stream, write_stream = streams[0], streams[1]

            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            self._transports[config.name] = transport_ctx
            self._sessions[config.name] = session
            await self._discover_tools(config.name, session)
        except Exception:
            # Clean up transport context on failure; ignore cleanup errors
            # (anyio cancel-scope RuntimeError can occur during cleanup)
            try:
                await transport_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            raise

    async def _probe_http(self, url: str) -> bool:
        """Probe if an HTTP MCP endpoint is reachable (1s timeout)."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(url)
                return resp.status_code < 500
        except Exception:
            return False

    async def _discover_tools(self, server_name: str, session: Any) -> None:
        """Discover tools from a connected session."""
        tools_result = await session.list_tools()
        discovered: list[MCPToolInfo] = []
        for tool in tools_result.tools:
            info = MCPToolInfo(
                server_name=server_name,
                tool_name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
            )
            discovered.append(info)
            self._tool_index[f"{server_name}:{tool.name}"] = info

        self._tools[server_name] = discovered

        # Broadcast status
        await self._broadcast_server_status(server_name, connected=True)

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    async def _disconnect(self, name: str) -> None:
        """Disconnect a single MCP server session."""
        session = self._sessions.pop(name, None)
        transport = self._transports.pop(name, None)
        self._tools.pop(name, None)
        keys_to_remove = [k for k in self._tool_index if k.startswith(f"{name}:")]
        for k in keys_to_remove:
            del self._tool_index[k]

        try:
            if session:
                await session.__aexit__(None, None, None)
            if transport:
                await transport.__aexit__(None, None, None)
        except Exception:
            logger.warning("Error disconnecting MCP server '%s'", name, exc_info=True)

        logger.info("MCP_AUDIT event=disconnect server=%s", name)
        await self._broadcast_server_status(name, connected=False)
        await self._soft_delete_server_tools(name)

    # ------------------------------------------------------------------
    # Tool invocation (with circuit breaker)
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a tool on a specific MCP server. Returns normalized result."""
        breaker = self._breakers.get(server_name, CircuitBreakerState())

        if not breaker.should_allow_request(settings.MCP_RECONNECT_INTERVAL_SEC):
            raise ConnectionError(
                f"MCP server '{server_name}' circuit is OPEN "
                f"(failures={breaker.failure_count})"
            )

        session = self._sessions.get(server_name)
        if session is None:
            # Try reconnect if config exists
            config = self._configs.get(server_name)
            if config and config.enabled:
                logger.info("MCP '%s' disconnected; reconnecting", server_name)
                await self._connect(config)
                session = self._sessions.get(server_name)
            if session is None:
                breaker.record_failure(settings.MCP_MAX_RETRIES)
                raise ConnectionError(f"MCP server '{server_name}' is not connected")

        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=float(settings.MCP_TOOL_TIMEOUT_SEC),
            )
        except asyncio.TimeoutError:
            breaker.record_failure(settings.MCP_MAX_RETRIES)
            logger.warning(
                "MCP_AUDIT event=call_tool server=%s tool=%s TIMEOUT after %ds circuit=%s",
                server_name, tool_name, settings.MCP_TOOL_TIMEOUT_SEC, breaker.state.value,
            )
            if breaker.state == CircuitState.OPEN:
                asyncio.create_task(self._soft_delete_server_tools(server_name))
            raise
        except Exception:
            breaker.record_failure(settings.MCP_MAX_RETRIES)
            logger.warning(
                "MCP_AUDIT event=call_tool server=%s tool=%s ERROR circuit=%s",
                server_name, tool_name, breaker.state.value,
                exc_info=True,
            )
            if breaker.state == CircuitState.OPEN:
                asyncio.create_task(self._soft_delete_server_tools(server_name))
            raise

        duration_ms = int((time.monotonic() - t0) * 1000)
        is_error = getattr(result, "isError", False)

        if is_error:
            breaker.record_failure(settings.MCP_MAX_RETRIES)
        else:
            breaker.record_success()

        logger.info(
            "MCP_AUDIT event=call_tool server=%s tool=%s duration_ms=%d is_error=%s circuit=%s",
            server_name, tool_name, duration_ms, is_error, breaker.state.value,
        )

        return {
            "content": [
                {
                    "type": getattr(block, "type", "text"),
                    "text": getattr(block, "text", str(block)),
                }
                for block in (result.content or [])
            ],
            "is_error": is_error,
        }

    # ------------------------------------------------------------------
    # Health check (periodic background task)
    # ------------------------------------------------------------------

    async def _periodic_health_check(self) -> None:
        """Background task: ping servers every 30s, reconnect OPEN circuits."""
        first_run = True
        while True:
            if first_run:
                await asyncio.sleep(2)  # short delay on first run
                first_run = False
            else:
                await asyncio.sleep(30)
            for name, config in self._configs.items():
                if not config.enabled:
                    continue

                breaker = self._breakers.get(name, CircuitBreakerState())

                try:
                    if name in self._sessions:
                        # Ping connected server
                        healthy = await self.health_check(name)
                        logger.debug(
                            "MCP_AUDIT event=health_check server=%s healthy=%s circuit=%s",
                            name, healthy, breaker.state.value,
                        )
                        if not healthy:
                            breaker.record_failure(settings.MCP_MAX_RETRIES)
                            await self._disconnect(name)
                    elif breaker.state == CircuitState.OPEN:
                        # Try reconnect if cooldown elapsed
                        if breaker.cooldown_elapsed(settings.MCP_RECONNECT_INTERVAL_SEC):
                            logger.info(
                                "MCP_AUDIT event=reconnect_attempt server=%s circuit=%s",
                                name, breaker.state.value,
                            )
                            breaker.state = CircuitState.HALF_OPEN
                            await self._connect(config)
                    elif breaker.state == CircuitState.CLOSED and name not in self._sessions:
                        # Not connected but circuit is closed — try connect
                        await self._connect(config)
                except BaseException:
                    logger.error("Health check error for MCP server '%s'", name, exc_info=True)

                # Broadcast current status
                await self._broadcast_server_status(
                    name, connected=name in self._sessions
                )

    async def health_check(self, server_name: str) -> bool:
        """Check if a server session is alive by listing tools."""
        session = self._sessions.get(server_name)
        if session is None:
            return False
        try:
            await session.list_tools()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Tool Registry Sync
    # ------------------------------------------------------------------

    async def _sync_tools_to_db(self, server_name: str) -> None:
        """Sync discovered MCP tools to tool_registry DB table."""
        tools = self._tools.get(server_name, [])
        if not tools:
            return

        try:
            from app.database import db_manager

            async with db_manager.connection() as db:
                for tool_info in tools:
                    mcp_config = json.dumps({
                        "mcp_server": server_name,
                        "mcp_tool": tool_info.tool_name,
                    })

                    # Check if seed/user entry already covers this MCP tool
                    existing = await db.fetchrow(
                        """SELECT id, source, enabled, mitre_techniques, category
                           FROM tool_registry
                           WHERE config_json LIKE $1 AND config_json LIKE $2""",
                        f'%"mcp_server":"{server_name}"%',
                        f'%"mcp_tool":"{tool_info.tool_name}"%',
                    )

                    if existing:
                        tool_id = f"{server_name}_{tool_info.tool_name}"
                        meta = _MCP_TOOL_METADATA.get(tool_id, {})
                        updates: list[str] = []
                        params: list = []
                        param_idx = 1
                        # Re-enable if disabled
                        if not existing["enabled"]:
                            updates.append("enabled = TRUE")
                        # Backfill MITRE techniques if empty
                        cur_mitre = existing["mitre_techniques"] or "[]"
                        if meta.get("mitre") and cur_mitre == "[]":
                            updates.append(f"mitre_techniques = ${param_idx}")
                            params.append(json.dumps(meta["mitre"]))
                            param_idx += 1
                        # Backfill category if still default
                        if meta.get("category") and existing["category"] == "reconnaissance" and meta["category"] != "reconnaissance":
                            updates.append(f"category = ${param_idx}")
                            params.append(meta["category"])
                            param_idx += 1
                        if updates:
                            updates.append("updated_at = NOW()")
                            params.append(existing["id"])
                            await db.execute(
                                f"UPDATE tool_registry SET {', '.join(updates)} WHERE id = ${param_idx}",
                                *params,
                            )
                    else:
                        # Insert new mcp_discovery entry
                        tool_id = f"{server_name}_{tool_info.tool_name}"
                        meta = _MCP_TOOL_METADATA.get(tool_id, {})
                        category = meta.get("category", "reconnaissance")
                        mitre = json.dumps(meta.get("mitre", []))
                        await db.execute(
                            """INSERT INTO tool_registry
                               (id, tool_id, name, description, kind, category,
                                mitre_techniques, enabled, source, config_json,
                                created_at, updated_at)
                               VALUES ($1, $2, $3, $4, 'tool', $5,
                                       $6, TRUE, 'mcp_discovery', $7,
                                       NOW(), NOW())
                               ON CONFLICT DO NOTHING""",
                            str(uuid.uuid4()),
                            tool_id,
                            tool_info.tool_name,
                            tool_info.description,
                            category,
                            mitre,
                            mcp_config,
                        )

            logger.info(
                "MCP_AUDIT event=tool_sync server=%s tools_synced=%d",
                server_name, len(tools),
            )
        except Exception:
            logger.debug("Tool registry sync failed for '%s'", server_name, exc_info=True)

    async def _soft_delete_server_tools(self, server_name: str) -> None:
        """Soft-delete (disable) tools associated with a disconnected MCP server."""
        try:
            from app.database import db_manager

            async with db_manager.connection() as db:
                await db.execute(
                    """UPDATE tool_registry SET enabled = FALSE, updated_at = NOW()
                       WHERE config_json LIKE $1
                         AND source IN ('seed', 'mcp_discovery')""",
                    f'%"mcp_server":"{server_name}"%',
                )

            logger.info(
                "MCP_AUDIT event=tool_soft_delete server=%s", server_name,
            )
        except Exception:
            logger.debug("Tool soft-delete failed for '%s'", server_name, exc_info=True)

    # ------------------------------------------------------------------
    # WebSocket broadcast helper
    # ------------------------------------------------------------------

    async def _broadcast_server_status(
        self, server_name: str, *, connected: bool
    ) -> None:
        """Broadcast mcp.server.status WS event."""
        if not self._ws:
            return
        try:
            await self._ws.broadcast_global("mcp.server.status", {
                "server": server_name,
                "connected": connected,
                "tool_count": len(self._tools.get(server_name, [])),
            })
        except Exception:
            logger.debug(
                "Failed to broadcast MCP status for '%s'", server_name, exc_info=True,
            )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def list_servers(self) -> list[dict[str, Any]]:
        """Return list of configured servers with connection and circuit status."""
        return [
            {
                "name": name,
                "transport": cfg.transport,
                "enabled": cfg.enabled,
                "connected": name in self._sessions,
                "tool_count": len(self._tools.get(name, [])),
                "description": cfg.description,
                "circuit_state": self._breakers.get(name, CircuitBreakerState()).state.value,
                "failure_count": self._breakers.get(name, CircuitBreakerState()).failure_count,
            }
            for name, cfg in self._configs.items()
        ]

    def list_all_tools(self) -> list[MCPToolInfo]:
        """Return flat list of all discovered tools across all servers."""
        return list(self._tool_index.values())

    def get_server_for_tool(self, tool_name: str) -> str | None:
        """Reverse lookup: find which server provides a given tool_name."""
        for info in self._tool_index.values():
            if info.tool_name == tool_name:
                return info.server_name
        return None

    def is_connected(self, server_name: str) -> bool:
        """Check if a server is currently connected."""
        return server_name in self._sessions

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

"""MCP Client Manager — manages connections to external MCP tool servers."""

import json
import logging
from dataclasses import dataclass, field
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


@dataclass
class MCPServerConfig:
    """Parsed config for a single MCP server from mcp_servers.json."""

    name: str
    transport: str  # "stdio" | "http"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
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


class MCPClientManager:
    """Manages connections to multiple MCP servers.

    Lifecycle:
        startup()  -> load config, connect to all enabled servers, discover tools
        shutdown() -> disconnect all sessions
    """

    def __init__(self) -> None:
        self._configs: dict[str, MCPServerConfig] = {}
        self._sessions: dict[str, Any] = {}  # name -> ClientSession
        self._transports: dict[str, Any] = {}  # name -> transport context manager
        self._tools: dict[str, list[MCPToolInfo]] = {}  # name -> discovered tools
        self._tool_index: dict[str, MCPToolInfo] = {}  # "server:tool" -> info

    async def startup(self) -> None:
        """Load mcp_servers.json and connect to all enabled servers."""
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
                enabled=cfg.get("enabled", True),
                description=cfg.get("description", ""),
                tool_prefix=cfg.get("tool_prefix", ""),
            )
            self._configs[name] = server_cfg
            if server_cfg.enabled:
                await self._connect(server_cfg)

    async def shutdown(self) -> None:
        """Disconnect all active MCP sessions."""
        for name in list(self._sessions.keys()):
            await self._disconnect(name)

    async def _connect(self, config: MCPServerConfig) -> None:
        """Establish connection to a single MCP server and discover tools."""
        try:
            if config.transport == "stdio":
                from mcp import StdioServerParameters
                from mcp.client.stdio import stdio_client

                params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env or None,
                )
                transport_ctx = stdio_client(params)
            elif config.transport == "http":
                from mcp.client.streamable_http import streamablehttp_client

                transport_ctx = streamablehttp_client(url=config.url)
            else:
                logger.error(
                    "Unknown transport '%s' for server '%s'",
                    config.transport, config.name,
                )
                return

            streams = await transport_ctx.__aenter__()
            # stdio returns (read, write); http returns (read, write, session_id)
            read_stream = streams[0]
            write_stream = streams[1]

            from mcp import ClientSession

            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            self._transports[config.name] = transport_ctx
            self._sessions[config.name] = session

            # Discover tools
            tools_result = await session.list_tools()
            discovered: list[MCPToolInfo] = []
            for tool in tools_result.tools:
                info = MCPToolInfo(
                    server_name=config.name,
                    tool_name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                )
                discovered.append(info)
                self._tool_index[f"{config.name}:{tool.name}"] = info

            self._tools[config.name] = discovered
            logger.info(
                "Connected to MCP server '%s' — discovered %d tools",
                config.name, len(discovered),
            )

        except Exception:
            logger.exception("Failed to connect to MCP server '%s'", config.name)

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

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a tool on a specific MCP server. Returns normalized result."""
        session = self._sessions.get(server_name)
        if session is None:
            raise ConnectionError(f"MCP server '{server_name}' is not connected")

        result = await session.call_tool(tool_name, arguments)
        return {
            "content": [
                {
                    "type": getattr(block, "type", "text"),
                    "text": getattr(block, "text", str(block)),
                }
                for block in (result.content or [])
            ],
            "is_error": getattr(result, "isError", False),
        }

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

    def list_servers(self) -> list[dict[str, Any]]:
        """Return list of configured servers with connection status."""
        return [
            {
                "name": name,
                "transport": cfg.transport,
                "enabled": cfg.enabled,
                "connected": name in self._sessions,
                "tool_count": len(self._tools.get(name, [])),
                "description": cfg.description,
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

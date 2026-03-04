# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""MCP Engine Client — BaseEngineClient adapter for MCP tool servers."""

import logging
from typing import Any
from uuid import uuid4

from app.clients import BaseEngineClient, ExecutionResult
from app.services.mcp_client_manager import MCPClientManager
from app.services.mcp_fact_extractor import MCPFactExtractor

logger = logging.getLogger(__name__)


class MCPEngineClient(BaseEngineClient):
    """Adapts MCPClientManager to the BaseEngineClient interface.

    ability_id is used as the MCP tool name (or "server:tool" qualified).
    target is passed as the "target" argument to the MCP tool.
    """

    def __init__(self, manager: MCPClientManager) -> None:
        self._manager = manager

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        execution_id = str(uuid4())

        # Resolve server and tool name
        if ":" in ability_id:
            server_name, tool_name = ability_id.split(":", 1)
        else:
            server_name = self._manager.get_server_for_tool(ability_id)
            tool_name = ability_id
            if server_name is None:
                return ExecutionResult(
                    success=False,
                    execution_id=execution_id,
                    error=f"No MCP server found for tool '{ability_id}'",
                )

        # Build arguments
        arguments: dict[str, Any] = {"target": target}
        if params:
            arguments.update(params)

        try:
            mcp_result = await self._manager.call_tool(server_name, tool_name, arguments)
        except ConnectionError as exc:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("MCP tool execution failed: %s", ability_id)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=f"MCP execution error: {exc}",
            )

        if mcp_result.get("is_error"):
            error_text = MCPFactExtractor._extract_text(mcp_result)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output=error_text[:2000],
                error=error_text[:500],
            )

        output_text, facts = MCPFactExtractor.extract(mcp_result)

        return ExecutionResult(
            success=True,
            execution_id=execution_id,
            output=output_text[:2000],
            facts=facts,
        )

    async def get_status(self, execution_id: str) -> str:
        """MCP tools are synchronous request/response — always completed."""
        return "completed"

    async def list_abilities(self) -> list[dict]:
        """List all available MCP tools across all connected servers."""
        return [
            {
                "ability_id": f"{t.server_name}:{t.tool_name}",
                "name": t.tool_name,
                "description": t.description,
                "server": t.server_name,
            }
            for t in self._manager.list_all_tools()
        ]

    async def is_available(self) -> bool:
        """Return True if at least one MCP server is connected."""
        return any(
            s["connected"]
            for s in self._manager.list_servers()
        )

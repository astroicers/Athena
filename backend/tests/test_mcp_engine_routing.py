# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for MCP engine routing in EngineRouter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_select_engine_returns_mcp():
    from app.services.engine_router import EngineRouter

    router = EngineRouter(MagicMock(), MagicMock(), MagicMock(), mcp_engine=MagicMock())
    assert router.select_engine("T1595", {}, gpt_recommendation="mcp") == "mcp"


@pytest.mark.asyncio
async def test_select_engine_mcp_fallback_when_no_engine():
    from app.services.engine_router import EngineRouter

    router = EngineRouter(MagicMock(), MagicMock(), MagicMock(), mcp_engine=None)
    result = router.select_engine("T1595", {}, gpt_recommendation="mcp")
    assert result == "ssh"  # fallback


@pytest.mark.asyncio
async def test_build_ooda_controller_wires_mcp_engine():
    """build_ooda_controller() passes MCPEngineClient to EngineRouter when MCP enabled."""
    with patch("app.services.ooda_controller.settings") as s:
        s.MOCK_C2_ENGINE = True
        s.MCP_ENABLED = True
        s.C2_ENGINE_URL = "http://mock"
        s.C2_ENGINE_API_KEY = ""
        mock_mgr = MagicMock()
        mock_mgr.list_servers.return_value = []
        with patch(
            "app.services.ooda_controller.get_mcp_manager", return_value=mock_mgr
        ):
            from app.services.ooda_controller import build_ooda_controller

            controller = build_ooda_controller()
    assert controller._router._mcp_engine is not None


@pytest.mark.asyncio
async def test_execute_mcp_calls_mcp_engine(seeded_db):
    """MCP route calls mcp_engine.execute with the ability_id."""
    from app.clients import ExecutionResult
    from app.services.engine_router import EngineRouter

    mock_mcp = MagicMock()
    mock_mcp.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True,
            execution_id="e1",
            output='{"facts": []}',
            facts=[],
        )
    )
    mock_fc = MagicMock()
    mock_fc.collect_from_result = AsyncMock(return_value=[])
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()

    with patch("app.services.engine_router.settings") as s:
        s.MCP_ENABLED = True
        s.MOCK_C2_ENGINE = True
        s.EXECUTION_ENGINE = "ssh"
        router = EngineRouter(MagicMock(), mock_fc, mock_ws, mcp_engine=mock_mcp)
        result = await router.execute(
            seeded_db,
            technique_id="T1003.001",
            target_id="test-target-1",
            engine="mcp",
            operation_id="test-op-1",
        )

    mock_mcp.execute.assert_awaited_once()
    assert result["engine"] == "mcp"

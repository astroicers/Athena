# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Tests for MCP engine routing in EngineRouter."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_select_engine_returns_mcp_ssh():
    from app.services.engine_router import EngineRouter

    router = EngineRouter(MagicMock(), MagicMock(), MagicMock(), mcp_engine=MagicMock())
    assert router.select_engine("T1595", {}, gpt_recommendation="mcp_ssh") == "mcp_ssh"


@pytest.mark.asyncio
async def test_select_engine_mcp_fallback_when_no_engine():
    from app.services.engine_router import EngineRouter

    router = EngineRouter(MagicMock(), MagicMock(), MagicMock(), mcp_engine=None)
    result = router.select_engine("T1595", {}, gpt_recommendation="mcp_ssh")
    assert result == "c2"  # fallback when MCP not available


@pytest.mark.asyncio
async def test_select_engine_default_is_mcp_ssh():
    from app.services.engine_router import EngineRouter

    router = EngineRouter(MagicMock(), MagicMock(), MagicMock(), mcp_engine=MagicMock())
    result = router.select_engine("T1595", {})
    assert result == "mcp_ssh"


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
        s.EXECUTION_ENGINE = "mcp_ssh"
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


@pytest.mark.asyncio
async def test_mcp_ssh_routes_to_executor(seeded_db):
    """EXECUTION_ENGINE=mcp_ssh routes through _execute_via_mcp_executor."""
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.0.1:22', 'credential', 1)",
        str(uuid.uuid4()),
    )

    mock_result = ExecutionResult(
        success=True,
        execution_id="mcp-exec-1",
        output="Linux host 5.15.0",
        facts=[{"trait": "host.os", "value": "Linux", "score": 1, "source": "attack_executor"}],
    )

    mcp_engine = AsyncMock()
    mcp_engine.execute = AsyncMock(return_value=mock_result)

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fact_collector = MagicMock()
    fact_collector.collect_from_result = AsyncMock()

    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=fact_collector,
        ws_manager=ws,
        mcp_engine=mcp_engine,
    )

    with patch("app.services.engine_router.settings") as mock_settings:
        mock_settings.EXECUTION_ENGINE = "mcp_ssh"
        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.PERSISTENCE_ENABLED = False

        result = await router.execute(
            db=seeded_db,
            technique_id="T1592",
            target_id="test-target-1",
            engine="auto",
            operation_id="test-op-1",
        )

    assert result["status"] == "success"
    assert result["engine"] == "mcp_ssh"

    mcp_engine.execute.assert_awaited_once()
    call_args = mcp_engine.execute.call_args
    assert call_args[0][0] == "attack-executor:execute_technique"


@pytest.mark.asyncio
async def test_execute_mcp_marks_compromised(seeded_db):
    """_execute_mcp() should call _mark_target_compromised on success."""
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    mock_result = ExecutionResult(
        success=True,
        execution_id="mcp-exec-2",
        output="uid=0(root)",
        facts=[],
    )

    mcp_engine = AsyncMock()
    mcp_engine.execute = AsyncMock(return_value=mock_result)

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fact_collector = MagicMock()
    fact_collector.collect_from_result = AsyncMock()

    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=fact_collector,
        ws_manager=ws,
        mcp_engine=mcp_engine,
    )

    await router._execute_mcp(
        db=seeded_db,
        exec_id="mcp-exec-2",
        now=datetime.now(timezone.utc),
        ability_id="nmap-scanner:scan_host",
        technique_id="T1592",
        target_id="test-target-1",
        engine="mcp",
        operation_id="test-op-1",
        ooda_iteration_id=None,
    )

    row = await seeded_db.fetchrow(
        "SELECT is_compromised, privilege_level FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is True
    assert row["privilege_level"] == "root"


def test_ooda_controller_wires_mcp():
    """_get_controller() uses build_ooda_controller which wires MCP engine."""
    with patch("app.services.ooda_controller.build_ooda_controller") as mock_build:
        mock_controller = MagicMock()
        mock_build.return_value = mock_controller

        from app.routers.ooda import _get_controller
        _get_controller.cache_clear()

        result = _get_controller()
        mock_build.assert_called_once()
        assert result is mock_controller

        _get_controller.cache_clear()

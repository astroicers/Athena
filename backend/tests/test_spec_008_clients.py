# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Execution engine client tests — SPEC-008 acceptance criteria."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients import ExecutionResult
from app.clients.mock_c2_client import MockC2Client
from app.clients.c2_client import C2EngineClient


# ===================================================================
# MockC2Client (5 tests)
# ===================================================================


async def test_mock_c2_execute_known_technique():
    """MockC2Client.execute() with known T1003.001 → success with facts."""
    client = MockC2Client()
    with patch("app.clients.mock_c2_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.execute("T1003.001", "DC-01")
    assert result.success is True
    assert result.execution_id  # non-empty UUID
    assert len(result.facts) > 0
    assert any("credential" in f["trait"] for f in result.facts)


async def test_mock_c2_execute_unknown_technique():
    """MockC2Client.execute() with unknown technique → success with empty facts."""
    client = MockC2Client()
    with patch("app.clients.mock_c2_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.execute("T9999.999", "WS-01")
    assert result.success is True
    assert result.facts == []
    assert "T9999.999" in result.output


async def test_mock_c2_get_status():
    """get_status() → 'finished'."""
    client = MockC2Client()
    status = await client.get_status("any-id")
    assert status == "finished"


async def test_mock_c2_list_abilities():
    """list_abilities() → non-empty list with known technique IDs."""
    client = MockC2Client()
    abilities = await client.list_abilities()
    assert len(abilities) >= 4
    ids = {a["ability_id"] for a in abilities}
    assert "T1003.001" in ids
    assert "T1595.001" in ids


async def test_mock_c2_is_available():
    """is_available() → True (always available in mock mode)."""
    client = MockC2Client()
    assert await client.is_available() is True


# ===================================================================
# C2EngineClient (1 test — structural only, no real C2 engine)
# ===================================================================


async def test_c2_engine_client_check_version_callable():
    """C2EngineClient has check_version() method that is callable."""
    client = C2EngineClient(base_url="http://localhost:8888", api_key="test")
    assert callable(client.check_version)
    assert callable(client.sync_agents)
    # Cleanup
    await client.aclose()


async def test_engine_router_metasploit_route(seeded_db):
    """EngineRouter routes to MetasploitRPCEngine when exploit=true CVE fact exists."""
    from app.services.engine_router import EngineRouter
    from app.clients.mock_c2_client import MockC2Client
    from app.services.fact_collector import FactCollector

    # Insert vuln.cve fact with exploit=true for seeded target
    await seeded_db.execute(
        """INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score)
           VALUES ($1, 'test-op-1', 'test-target-1',
                   'vuln.cve', 'CVE-2011-2523:vsftpd:vsftpd_2.3.4:cvss=10.0:exploit=true',
                   'vulnerability', 1)""",
        str(uuid.uuid4()),
    )
    # Insert a technique record for T1190
    await seeded_db.execute(
        """INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
           VALUES ('tech-t1190', 'T1190', 'Exploit Public-Facing Application',
                   'Initial Access', 'TA0001', 'high')
           ON CONFLICT DO NOTHING"""
    )

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    router = EngineRouter(
        c2_engine=MockC2Client(),
        fact_collector=FactCollector(ws_manager=mock_ws),
        ws_manager=mock_ws,
    )

    result = await router.execute(
        db=seeded_db,
        technique_id="T1190",
        target_id="test-target-1",
        engine="metasploit",
        operation_id="test-op-1",
    )

    assert result["status"] == "success"
    assert result.get("engine") in ("metasploit", "metasploit_mock")

    # Verify that technique_executions was written by _execute_metasploit()
    exec_row = await seeded_db.fetchrow(
        "SELECT engine, status FROM technique_executions "
        "WHERE operation_id = 'test-op-1' ORDER BY started_at DESC LIMIT 1"
    )
    assert exec_row is not None, "technique_executions row was not written"
    assert exec_row["engine"] == "metasploit"
    assert exec_row["status"] == "success"


async def test_engine_router_mcp_ssh_route(seeded_db):
    """EXECUTION_ENGINE=mcp_ssh routes to _execute_via_mcp_executor.

    Uses seeded_db with real PostgreSQL schema instead of in-memory SQLite.
    """
    from app.services.engine_router import EngineRouter
    from app.clients.mock_c2_client import MockC2Client
    from app.clients import ExecutionResult

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    mock_mcp = MagicMock()
    mock_mcp.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True, execution_id="exec-123",
            output="Linux test", facts=[], error=None,
        )
    )
    mock_fc = MagicMock()
    mock_fc.collect_from_result = AsyncMock(return_value=[])
    router = EngineRouter(
        c2_engine=MockC2Client(),
        fact_collector=mock_fc,
        ws_manager=mock_ws,
        mcp_engine=mock_mcp,
    )

    # Insert required data for this test
    await seeded_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('t1-mcp-route', 'T1003.001', 'OS Credential Dumping', 'Credential Access', 'TA0006', 'high') "
        "ON CONFLICT DO NOTHING"
    )
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, category, trait, value, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential', "
        "'credential.ssh', 'root:toor@10.0.1.5:22', 1)",
        str(uuid.uuid4()),
    )

    with patch("app.services.engine_router.settings") as mock_settings:
        mock_settings.EXECUTION_ENGINE = "mcp_ssh"
        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.PERSISTENCE_ENABLED = False

        result = await router.execute(
            db=seeded_db,
            technique_id="T1003.001",
            target_id="test-target-1",
            engine="auto",
            operation_id="test-op-1",
        )

    assert result["status"] == "success"
    assert result["engine"] == "mcp_ssh"
    mock_mcp.execute.assert_awaited_once()
    call_args = mock_mcp.execute.call_args
    assert call_args[0][0] == "attack-executor:execute_technique"

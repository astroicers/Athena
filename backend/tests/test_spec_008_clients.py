# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Execution engine client tests — SPEC-008 acceptance criteria."""

from unittest.mock import AsyncMock, patch

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
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    from app.services.engine_router import EngineRouter
    from app.clients.mock_c2_client import MockC2Client
    from app.services.fact_collector import FactCollector
    from app.ws_manager import WebSocketManager

    # Insert vuln.cve fact with exploit=true for seeded target
    await seeded_db.execute(
        """INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score)
           VALUES (?, 'test-op-1', 'test-target-1',
                   'vuln.cve', 'CVE-2011-2523:vsftpd:vsftpd_2.3.4:cvss=10.0:exploit=true',
                   'vulnerability', 1)""",
        (str(uuid.uuid4()),)
    )
    # Insert a technique record for T1190
    await seeded_db.execute(
        """INSERT OR IGNORE INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
           VALUES ('tech-t1190', 'T1190', 'Exploit Public-Facing Application',
                   'Initial Access', 'TA0001', 'high')"""
    )
    await seeded_db.commit()

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
    cursor = await seeded_db.execute(
        "SELECT engine, status FROM technique_executions "
        "WHERE operation_id = 'test-op-1' ORDER BY started_at DESC LIMIT 1"
    )
    exec_row = await cursor.fetchone()
    assert exec_row is not None, "technique_executions row was not written"
    assert exec_row["engine"] == "metasploit"
    assert exec_row["status"] == "success"


async def test_engine_router_mcp_ssh_route():
    """EXECUTION_ENGINE=mcp_ssh routes to _execute_via_mcp_executor."""
    import aiosqlite
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services.engine_router import EngineRouter
    from app.clients.mock_c2_client import MockC2Client
    from app.services.fact_collector import FactCollector
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

    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            CREATE TABLE techniques (id TEXT PRIMARY KEY, mitre_id TEXT, name TEXT,
                tactic TEXT, tactic_id TEXT, kill_chain_stage TEXT, risk_level TEXT,
                c2_ability_id TEXT);
            CREATE TABLE technique_executions (id TEXT PRIMARY KEY, technique_id TEXT,
                target_id TEXT, operation_id TEXT, ooda_iteration_id TEXT,
                engine TEXT, status TEXT, started_at TEXT, completed_at TEXT,
                result_summary TEXT, facts_collected_count INTEGER DEFAULT 0,
                error_message TEXT);
            CREATE TABLE facts (id TEXT PRIMARY KEY, operation_id TEXT,
                source_target_id TEXT, category TEXT, trait TEXT, value TEXT,
                score INTEGER DEFAULT 1, collected_at TEXT, source TEXT);
            CREATE TABLE operations (id TEXT PRIMARY KEY, techniques_executed INTEGER DEFAULT 0);
            CREATE TABLE technique_playbooks (id TEXT PRIMARY KEY, mitre_id TEXT NOT NULL,
                platform TEXT NOT NULL DEFAULT 'linux', command TEXT NOT NULL,
                output_parser TEXT, facts_traits TEXT NOT NULL DEFAULT '[]',
                source TEXT DEFAULT 'seed', tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')));
            INSERT INTO techniques VALUES ('t1', 'T1592', 'Host Discovery',
                'Reconnaissance', 'TA0043', 'recon', 'low', 'T1592');
            CREATE TABLE targets (id TEXT PRIMARY KEY, hostname TEXT,
                ip_address TEXT, os TEXT, role TEXT, operation_id TEXT,
                is_compromised INTEGER DEFAULT 0, privilege_level TEXT,
                access_status TEXT DEFAULT 'unknown');
            INSERT INTO targets VALUES ('tgt-1', 'test-host', '127.0.0.1', 'Linux',
                'target', 'op-persist-test', 0, NULL, 'unknown');
            INSERT INTO operations VALUES ('op-persist-test', 0);
            INSERT INTO facts VALUES ('f1', 'op-persist-test', 'tgt-1', 'credential',
                'credential.ssh', 'root:toor@127.0.0.1:22', 1, '2026-01-01', 'test');
        """)
        await db.commit()

        with patch("app.services.engine_router.settings") as mock_settings:
            mock_settings.EXECUTION_ENGINE = "mcp_ssh"
            mock_settings.MOCK_C2_ENGINE = False
            mock_settings.MCP_ENABLED = True
            mock_settings.PERSISTENCE_ENABLED = False

            result = await router.execute(
                db=db,
                technique_id="T1592",
                target_id="tgt-1",
                engine="auto",
                operation_id="op-persist-test",
            )

    assert result["status"] == "success"
    assert result["engine"] == "mcp_ssh"
    mock_mcp.execute.assert_awaited_once()
    call_args = mock_mcp.execute.call_args
    assert call_args[0][0] == "attack-executor:execute_technique"

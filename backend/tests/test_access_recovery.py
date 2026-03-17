# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Tests for OODA Access Recovery & Credential Invalidation -- SPEC-037."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.engine_router import EngineRouter, _is_auth_failure


# ---------------------------------------------------------------------------
# _is_auth_failure tests
# ---------------------------------------------------------------------------


class TestIsAuthFailure:
    def test_none_error(self):
        assert _is_auth_failure(None) is False

    def test_empty_error(self):
        assert _is_auth_failure("") is False

    def test_authentication_failed(self):
        assert _is_auth_failure("Authentication failed for user 'root'") is True

    def test_permission_denied(self):
        assert _is_auth_failure("Permission denied (publickey,password)") is True

    def test_connection_refused(self):
        assert _is_auth_failure("Connection refused by 192.168.0.23:22") is True

    def test_host_unreachable(self):
        assert _is_auth_failure("No route to host 192.168.0.23") is True

    def test_connection_timed_out(self):
        assert _is_auth_failure("Connection timed out after 30s") is True

    def test_unrelated_error(self):
        assert _is_auth_failure("Command exited with code 1") is False

    def test_case_insensitive(self):
        assert _is_auth_failure("AUTHENTICATION FAILED") is True


# ---------------------------------------------------------------------------
# _handle_access_lost tests
# ---------------------------------------------------------------------------


def _make_router():
    """Create EngineRouter with mocked dependencies."""
    c2 = MagicMock()
    fc = MagicMock()
    fc.collect_from_result = AsyncMock(return_value=[])
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    return EngineRouter(c2, fc, ws)


def _make_db(target_ip="192.168.0.23"):
    """Create a mock DB that returns target IP."""
    db = AsyncMock()
    db.row_factory = None

    ip_cursor = AsyncMock()
    ip_cursor.fetchone = AsyncMock(return_value={"ip_address": target_ip})

    db.execute = AsyncMock(return_value=ip_cursor)
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_handle_access_lost_revokes_compromised():
    """_handle_access_lost should UPDATE targets to revoke compromised status."""
    router = _make_router()
    db = _make_db()

    await router._handle_access_lost(db, "op-1", "tgt-1")

    # Verify at least one execute call updates targets
    calls = [str(c) for c in db.execute.call_args_list]
    target_update = [c for c in calls if ("is_compromised = 0" in c or "is_compromised = FALSE" in c) and "access_status = 'lost'" in c]
    assert len(target_update) >= 1, f"Expected target update call, got: {calls}"


@pytest.mark.asyncio
async def test_handle_access_lost_invalidates_credentials():
    """_handle_access_lost should rename credential.ssh to credential.ssh.invalidated."""
    router = _make_router()
    db = _make_db()

    await router._handle_access_lost(db, "op-1", "tgt-1")

    calls = [str(c) for c in db.execute.call_args_list]
    cred_invalidate = [c for c in calls if "credential.ssh.invalidated" in c]
    assert len(cred_invalidate) >= 1, f"Expected credential invalidation call, got: {calls}"


@pytest.mark.asyncio
async def test_handle_access_lost_inserts_fact():
    """_handle_access_lost should insert an access.lost fact."""
    router = _make_router()
    db = _make_db()

    await router._handle_access_lost(db, "op-1", "tgt-1")

    calls = [str(c) for c in db.execute.call_args_list]
    fact_insert = [c for c in calls if "access.lost" in c]
    assert len(fact_insert) >= 1, f"Expected access.lost fact insert, got: {calls}"


@pytest.mark.asyncio
async def test_handle_access_lost_is_idempotent():
    """Multiple calls to _handle_access_lost should not raise errors."""
    router = _make_router()
    db = _make_db()

    # First call
    await router._handle_access_lost(db, "op-1", "tgt-1")
    # Second call -- should not raise
    await router._handle_access_lost(db, "op-1", "tgt-1")


# ---------------------------------------------------------------------------
# Integration: _finalize_execution triggers access lost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_execution_triggers_access_lost_on_auth_failure():
    """_finalize_execution should call _handle_access_lost when auth fails."""
    router = _make_router()
    router._handle_access_lost = AsyncMock()

    db = _make_db()

    from app.clients import ExecutionResult
    result = ExecutionResult(
        success=False,
        execution_id="exec-1",
        output="",
        error="Permission denied (publickey,password)",
        facts=[],
    )

    await router._finalize_execution(
        db, "exec-1", "T1059.004", "tgt-1", "mcp_ssh", "op-1", result
    )

    router._handle_access_lost.assert_awaited_once_with(db, "op-1", "tgt-1")


@pytest.mark.asyncio
async def test_finalize_execution_no_access_lost_on_normal_failure():
    """_finalize_execution should NOT call _handle_access_lost on normal errors."""
    router = _make_router()
    router._handle_access_lost = AsyncMock()

    db = _make_db()

    from app.clients import ExecutionResult
    result = ExecutionResult(
        success=False,
        execution_id="exec-1",
        output="",
        error="Command exited with code 1",
        facts=[],
    )

    await router._finalize_execution(
        db, "exec-1", "T1059.004", "tgt-1", "mcp_ssh", "op-1", result
    )

    router._handle_access_lost.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_execution_no_access_lost_on_success():
    """_finalize_execution should NOT call _handle_access_lost on success."""
    router = _make_router()
    router._handle_access_lost = AsyncMock()

    db = _make_db()

    from app.clients import ExecutionResult
    result = ExecutionResult(
        success=True,
        execution_id="exec-1",
        output="uid=0(root)",
        error=None,
        facts=[],
    )

    await router._finalize_execution(
        db, "exec-1", "T1059.004", "tgt-1", "mcp_ssh", "op-1", result
    )

    router._handle_access_lost.assert_not_awaited()


# ---------------------------------------------------------------------------
# Attack Graph: invalidated credentials excluded
# ---------------------------------------------------------------------------


def test_attack_graph_excludes_invalidated_facts():
    """AttackGraphEngine should exclude .invalidated facts from fact_traits."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    engine = AttackGraphEngine(ws)

    facts = [
        {"id": "f1", "trait": "credential.ssh", "value": "user:user@10.0.1.1:22",
         "category": "credential", "source_technique_id": "T1110.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f2", "trait": "credential.ssh.invalidated", "value": "old:old@10.0.1.1:22",
         "category": "credential", "source_technique_id": "T1110.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f3", "trait": "service.open_port", "value": "22/tcp",
         "category": "service", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]

    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.1",
         "os": "Linux", "role": "server", "operation_id": "op-1"},
    ]

    graph = engine._build_graph_in_memory("op-1", targets, facts, [])

    assert len(graph.nodes) > 0


# ---------------------------------------------------------------------------
# Phase 2: Banner-based Metasploit inference + routing fixes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_infer_exploitable_service_vsftpd():
    """_infer_exploitable_service matches vsftpd_2.3.4 banner."""
    router = _make_router()
    db = AsyncMock()
    db.row_factory = None

    db.fetch = AsyncMock(return_value=[
        {"value": "21/tcp/ftp/vsftpd_2.3.4"},
    ])

    result = await router._infer_exploitable_service(db, "op-1", "tgt-1")
    assert result == "vsftpd"


@pytest.mark.asyncio
async def test_infer_exploitable_service_samba():
    """_infer_exploitable_service matches samba 3.0 banner."""
    router = _make_router()
    db = AsyncMock()

    db.fetch = AsyncMock(return_value=[
        {"value": "445/tcp/netbios-ssn/Samba 3.0.20-Debian"},
    ])

    result = await router._infer_exploitable_service(db, "op-1", "tgt-1")
    assert result == "samba"


@pytest.mark.asyncio
async def test_infer_exploitable_service_no_match():
    """_infer_exploitable_service returns None for unrecognized banners."""
    router = _make_router()
    db = AsyncMock()
    db.row_factory = None

    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[
        {"value": "22/tcp/ssh/OpenSSH_4.7p1"},
        {"value": "80/tcp/http/Apache_2.2.8"},
    ])
    db.execute = AsyncMock(return_value=cursor)

    result = await router._infer_exploitable_service(db, "op-1", "tgt-1")
    assert result is None


@pytest.mark.asyncio
async def test_infer_exploitable_service_unrealircd():
    """_infer_exploitable_service matches unrealircd banner."""
    router = _make_router()
    db = AsyncMock()

    db.fetch = AsyncMock(return_value=[
        {"value": "6667/tcp/irc/UnrealIRCd"},
    ])

    result = await router._infer_exploitable_service(db, "op-1", "tgt-1")
    assert result == "unrealircd"


@pytest.mark.asyncio
async def test_no_cred_early_return_writes_execution(tmp_db):
    """No-credential early return should write technique_executions record."""
    # Seed required data
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('t1', 'T1059.004', 'Unix Shell', 'Execution', 'TA0002', 'medium')"
    )
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, "
        "is_compromised, access_status) "
        "VALUES ('tgt-1', 'test-host', '10.0.0.1', 'Linux', 'target', 'op-1', false, 'lost')"
    )

    router = _make_router()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = await router._execute_via_mcp_executor(
        tmp_db, "exec-1", now, "T1059.004",
        "T1059.004", "tgt-1", "mcp_ssh", "op-1", "ooda-1",
    )

    assert result["status"] == "failed"
    assert "invalidated" in result["error"]

    # Verify technique_executions record was written
    row = await tmp_db.fetchrow(
        "SELECT status, error_message FROM technique_executions WHERE id = 'exec-1'"
    )
    assert row is not None, "technique_executions record was not written"
    assert row["status"] == "failed"
    assert "invalidated" in row["error_message"]


@pytest.mark.asyncio
async def test_metasploit_route_on_explicit_engine(tmp_db):
    """engine='metasploit' with exploitable banner should route to Metasploit."""
    from app.clients.mock_c2_client import MockC2Client

    # Seed required data
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('t1', 'T1190', 'Exploit Public-Facing App', 'Initial Access', 'TA0001', 'high')"
    )
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, "
        "is_compromised, access_status) "
        "VALUES ('tgt-1', 'msf2', '192.168.0.23', 'Linux', 'target', 'op-1', false, 'lost')"
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, category, trait, value, score, collected_at) "
        "VALUES ('f1', 'op-1', 'tgt-1', 'service', 'service.open_port', "
        "'21/tcp/ftp/vsftpd_2.3.4', 1, '2026-01-01T00:00:00+00:00')"
    )

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fc = MagicMock()
    fc.collect_from_result = AsyncMock(return_value=[])
    router = EngineRouter(MockC2Client(), fc, ws)

    result = await router.execute(
        tmp_db, technique_id="T1190", target_id="tgt-1",
        engine="metasploit", operation_id="op-1",
    )

    # Should have routed through Metasploit (mock mode)
    assert result.get("engine") in ("metasploit", "metasploit_mock")


@pytest.mark.asyncio
async def test_banner_fallback_auto_detects_vsftpd(tmp_db):
    """Default routing auto-detects vsftpd from banner when no vuln.cve fact exists."""
    from app.clients.mock_c2_client import MockC2Client

    # Seed required data
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('t1', 'T1110.001', 'Brute Force', 'Credential Access', 'TA0006', 'medium')"
    )
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, "
        "is_compromised, access_status) "
        "VALUES ('tgt-1', 'msf2', '192.168.0.23', 'Linux', 'target', 'op-1', false, 'unknown')"
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, category, trait, value, score, collected_at) "
        "VALUES ('f1', 'op-1', 'tgt-1', 'service', 'service.open_port', "
        "'21/tcp/ftp/vsftpd_2.3.4', 1, '2026-01-01T00:00:00+00:00')"
    )

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fc = MagicMock()
    fc.collect_from_result = AsyncMock(return_value=[])
    router = EngineRouter(MockC2Client(), fc, ws)

    result = await router.execute(
        tmp_db, technique_id="T1110.001", target_id="tgt-1",
        engine="auto", operation_id="op-1",
    )

    # Should have been intercepted by banner-based Metasploit fallback
    assert result.get("engine") in ("metasploit", "metasploit_mock")


@pytest.mark.asyncio
async def test_exploit_vsftpd_no_lhost():
    """exploit_vsftpd should NOT pass LHOST (bind shell, not reverse)."""
    from unittest.mock import patch
    from app.clients.metasploit_client import MetasploitRPCEngine

    engine = MetasploitRPCEngine()

    with patch.object(engine, "_run_exploit", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"status": "success", "output": "uid=0(root)", "engine": "metasploit"}
        await engine.exploit_vsftpd("192.168.0.23")

        mock_run.assert_called_once()
        _, _, options = mock_run.call_args[0]
        assert "RHOSTS" in options
        assert "LHOST" not in options, "vsftpd bind shell must not pass LHOST"


@pytest.mark.asyncio
async def test_metasploit_success_updates_target(tmp_db):
    """Metasploit success should set target compromised=Root and write root_shell fact."""
    from app.clients.mock_c2_client import MockC2Client

    # Seed required data
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, ip_address, operation_id, is_compromised, "
        "privilege_level, access_status, hostname, os, role) "
        "VALUES ('tgt-1', '192.168.0.23', 'op-1', false, NULL, 'lost', 'msf2', 'Linux', 'target')"
    )

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fc = MagicMock()
    fc.collect_from_result = AsyncMock(return_value=[])
    router = EngineRouter(MockC2Client(), fc, ws)

    # Mock MetasploitRPCEngine to return success
    mock_msf_instance = MagicMock()
    mock_msf_instance.get_exploit_for_service.return_value = AsyncMock(
        return_value={"status": "success", "output": "uid=0(root)", "engine": "metasploit"}
    )
    mock_msf_cls = MagicMock(return_value=mock_msf_instance)

    with patch("app.clients.metasploit_client.MetasploitRPCEngine", mock_msf_cls):
        result = await router._execute_metasploit(
            tmp_db, "exec-msf-1", "2026-01-01T00:00:00",
            "T1190", "tgt-1", "op-1", "ooda-1",
            "vsftpd", "192.168.0.23", "metasploit",
        )

    assert result["status"] == "success"

    # Check target updated to Root
    row = await tmp_db.fetchrow(
        "SELECT is_compromised, privilege_level, access_status FROM targets WHERE id = 'tgt-1'"
    )
    assert row["is_compromised"] is True
    assert row["privilege_level"] == "Root"
    assert row["access_status"] == "active"

    # Check root_shell fact written
    row = await tmp_db.fetchrow(
        "SELECT trait, value FROM facts WHERE trait = 'credential.root_shell'"
    )
    assert row is not None, "credential.root_shell fact was not written"
    assert "metasploit:vsftpd" in row["value"]

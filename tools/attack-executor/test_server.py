"""Tests for attack-executor MCP server — SSH and WinRM technique execution."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# SSH — direct execution
# ---------------------------------------------------------------------------

async def test_execute_technique_ssh_mock():
    """SSH execution with mocked asyncssh returns success + facts."""
    mock_result = MagicMock()
    mock_result.stdout = "Linux host 5.15.0 #1 SMP x86_64"
    mock_result.stderr = ""
    mock_result.exit_status = 0

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("asyncssh.connect", return_value=mock_ctx):
        from server import execute_technique

        result_str = await execute_technique(
            technique_id="T1592",
            credential="root:password@10.0.0.1:22",
            protocol="ssh",
        )

    data = json.loads(result_str)
    assert data["success"] is True
    assert len(data["facts"]) >= 1
    assert data["facts"][0]["trait"] in ("host.os", "host.user")
    assert "Linux" in data["raw_output"]


# ---------------------------------------------------------------------------
# WinRM execution
# ---------------------------------------------------------------------------

async def test_execute_technique_winrm_mock():
    """WinRM execution with mocked pywinrm returns success."""
    mock_response = MagicMock()
    mock_response.std_out = b"DOMAIN\\admin\r\nCOMP-01"
    mock_response.std_err = b""
    mock_response.status_code = 0

    mock_session = MagicMock()
    mock_session.run_ps.return_value = mock_response

    with patch.dict("sys.modules", {"winrm": MagicMock()}) as _:
        import sys
        winrm_mod = sys.modules["winrm"]
        winrm_mod.Session.return_value = mock_session

        from server import execute_technique

        result_str = await execute_technique(
            technique_id="T1021.001",
            credential="admin:pass@10.0.0.1:5985",
            protocol="winrm",
        )

    data = json.loads(result_str)
    assert data["success"] is True
    assert "DOMAIN" in data["raw_output"]


# ---------------------------------------------------------------------------
# Unknown technique
# ---------------------------------------------------------------------------

async def test_execute_technique_unknown_id():
    """Unknown technique_id returns error."""
    from server import execute_technique

    result_str = await execute_technique(
        technique_id="T9999.999",
        credential="root:pass@10.0.0.1:22",
        protocol="ssh",
    )

    data = json.loads(result_str)
    assert data["success"] is False
    assert "error" in data
    assert "T9999.999" in data["error"]


# ---------------------------------------------------------------------------
# Close sessions
# ---------------------------------------------------------------------------

async def test_close_sessions():
    """close_sessions clears pool entries for a given key."""
    from server import _SESSION_POOL, _SESSION_LOCKS, _SESSION_LAST_USED, close_sessions

    # Plant fake sessions
    mock_conn = MagicMock()
    _SESSION_POOL[("op-123", "cred-a")] = mock_conn
    _SESSION_POOL[("op-123", "cred-b")] = mock_conn
    _SESSION_POOL[("op-456", "cred-c")] = mock_conn

    result_str = await close_sessions(session_key="op-123")
    data = json.loads(result_str)

    assert data["closed"] == 2
    assert ("op-123", "cred-a") not in _SESSION_POOL
    assert ("op-123", "cred-b") not in _SESSION_POOL
    # Other operation's sessions untouched
    assert ("op-456", "cred-c") in _SESSION_POOL

    # Cleanup
    _SESSION_POOL.clear()
    _SESSION_LOCKS.clear()
    _SESSION_LAST_USED.clear()


# ---------------------------------------------------------------------------
# Persistent session reuse
# ---------------------------------------------------------------------------

async def test_persistent_session_reuse():
    """Second call with same session_key reuses the pooled connection."""
    import asyncio
    from server import _SESSION_POOL, _SESSION_LOCKS, _SESSION_LAST_USED

    mock_result = MagicMock()
    mock_result.stdout = "root"
    mock_result.stderr = ""
    mock_result.exit_status = 0

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_conn.close = MagicMock()

    connect_count = 0
    original_connect = None

    async def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return mock_conn

    with patch("asyncssh.connect", side_effect=counting_connect):
        from server import execute_technique

        # First call — should create new session
        await execute_technique(
            technique_id="T1021.004",
            credential="root:pass@10.0.0.1:22",
            protocol="ssh",
            persistent_session_key="op-test",
        )
        assert connect_count == 1

        # Second call — should reuse session
        await execute_technique(
            technique_id="T1087",
            credential="root:pass@10.0.0.1:22",
            protocol="ssh",
            persistent_session_key="op-test",
        )
        # Should still be 1 because connection is reused
        assert connect_count == 1

    # Cleanup
    _SESSION_POOL.clear()
    _SESSION_LOCKS.clear()
    _SESSION_LAST_USED.clear()

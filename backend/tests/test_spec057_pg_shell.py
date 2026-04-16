"""SPEC-057 — PostgreSQL COPY TO PROGRAM Shell Escalation.

Tests that:
- postgresql_exec_check MCP tool exists and is callable
- InitialAccessEngine triggers escalation after PostgreSQL credential success
- credential.shell fact is in _SHELL_CAPABLE_TRAITS (compromise gate)
- Failure is non-fatal (credential.postgresql still valid)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── T06: credential.shell is in _SHELL_CAPABLE_TRAITS ──────────────

def test_credential_shell_in_shell_capable_traits():
    """credential.shell must be in _SHELL_CAPABLE_TRAITS to trigger compromise gate."""
    from app.services.ooda_controller import _SHELL_CAPABLE_TRAITS
    assert "credential.shell" in _SHELL_CAPABLE_TRAITS


# ─── T04: InitialAccessEngine triggers escalation ───────────────────

@pytest.mark.asyncio
async def test_postgresql_credential_triggers_escalation():
    """After PostgreSQL credential success, _try_postgresql_shell_escalation is called."""
    from app.services.initial_access_engine import InitialAccessEngine

    engine = InitialAccessEngine()

    mock_mgr = MagicMock()
    mock_mgr.is_connected.return_value = True
    # First call: credential check returns success
    # Second call: exec check returns shell fact
    mock_mgr.call_tool = AsyncMock(side_effect=[
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.postgresql", "value": "postgres:@host:5432"}],
            "raw_output": "PostgreSQL auth success",
        })}]},
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.shell", "value": "postgresql_copy_exec:postgres:@host:5432 (uid=0(root))"}],
            "raw_output": "PostgreSQL COPY TO PROGRAM success",
        })}]},
    ])

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mgr):
        mock_db = AsyncMock()
        mock_db.fetchval = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()
        mock_db.fetch = AsyncMock(return_value=[])

        result = await engine._try_mcp_credential_check(
            mock_db, "op-1", "tgt-1", "192.168.0.26",
            protocol="postgresql", mcp_tool="postgresql_credential_check",
            trait="credential.postgresql", creds_key="postgresql", port=5432,
        )

        assert result.success is True
        assert result.method == "postgresql_credential"

        # Verify postgresql_exec_check was called (second call_tool invocation)
        assert mock_mgr.call_tool.call_count == 2
        second_call = mock_mgr.call_tool.call_args_list[1]
        assert second_call[0][1] == "postgresql_exec_check"


# ─── T05: MCP unavailable — escalation skipped silently ─────────────

@pytest.mark.asyncio
async def test_postgresql_escalation_skipped_when_mcp_unavailable():
    """If MCP call fails, escalation is skipped but credential.postgresql is still valid."""
    from app.services.initial_access_engine import InitialAccessEngine

    engine = InitialAccessEngine()

    mock_mgr = MagicMock()
    mock_mgr.is_connected.return_value = True
    # First call: credential check success
    # Second call: exec check throws exception
    mock_mgr.call_tool = AsyncMock(side_effect=[
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.postgresql", "value": "postgres:@host:5432"}],
            "raw_output": "PostgreSQL auth success",
        })}]},
        Exception("MCP connection lost"),
    ])

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mgr):
        mock_db = AsyncMock()
        mock_db.fetchval = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()
        mock_db.fetch = AsyncMock(return_value=[])

        result = await engine._try_mcp_credential_check(
            mock_db, "op-1", "tgt-1", "192.168.0.26",
            protocol="postgresql", mcp_tool="postgresql_credential_check",
            trait="credential.postgresql", creds_key="postgresql", port=5432,
        )

        # Still returns success (credential.postgresql is valid)
        assert result.success is True
        assert result.method == "postgresql_credential"


# ─── T02: Non-superuser — no shell fact ─────────────────────────────

@pytest.mark.asyncio
async def test_postgresql_escalation_denied_non_superuser():
    """COPY TO PROGRAM denied → no credential.shell written, but credential still valid."""
    from app.services.initial_access_engine import InitialAccessEngine

    engine = InitialAccessEngine()

    mock_mgr = MagicMock()
    mock_mgr.is_connected.return_value = True
    mock_mgr.call_tool = AsyncMock(side_effect=[
        # credential check success
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.postgresql", "value": "admin:@host:5432"}],
            "raw_output": "PostgreSQL auth success",
        })}]},
        # exec check: denied (empty facts)
        {"content": [{"text": json.dumps({
            "facts": [],
            "raw_output": "PostgreSQL COPY TO PROGRAM denied: must be superuser",
        })}]},
    ])

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mgr):
        mock_db = AsyncMock()
        mock_db.fetchval = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()
        mock_db.fetch = AsyncMock(return_value=[])

        result = await engine._try_mcp_credential_check(
            mock_db, "op-1", "tgt-1", "192.168.0.26",
            protocol="postgresql", mcp_tool="postgresql_credential_check",
            trait="credential.postgresql", creds_key="postgresql", port=5432,
        )

        assert result.success is True
        # credential.postgresql fact was written (first call)
        # but credential.shell was NOT written (second call returned empty facts)
        shell_writes = [
            c for c in mock_db.execute.call_args_list
            if "credential.shell" in str(c)
        ]
        assert len(shell_writes) == 0


# ─── T01: Superuser — shell fact written ────────────────────────────

@pytest.mark.asyncio
async def test_postgresql_escalation_success_writes_shell_fact():
    """COPY TO PROGRAM success → credential.shell fact written."""
    from app.services.initial_access_engine import InitialAccessEngine

    engine = InitialAccessEngine()

    mock_mgr = MagicMock()
    mock_mgr.is_connected.return_value = True
    mock_mgr.call_tool = AsyncMock(side_effect=[
        # credential check success
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.postgresql", "value": "postgres:@host:5432"}],
            "raw_output": "PostgreSQL auth success",
        })}]},
        # exec check: success with shell
        {"content": [{"text": json.dumps({
            "facts": [{"trait": "credential.shell", "value": "postgresql_copy_exec:postgres:@host:5432 (uid=0(root))"}],
            "raw_output": "PostgreSQL COPY TO PROGRAM success: id → uid=0(root)",
        })}]},
    ])

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mgr):
        mock_db = AsyncMock()
        mock_db.fetchval = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()
        mock_db.fetch = AsyncMock(return_value=[])

        await engine._try_mcp_credential_check(
            mock_db, "op-1", "tgt-1", "192.168.0.26",
            protocol="postgresql", mcp_tool="postgresql_credential_check",
            trait="credential.postgresql", creds_key="postgresql", port=5432,
        )

        # credential.shell fact should have been written
        shell_writes = [
            c for c in mock_db.execute.call_args_list
            if "credential.shell" in str(c)
        ]
        assert len(shell_writes) == 1
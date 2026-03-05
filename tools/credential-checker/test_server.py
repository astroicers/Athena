"""Tests for credential-checker MCP server — SSH, RDP, WinRM handlers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# SSH
# ---------------------------------------------------------------------------

async def test_ssh_check_success():
    """Successful SSH login returns credential.ssh fact."""
    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="uid=0(root)"))

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("asyncssh.connect", return_value=mock_ctx):
        from server import ssh_credential_check

        result_str = await ssh_credential_check(
            target="10.0.0.1", username="admin", password="secret"
        )

    data = json.loads(result_str)
    assert len(data["facts"]) == 1
    assert data["facts"][0]["trait"] == "credential.ssh"
    assert "admin" in data["facts"][0]["value"]


async def test_ssh_check_auth_failure():
    """Auth failure returns empty facts."""
    import asyncssh

    with patch("asyncssh.connect", side_effect=asyncssh.PermissionDenied("")):
        from server import ssh_credential_check

        result_str = await ssh_credential_check(
            target="10.0.0.1", username="admin", password="wrong"
        )

    data = json.loads(result_str)
    assert data["facts"] == []
    assert "auth_failure" in data["raw_output"]


# ---------------------------------------------------------------------------
# RDP
# ---------------------------------------------------------------------------

async def test_rdp_check_success():
    """Successful RDP auth returns credential.rdp fact."""
    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        from server import rdp_credential_check

        result_str = await rdp_credential_check(
            target="10.0.0.1", username="Administrator", password="P@ssw0rd"
        )

    data = json.loads(result_str)
    assert len(data["facts"]) == 1
    assert data["facts"][0]["trait"] == "credential.rdp"
    assert "Administrator" in data["facts"][0]["value"]


async def test_rdp_check_auth_failure():
    """RDP auth failure returns empty facts."""
    proc = AsyncMock()
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", b"auth failed"))

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        from server import rdp_credential_check

        result_str = await rdp_credential_check(
            target="10.0.0.1", username="admin", password="wrong"
        )

    data = json.loads(result_str)
    assert data["facts"] == []
    assert "auth_failure" in data["raw_output"]


# ---------------------------------------------------------------------------
# WinRM
# ---------------------------------------------------------------------------

async def test_winrm_check_success():
    """Successful WinRM auth returns credential.winrm fact."""
    mock_result = MagicMock()
    mock_result.status_code = 0
    mock_result.std_out = b"DOMAIN\\admin"

    mock_session = MagicMock()
    mock_session.run_ps.return_value = mock_result

    with patch.dict("sys.modules", {"winrm": MagicMock()}):
        import sys
        winrm_mod = sys.modules["winrm"]
        winrm_mod.Session.return_value = mock_session

        from server import _winrm_handler
        result = await _winrm_handler("10.0.0.1", "admin", "pass", 5985, 10)

    assert len(result["facts"]) == 1
    assert result["facts"][0]["trait"] == "credential.winrm"


async def test_winrm_check_auth_failure():
    """WinRM auth failure returns empty facts."""
    mock_result = MagicMock()
    mock_result.status_code = 1
    mock_result.std_out = b""

    mock_session = MagicMock()
    mock_session.run_ps.return_value = mock_result

    with patch.dict("sys.modules", {"winrm": MagicMock()}):
        import sys
        winrm_mod = sys.modules["winrm"]
        winrm_mod.Session.return_value = mock_session

        from server import _winrm_handler
        result = await _winrm_handler("10.0.0.1", "admin", "wrong", 5985, 10)

    assert result["facts"] == []
    assert "auth_failure" in result["raw_output"]

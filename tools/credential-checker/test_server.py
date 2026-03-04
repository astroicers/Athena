"""Tests for credential-checker MCP server."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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


async def test_ssh_check_connection_error():
    """Connection error returns empty facts with error message."""
    with patch("asyncssh.connect", side_effect=ConnectionRefusedError("refused")):
        from server import ssh_credential_check

        result_str = await ssh_credential_check(
            target="10.0.0.1", username="admin", password="secret"
        )

    data = json.loads(result_str)
    assert data["facts"] == []
    assert "error" in data["raw_output"].lower()

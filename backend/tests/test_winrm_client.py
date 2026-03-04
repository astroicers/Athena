# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for WinRMEngine (WinRM mock mode + credential parsing)."""
import pytest


@pytest.mark.asyncio
async def test_winrm_mock_returns_success():
    """WINRM_ENABLED=false → WinRMEngine returns mock success result."""
    from app.clients.winrm_client import WinRMEngine
    engine = WinRMEngine()
    result = await engine.execute("T1021.001", "admin:pass@10.0.0.1:5985")
    assert result.success is True
    assert "MOCK" in result.output


def test_parse_winrm_credential_valid():
    """_parse_winrm_credential correctly parses user:pass@host:port."""
    from app.clients.winrm_client import _parse_winrm_credential
    user, pw, host, port = _parse_winrm_credential("admin:P@ss!@10.0.1.5:5985")
    assert user == "admin"
    assert pw == "P@ss!"
    assert host == "10.0.1.5"
    assert port == 5985


def test_parse_winrm_credential_default_port():
    """No port → defaults to 5985."""
    from app.clients.winrm_client import _parse_winrm_credential
    _, _, _, port = _parse_winrm_credential("admin:pass@10.0.0.1")
    assert port == 5985


def test_winrm_technique_executors_has_windows_techniques():
    """WINRM_TECHNIQUE_EXECUTORS should include T1021.001 and T1053.005."""
    from app.clients.winrm_client import WINRM_TECHNIQUE_EXECUTORS
    assert "T1021.001" in WINRM_TECHNIQUE_EXECUTORS
    assert "T1053.005" in WINRM_TECHNIQUE_EXECUTORS

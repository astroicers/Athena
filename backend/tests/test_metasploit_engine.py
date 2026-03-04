# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for MetasploitRPCEngine (ADR-019)."""
import pytest
from unittest.mock import patch

from app.clients.metasploit_client import MetasploitRPCEngine


async def test_vsftpd_exploit_mock_mode():
    """MOCK_METASPLOIT=true: vsftpd exploit returns mock success."""
    engine = MetasploitRPCEngine()
    result = await engine.exploit_vsftpd("192.168.1.1")
    assert result["status"] == "success"
    assert "shell" in result
    assert result["engine"] == "metasploit_mock"
    assert result["module"] == "exploit/unix/ftp/vsftpd_234_backdoor"


async def test_unrealircd_exploit_mock_mode():
    """MOCK_METASPLOIT=true: UnrealIRCd exploit returns mock success."""
    result = await MetasploitRPCEngine().exploit_unrealircd("192.168.1.1")
    assert result["status"] == "success"
    assert "shell" in result


async def test_samba_exploit_mock_mode():
    """MOCK_METASPLOIT=true: Samba exploit returns mock success."""
    result = await MetasploitRPCEngine().exploit_samba("192.168.1.1")
    assert result["status"] == "success"
    assert "shell" in result


async def test_winrm_login_mock_mode():
    """MOCK_METASPLOIT=true: WinRM login returns mock success."""
    result = await MetasploitRPCEngine().exploit_winrm("192.168.1.1", "administrator", "Password1!")
    assert result["status"] == "success"
    assert "shell" in result


async def test_get_exploit_for_service_maps_correctly():
    """get_exploit_for_service maps known services to methods."""
    engine = MetasploitRPCEngine()
    assert engine.get_exploit_for_service("vsftpd") is not None
    assert engine.get_exploit_for_service("unrealircd") is not None
    assert engine.get_exploit_for_service("samba") is not None
    assert engine.get_exploit_for_service("winrm") is not None
    assert engine.get_exploit_for_service("unknown_xyz") is None


async def test_get_exploit_for_service_case_insensitive():
    """get_exploit_for_service handles case-insensitive matching."""
    engine = MetasploitRPCEngine()
    assert engine.get_exploit_for_service("VSFTPD") is not None
    assert engine.get_exploit_for_service("Samba SMBv1") is not None
    assert engine.get_exploit_for_service("WinRM Service") is not None
    assert engine.get_exploit_for_service("UnrealIRCd 3.2.8.1") is not None

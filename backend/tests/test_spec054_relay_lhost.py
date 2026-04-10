# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — metasploit_client exploit methods read LHOST from settings.

Verifies that:
  1. exploit_samba / exploit_unrealircd read LHOST from settings.RELAY_IP
     (no longer hardcoded to "0.0.0.0")
  2. exploit_vsftpd remains a bind shell (no LHOST in options)
  3. All exploit methods accept probe_cmd keyword-only parameter and
     passthrough to _run_exploit (SPEC-053 one-shot terminal path)
  4. Degraded mode: empty RELAY_IP -> LHOST fallback to "0.0.0.0" with
     warning, no crash
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.clients.metasploit_client import MetasploitRPCEngine


# ---------------------------------------------------------------------------
# T01: exploit_samba reads RELAY_IP as LHOST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t01_exploit_samba_uses_relay_ip_as_lhost() -> None:
    """SPEC-054 S1: exploit_samba LHOST comes from settings.RELAY_IP."""
    engine = MetasploitRPCEngine()

    captured_options: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_options.update(options)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_samba("192.168.0.26")

    assert captured_options.get("LHOST") == "192.168.0.100", (
        f"Expected LHOST=192.168.0.100, got {captured_options.get('LHOST')}"
    )
    assert captured_options.get("RHOSTS") == "192.168.0.26"


@pytest.mark.asyncio
async def test_t01_exploit_unrealircd_uses_relay_ip_as_lhost() -> None:
    """SPEC-054 S1: exploit_unrealircd LHOST comes from settings.RELAY_IP."""
    engine = MetasploitRPCEngine()

    captured_options: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_options.update(options)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_unrealircd("192.168.0.26")

    assert captured_options.get("LHOST") == "192.168.0.100"
    assert captured_options.get("RHOSTS") == "192.168.0.26"


# ---------------------------------------------------------------------------
# T02: exploit_vsftpd remains bind shell (no LHOST)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t02_exploit_vsftpd_has_no_lhost() -> None:
    """SPEC-054 S2: exploit_vsftpd is bind shell, options must NOT contain LHOST."""
    engine = MetasploitRPCEngine()

    captured_options: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_options.update(options)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        # Even if RELAY_IP is set, vsftpd must not pick it up
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_vsftpd("192.168.0.26")

    assert "LHOST" not in captured_options, (
        f"exploit_vsftpd is bind shell; LHOST must not be set. "
        f"Got: {captured_options}"
    )
    assert captured_options.get("RHOSTS") == "192.168.0.26"


# ---------------------------------------------------------------------------
# T03: All exploit methods support probe_cmd passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t03_exploit_samba_passes_probe_cmd() -> None:
    """SPEC-054 B3: probe_cmd keyword passthrough for terminal re-exploit."""
    engine = MetasploitRPCEngine()

    captured_kwargs: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_kwargs.update(kwargs)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_samba("192.168.0.26", probe_cmd="whoami")

    assert captured_kwargs.get("probe_cmd") == "whoami"


@pytest.mark.asyncio
async def test_t03_exploit_vsftpd_passes_probe_cmd() -> None:
    """SPEC-054 B3: vsftpd also honors probe_cmd (needed by terminal re-exploit)."""
    engine = MetasploitRPCEngine()

    captured_kwargs: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_kwargs.update(kwargs)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_vsftpd("192.168.0.26", probe_cmd="id")

    assert captured_kwargs.get("probe_cmd") == "id"


@pytest.mark.asyncio
async def test_t03_exploit_unrealircd_passes_probe_cmd() -> None:
    """SPEC-054 B3: unrealircd also honors probe_cmd."""
    engine = MetasploitRPCEngine()

    captured_kwargs: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_kwargs.update(kwargs)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_unrealircd("192.168.0.26", probe_cmd="uname -a")

    assert captured_kwargs.get("probe_cmd") == "uname -a"


# ---------------------------------------------------------------------------
# T04 / N3: Degraded mode — empty RELAY_IP falls back to "0.0.0.0"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_n3_empty_relay_ip_degrades_to_zero_zero_zero_zero() -> None:
    """SPEC-054 S6: RELAY_IP='' -> LHOST='0.0.0.0', no crash, warning logged."""
    engine = MetasploitRPCEngine()

    captured_options: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_options.update(options)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = ""
        mock_settings.MOCK_METASPLOIT = False
        # Must not raise
        await engine.exploit_samba("192.168.0.26")

    assert captured_options.get("LHOST") == "0.0.0.0", (
        f"Empty RELAY_IP should degrade to 0.0.0.0. "
        f"Got: {captured_options.get('LHOST')}"
    )


@pytest.mark.asyncio
async def test_explicit_lhost_override_still_works() -> None:
    """Explicit lhost= argument still overrides settings (backward compat)."""
    engine = MetasploitRPCEngine()

    captured_options: dict = {}

    async def fake_run_exploit(module, payload, options, **kwargs):
        captured_options.update(options)
        return {"status": "success", "engine": "metasploit"}

    with patch.object(engine, "_run_exploit", side_effect=fake_run_exploit), \
         patch("app.clients.metasploit_client.settings") as mock_settings:
        mock_settings.RELAY_IP = "10.0.0.1"  # Should be ignored
        mock_settings.MOCK_METASPLOIT = False
        await engine.exploit_samba("192.168.0.26", lhost="172.16.0.1")

    assert captured_options.get("LHOST") == "172.16.0.1"

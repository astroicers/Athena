# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — engine_router._execute_metasploit logs LHOST value.

This is a minimal contract: _execute_metasploit must emit a log line
that includes the LHOST value (either the relay IP or the degraded
fallback string) so operators can audit what the metasploit module
saw per execution.

The actual LHOST injection happens in metasploit_client (see
test_spec054_relay_lhost.py). Here we only verify that engine_router
logs what it is about to pass through.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T01: _execute_metasploit logs lhost= value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t01_execute_metasploit_logs_lhost_from_settings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """engine_router must log lhost=<settings.RELAY_IP> when running metasploit."""
    from app.services.engine_router import EngineRouter

    router = EngineRouter.__new__(EngineRouter)
    router._ws = MagicMock()
    router._ws.broadcast = AsyncMock()
    router._fact_collector = MagicMock()

    # Stub DB connection
    db = MagicMock()
    db.execute = AsyncMock()
    db.fetchrow = AsyncMock()

    with patch(
        "app.clients.metasploit_client.MetasploitRPCEngine",
        autospec=True,
    ) as mock_engine_cls, patch(
        "app.services.engine_router.settings",
    ) as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.PERSISTENCE_ENABLED = False

        mock_engine = mock_engine_cls.return_value

        async def fake_exploit(target_ip, **kwargs):
            return {
                "status": "success",
                "output": "uid=0(root)",
                "engine": "metasploit",
            }

        mock_engine.get_exploit_for_service.return_value = fake_exploit

        caplog.set_level(logging.INFO, logger="app.services.engine_router")

        try:
            await router._execute_metasploit(
                db=db,
                exec_id="exec-1",
                now="2026-04-10T00:00:00+00:00",
                technique_id="T1190",
                target_id="tgt-1",
                operation_id="op-1",
                ooda_iteration_id="ooda-1",
                service_name="samba",
                target_ip="192.168.0.26",
                engine="metasploit",
            )
        except Exception:
            # We don't care about downstream DB bookkeeping failing in this
            # minimal stub setup — only that the log line with lhost= is
            # emitted before the failure.
            pass

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "lhost=192.168.0.100" in log_text, (
        f"engine_router must log 'lhost=<value>' to audit metasploit "
        f"LHOST per execution. Captured log:\n{log_text}"
    )


@pytest.mark.asyncio
async def test_t01_execute_metasploit_logs_lhost_degraded_when_relay_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When RELAY_IP is empty, log shows the degraded sentinel."""
    from app.services.engine_router import EngineRouter

    router = EngineRouter.__new__(EngineRouter)
    router._ws = MagicMock()
    router._ws.broadcast = AsyncMock()
    router._fact_collector = MagicMock()

    db = MagicMock()
    db.execute = AsyncMock()
    db.fetchrow = AsyncMock()

    with patch(
        "app.clients.metasploit_client.MetasploitRPCEngine",
        autospec=True,
    ) as mock_engine_cls, patch(
        "app.services.engine_router.settings",
    ) as mock_settings:
        mock_settings.RELAY_IP = ""
        mock_settings.PERSISTENCE_ENABLED = False

        mock_engine = mock_engine_cls.return_value

        async def fake_exploit(target_ip, **kwargs):
            return {
                "status": "failed",
                "reason": "no session within 60s",
                "engine": "metasploit",
            }

        mock_engine.get_exploit_for_service.return_value = fake_exploit

        caplog.set_level(logging.INFO, logger="app.services.engine_router")

        try:
            await router._execute_metasploit(
                db=db,
                exec_id="exec-2",
                now="2026-04-10T00:00:00+00:00",
                technique_id="T1190",
                target_id="tgt-1",
                operation_id="op-1",
                ooda_iteration_id="ooda-1",
                service_name="samba",
                target_ip="192.168.0.26",
                engine="metasploit",
            )
        except Exception:
            pass

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    # Degraded mode shows (none/bind) or empty-value marker — we accept
    # either as long as it's not a real IP.
    assert "lhost=" in log_text, (
        f"engine_router must emit lhost= in log even when RELAY_IP is empty. "
        f"Captured:\n{log_text}"
    )
    assert "192.168.0.100" not in log_text

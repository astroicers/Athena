# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for Phase D — PersistentSSHChannelEngine."""
import pytest


def test_ssh_common_exports_technique_executors():
    from app.clients._ssh_common import TECHNIQUE_EXECUTORS
    assert "T1592" in TECHNIQUE_EXECUTORS
    assert "T1003.001" in TECHNIQUE_EXECUTORS
    assert len(TECHNIQUE_EXECUTORS) >= 13


def test_ssh_common_exports_parse_credential():
    from app.clients._ssh_common import _parse_credential
    user, password, host, port = _parse_credential("root:toor@192.168.1.1:22")
    assert user == "root"
    assert password == "toor"
    assert host == "192.168.1.1"
    assert port == 22


def test_ssh_common_parse_credential_default_port():
    from app.clients._ssh_common import _parse_credential
    user, password, host, port = _parse_credential("admin:pass@10.0.0.1")
    assert port == 22
    assert host == "10.0.0.1"


def test_ssh_common_exports_parse_stdout_to_facts():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "Linux kali 5.10\nroot\n")
    assert len(facts) >= 1
    assert facts[0]["trait"] in ("host.os", "host.user")
    assert "value" in facts[0]
    assert facts[0]["source"] == "direct_ssh"


def test_ssh_common_parse_stdout_empty_returns_no_facts():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "")
    assert facts == []

def test_ssh_common_parse_stdout_custom_source():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "Linux kali 5.10\n", source="persistent_ssh")
    assert facts[0]["source"] == "persistent_ssh"


import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_persistent_engine_reuses_existing_session():
    """Second execute() reuses the pooled connection — asyncssh.connect called only once."""
    from app.clients.persistent_ssh_client import PersistentSSHChannelEngine, _SESSION_POOL
    _SESSION_POOL.clear()

    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.stdout = "Linux kali 5.10\nroot\n"
    mock_result.stderr = ""
    mock_result.exit_status = 0
    mock_conn.run = AsyncMock(return_value=mock_result)

    with patch("app.clients.persistent_ssh_client.asyncssh") as mock_asyncssh:
        mock_asyncssh.connect = AsyncMock(return_value=mock_conn)

        engine = PersistentSSHChannelEngine(operation_id="op-001")
        result1 = await engine.execute("T1592", "root:toor@192.168.1.1:22")
        result2 = await engine.execute("T1592", "root:toor@192.168.1.1:22")

    assert result1.success is True
    assert result2.success is True
    assert mock_asyncssh.connect.call_count == 1  # connection reused


@pytest.mark.asyncio
async def test_persistent_engine_returns_facts():
    """execute() parses stdout into facts with source='direct_ssh'."""
    from app.clients.persistent_ssh_client import PersistentSSHChannelEngine, _SESSION_POOL
    _SESSION_POOL.clear()

    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.stdout = "Linux kali 5.10 x86_64\nroot\n"
    mock_result.stderr = ""
    mock_result.exit_status = 0
    mock_conn.run = AsyncMock(return_value=mock_result)

    with patch("app.clients.persistent_ssh_client.asyncssh") as mock_asyncssh:
        mock_asyncssh.connect = AsyncMock(return_value=mock_conn)

        engine = PersistentSSHChannelEngine(operation_id="op-002")
        result = await engine.execute("T1592", "root:toor@10.0.0.1:22")

    assert result.success is True
    assert len(result.facts) > 0
    assert result.facts[0]["source"] == "direct_ssh"


@pytest.mark.asyncio
async def test_persistent_engine_unknown_technique_returns_failure():
    """Unknown MITRE ID returns success=False without making SSH call."""
    from app.clients.persistent_ssh_client import PersistentSSHChannelEngine, _SESSION_POOL
    _SESSION_POOL.clear()

    engine = PersistentSSHChannelEngine(operation_id="op-003")
    result = await engine.execute("T9999.999", "root:toor@10.0.0.1:22")

    assert result.success is False
    assert "No SSH executor" in result.error


@pytest.mark.asyncio
async def test_close_all_sessions_clears_pool():
    """close_all_sessions() removes only the given operation_id's sessions."""
    from app.clients.persistent_ssh_client import PersistentSSHChannelEngine, _SESSION_POOL

    mock_conn = MagicMock()
    mock_conn.close = MagicMock()

    _SESSION_POOL[("op-cleanup", "target-1")] = mock_conn
    _SESSION_POOL[("op-cleanup", "target-2")] = mock_conn
    _SESSION_POOL[("other-op", "target-x")] = mock_conn

    await PersistentSSHChannelEngine.close_all_sessions("op-cleanup")

    assert ("op-cleanup", "target-1") not in _SESSION_POOL
    assert ("op-cleanup", "target-2") not in _SESSION_POOL
    assert ("other-op", "target-x") in _SESSION_POOL  # untouched


@pytest.mark.asyncio
async def test_persistent_engine_is_available():
    """is_available() always returns True (no external dependencies)."""
    from app.clients.persistent_ssh_client import PersistentSSHChannelEngine
    engine = PersistentSSHChannelEngine(operation_id="op-avail")
    assert await engine.is_available() is True

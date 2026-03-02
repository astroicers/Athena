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

"""Execution engine client tests — SPEC-008 acceptance criteria."""

from unittest.mock import AsyncMock, patch

import pytest

from app.clients import ExecutionResult
from app.clients.mock_c2_client import MockC2Client
from app.clients.ai_engine_client import EngineNotAvailableError, AiEngineClient
from app.clients.c2_client import C2EngineClient


# ===================================================================
# MockC2Client (5 tests)
# ===================================================================


async def test_mock_c2_execute_known_technique():
    """MockC2Client.execute() with known T1003.001 → success with facts."""
    client = MockC2Client()
    with patch("app.clients.mock_c2_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.execute("T1003.001", "DC-01")
    assert result.success is True
    assert result.execution_id  # non-empty UUID
    assert len(result.facts) > 0
    assert any("credential" in f["trait"] for f in result.facts)


async def test_mock_c2_execute_unknown_technique():
    """MockC2Client.execute() with unknown technique → success with empty facts."""
    client = MockC2Client()
    with patch("app.clients.mock_c2_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.execute("T9999.999", "WS-01")
    assert result.success is True
    assert result.facts == []
    assert "T9999.999" in result.output


async def test_mock_c2_get_status():
    """get_status() → 'finished'."""
    client = MockC2Client()
    status = await client.get_status("any-id")
    assert status == "finished"


async def test_mock_c2_list_abilities():
    """list_abilities() → non-empty list with known technique IDs."""
    client = MockC2Client()
    abilities = await client.list_abilities()
    assert len(abilities) >= 4
    ids = {a["ability_id"] for a in abilities}
    assert "T1003.001" in ids
    assert "T1595.001" in ids


async def test_mock_c2_is_available():
    """is_available() → True (always available in mock mode)."""
    client = MockC2Client()
    assert await client.is_available() is True


# ===================================================================
# AiEngineClient (3 tests)
# ===================================================================


async def test_ai_engine_client_disabled_when_no_url():
    """AI_ENGINE_URL='' → enabled=False, is_available=False."""
    client = AiEngineClient("")
    assert client.enabled is False
    assert await client.is_available() is False


async def test_ai_engine_client_execute_when_disabled():
    """execute() when disabled → raises EngineNotAvailableError."""
    client = AiEngineClient("")
    with pytest.raises(EngineNotAvailableError):
        await client.execute("T1003.001", "DC-01")


async def test_ai_engine_client_get_status_when_disabled():
    """get_status() when disabled → 'unavailable'."""
    client = AiEngineClient("")
    status = await client.get_status("any-id")
    assert status == "unavailable"


# ===================================================================
# C2EngineClient (1 test — structural only, no real C2 engine)
# ===================================================================


async def test_c2_engine_client_check_version_callable():
    """C2EngineClient has check_version() method that is callable."""
    client = C2EngineClient(base_url="http://localhost:8888", api_key="test")
    assert callable(client.check_version)
    assert callable(client.sync_agents)
    # Cleanup
    await client.aclose()

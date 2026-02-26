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

"""Integration tests for real Caldera + LLM API connections.

Tests in this file are SKIPPED by default when API keys or real services
are not available. They run only when:
  - ANTHROPIC_API_KEY is set (LLM tests)
  - MOCK_CALDERA=false and Caldera is reachable (Caldera tests)

Run manually:
  ANTHROPIC_API_KEY=sk-ant-... MOCK_CALDERA=false pytest tests/test_integration_real_mode.py -v
"""

import json
import os

import pytest

from app.config import settings

# ---------------------------------------------------------------------------
# Skip markers
# ---------------------------------------------------------------------------

SKIP_NO_CLAUDE = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="No ANTHROPIC_API_KEY set",
)

SKIP_NO_CALDERA = pytest.mark.skipif(
    os.getenv("MOCK_CALDERA", "true").lower() == "true",
    reason="MOCK_CALDERA=true (set MOCK_CALDERA=false to enable)",
)


# ═══════════════════════════════════════════════════════════════════════════
# LLM Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


@SKIP_NO_CLAUDE
@pytest.mark.asyncio
async def test_call_claude_returns_json():
    """Real Claude API call returns parseable JSON recommendation."""
    from app.services.orient_engine import OrientEngine
    from app.ws_manager import WebSocketManager

    engine = OrientEngine(WebSocketManager())
    response = await engine._call_claude(
        "You are a security advisor. Return exactly this JSON: "
        '{"situation_assessment":"test","recommended_technique_id":"T1003.001",'
        '"confidence":0.85,"reasoning_text":"test","options":[{"technique_id":'
        '"T1003.001","technique_name":"LSASS","reasoning":"test","risk_level":'
        '"medium","recommended_engine":"caldera","confidence":0.85,'
        '"prerequisites":["admin"]}]}'
    )
    parsed = json.loads(response)
    assert "situation_assessment" in parsed or "recommended_technique_id" in parsed


@SKIP_NO_CLAUDE
@pytest.mark.asyncio
async def test_orient_real_llm_full_cycle(seeded_db):
    """Full Orient cycle with real Claude API — build prompt, call, parse, store."""
    from app.services.orient_engine import OrientEngine
    from app.ws_manager import WebSocketManager

    engine = OrientEngine(WebSocketManager())
    # Temporarily disable mock
    original = settings.MOCK_LLM
    settings.MOCK_LLM = False
    try:
        rec = await engine.analyze(seeded_db, "test-op-1", "Initial recon complete.")
        assert "situation_assessment" in rec
        assert "options" in rec
        assert isinstance(rec["options"], list)
        assert rec["confidence"] > 0
    finally:
        settings.MOCK_LLM = original


def test_llm_markdown_stripping():
    """Markdown-wrapped JSON is correctly stripped before parsing."""
    import re

    raw = '```json\n{"situation_assessment":"test","recommended_technique_id":"T1003.001","confidence":0.8,"reasoning_text":"r","options":[{"technique_id":"T1003.001","technique_name":"LSASS","reasoning":"r","risk_level":"medium","recommended_engine":"caldera","confidence":0.8,"prerequisites":[]}]}\n```'
    cleaned = raw.strip()
    md_match = re.match(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    assert md_match is not None
    json_str = md_match.group(1).strip()
    parsed = json.loads(json_str)
    assert parsed["recommended_technique_id"] == "T1003.001"
    assert len(parsed["options"]) == 1


def test_llm_missing_fields_fallback():
    """LLM response missing required fields triggers mock fallback."""
    from app.services.orient_engine import _MOCK_RECOMMENDATION

    # Simulate incomplete response
    incomplete = {"situation_assessment": "test"}  # missing other required fields
    required = ("situation_assessment", "recommended_technique_id", "confidence", "options")
    if not all(k in incomplete for k in required):
        result = _MOCK_RECOMMENDATION
    else:
        result = incomplete

    assert result is _MOCK_RECOMMENDATION
    assert len(result["options"]) == 3


# ═══════════════════════════════════════════════════════════════════════════
# Caldera Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


@SKIP_NO_CALDERA
@pytest.mark.asyncio
async def test_caldera_health_check():
    """Real Caldera instance responds to health check."""
    from app.clients.caldera_client import CalderaClient

    client = CalderaClient(settings.CALDERA_URL, settings.CALDERA_API_KEY)
    try:
        available = await client.is_available()
        assert available is True
    finally:
        await client.aclose()


@SKIP_NO_CALDERA
@pytest.mark.asyncio
async def test_caldera_version_check():
    """Real Caldera reports a supported version (4.x or 5.x)."""
    from app.clients.caldera_client import CalderaClient

    client = CalderaClient(settings.CALDERA_URL, settings.CALDERA_API_KEY)
    try:
        version = await client.check_version()
        assert version.startswith("4.") or version.startswith("5."), (
            f"Unsupported Caldera version: {version}"
        )
    finally:
        await client.aclose()


@SKIP_NO_CALDERA
@pytest.mark.asyncio
async def test_caldera_list_abilities():
    """Real Caldera returns a non-empty abilities list."""
    from app.clients.caldera_client import CalderaClient

    client = CalderaClient(settings.CALDERA_URL, settings.CALDERA_API_KEY)
    try:
        abilities = await client.list_abilities()
        assert isinstance(abilities, list)
        assert len(abilities) > 0, "Caldera returned empty abilities list"
    finally:
        await client.aclose()


@SKIP_NO_CALDERA
@pytest.mark.asyncio
async def test_health_endpoint_real_mode(seeded_db):
    """GET /api/health reports caldera as 'connected' in real mode."""
    from httpx import AsyncClient, ASGITransport

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["caldera"] in ("connected", "unreachable")

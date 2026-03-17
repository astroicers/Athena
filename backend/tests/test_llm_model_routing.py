# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Unit tests for SPEC-029: LLM multi-model static routing (Model Alloys).

Verifies that LLMClient.call() resolves the correct model based on
task_type, explicit model override, and fallback behaviour.
"""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings, TASK_MODEL_MAP
from app.services.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> LLMClient:
    """Create a fresh LLMClient instance (not the singleton)."""
    return LLMClient()


def _api_key_patch():
    """Patch settings.ANTHROPIC_API_KEY so the api_key backend path is entered."""
    return patch.object(settings, "ANTHROPIC_API_KEY", "test-key-for-routing")


# ---------------------------------------------------------------------------
# Test 1: orient_analysis routes to Opus
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_type_orient_routes_to_opus():
    """task_type='orient_analysis' should resolve to the Opus model."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type="orient_analysis")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]  # positional arg: model
        assert actual_model == settings.CLAUDE_MODEL_OPUS


# ---------------------------------------------------------------------------
# Test 2: fact_summary routes to Sonnet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_type_fact_summary_routes_to_sonnet():
    """task_type='fact_summary' should resolve to the Sonnet model."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type="fact_summary")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL_SONNET


# ---------------------------------------------------------------------------
# Test 3: node_summary routes to Haiku
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_type_node_summary_routes_to_haiku():
    """task_type='node_summary' should resolve to the Haiku model."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type="node_summary")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL_HAIKU


# ---------------------------------------------------------------------------
# Test 4: format_report routes to Haiku
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_type_format_report_routes_to_haiku():
    """task_type='format_report' should resolve to the Haiku model."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type="format_report")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL_HAIKU


# ---------------------------------------------------------------------------
# Test 5: classify_vulnerability routes to Haiku
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_type_classify_vuln_routes_to_haiku():
    """task_type='classify_vulnerability' should resolve to the Haiku model."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type="classify_vulnerability")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL_HAIKU


# ---------------------------------------------------------------------------
# Test 6: unknown task_type falls back to default + WARNING log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_task_type_falls_back_to_default(caplog):
    """Unknown task_type should fall back to settings.CLAUDE_MODEL and emit WARNING."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call, \
         caplog.at_level(logging.WARNING, logger="app.services.llm_client"):
        await client.call("sys", "usr", task_type="nonexistent_task")
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL
        assert "Unknown task_type" in caplog.text
        assert "nonexistent_task" in caplog.text


# ---------------------------------------------------------------------------
# Test 7: task_type=None falls back to default
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_none_task_type_falls_back_to_default():
    """task_type=None should use settings.CLAUDE_MODEL (default behaviour)."""
    client = _make_client()

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call("sys", "usr", task_type=None)
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == settings.CLAUDE_MODEL


# ---------------------------------------------------------------------------
# Test 8: explicit model overrides task_type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explicit_model_overrides_task_type():
    """When model= is explicitly provided, it should override task_type routing."""
    client = _make_client()
    override_model = "custom-model-override"

    with _api_key_patch(), \
         patch.object(client, "_resolve_backend", return_value="api_key"), \
         patch.object(client, "_call_claude", new_callable=AsyncMock, return_value="ok") as mock_call:
        await client.call(
            "sys", "usr",
            model=override_model,
            task_type="orient_analysis",
        )
        mock_call.assert_awaited_once()
        actual_model = mock_call.call_args[0][2]
        assert actual_model == override_model


# ---------------------------------------------------------------------------
# Test 9: TASK_MODEL_MAP references settings values
# ---------------------------------------------------------------------------

def test_task_model_map_uses_settings_values():
    """TASK_MODEL_MAP entries should reference settings.CLAUDE_MODEL_* values."""
    assert TASK_MODEL_MAP["orient_analysis"] == settings.CLAUDE_MODEL_OPUS
    assert TASK_MODEL_MAP["fact_summary"] == settings.CLAUDE_MODEL_SONNET
    assert TASK_MODEL_MAP["node_summary"] == settings.CLAUDE_MODEL_HAIKU
    assert TASK_MODEL_MAP["format_report"] == settings.CLAUDE_MODEL_HAIKU
    assert TASK_MODEL_MAP["classify_vulnerability"] == settings.CLAUDE_MODEL_HAIKU

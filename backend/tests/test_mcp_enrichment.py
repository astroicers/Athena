# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for MCP post-Act fact enrichment pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_enrichment_skips_when_mcp_disabled():
    from app.services.ooda_controller import OODAController

    controller = OODAController(
        fact_collector=MagicMock(),
        orient_engine=MagicMock(),
        decision_engine=MagicMock(),
        engine_router=MagicMock(),
        c5isr_mapper=MagicMock(),
        ws_manager=MagicMock(),
    )
    with patch("app.services.ooda_controller.settings") as s:
        s.MCP_ENABLED = False
        # Should return without error
        await controller._run_mcp_enrichment(
            MagicMock(), "op-1", {"status": "success", "engine": "mcp"}
        )


@pytest.mark.asyncio
async def test_enrichment_skips_non_mcp_engine():
    from app.services.ooda_controller import OODAController

    controller = OODAController(
        fact_collector=MagicMock(),
        orient_engine=MagicMock(),
        decision_engine=MagicMock(),
        engine_router=MagicMock(),
        c5isr_mapper=MagicMock(),
        ws_manager=MagicMock(),
    )
    with patch("app.services.ooda_controller.settings") as s:
        s.MCP_ENABLED = True
        await controller._run_mcp_enrichment(
            MagicMock(), "op-1", {"status": "success", "engine": "ssh"}
        )


@pytest.mark.asyncio
async def test_enrichment_skips_non_success():
    from app.services.ooda_controller import OODAController

    controller = OODAController(
        fact_collector=MagicMock(),
        orient_engine=MagicMock(),
        decision_engine=MagicMock(),
        engine_router=MagicMock(),
        c5isr_mapper=MagicMock(),
        ws_manager=MagicMock(),
    )
    with patch("app.services.ooda_controller.settings") as s:
        s.MCP_ENABLED = True
        await controller._run_mcp_enrichment(
            MagicMock(), "op-1", {"status": "failed", "engine": "mcp"}
        )

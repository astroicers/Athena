# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Reports router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def test_get_operation_report(client: AsyncClient):
    """GET /api/operations/test-op-1/report -> 200, JSON with operation data."""
    resp = await client.get("/api/operations/test-op-1/report")
    assert resp.status_code == 200
    body = resp.json()
    assert "operation" in body
    assert body["operation"]["id"] == "test-op-1"
    assert "ooda_timeline" in body
    assert "executions" in body
    assert "facts" in body
    assert "recommendations" in body
    assert "c5isr" in body
    assert "logs" in body
    assert "mission_steps" in body
    assert "targets" in body
    assert "agents" in body


async def test_get_operation_report_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/report -> 404."""
    resp = await client.get("/api/operations/nonexistent-op/report")
    assert resp.status_code == 404


async def test_get_structured_report(client: AsyncClient):
    """GET /api/operations/test-op-1/report/structured -> 200 with PentestReport.

    ReportGenerator.generate uses asyncio.gather over a single asyncpg connection
    which raises InterfaceError in test mode.  We mock it to return a minimal
    PentestReport so the router/serialisation path is exercised without hitting
    the concurrent-query limitation.
    """
    from app.models.report import PentestReport

    mock_report = PentestReport(
        operation_id="test-op-1",
        operation_name="Test Operation",
        codename="PHANTOM-TEST",
        generated_at="2025-01-01T00:00:00+00:00",
        client_name=None,
        contact_email=None,
        in_scope=[],
        out_of_scope=[],
        engagement_status=None,
        executive_summary="Mock summary.",
        targets_discovered=1,
        subdomains_found=0,
        services_scanned=0,
        vulnerabilities_found=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        findings=[],
        attack_steps=[],
        orient_recommendations=[],
        mitre_coverage={},
    )

    with patch(
        "app.services.report_generator.ReportGenerator",
    ) as MockGen:
        instance = MagicMock()
        MockGen.return_value = instance
        instance.generate = AsyncMock(return_value=mock_report)

        resp = await client.get("/api/operations/test-op-1/report/structured")

    assert resp.status_code == 200
    body = resp.json()
    assert body["operation_id"] == "test-op-1"
    assert "executive_summary" in body
    assert "findings" in body
    assert "attack_steps" in body
    assert "mitre_coverage" in body


async def test_get_markdown_report(client: AsyncClient):
    """GET /api/operations/test-op-1/report/markdown -> 200, text/markdown content.

    Same concurrent-query constraint as structured report — mock ReportGenerator.
    """
    from app.models.report import PentestReport
    from app.services.report_generator import ReportGenerator as _RG

    mock_report = PentestReport(
        operation_id="test-op-1",
        operation_name="Test Operation",
        codename="PHANTOM-TEST",
        generated_at="2025-01-01T00:00:00+00:00",
        client_name=None,
        contact_email=None,
        in_scope=[],
        out_of_scope=[],
        engagement_status=None,
        executive_summary="Mock executive summary.",
        targets_discovered=1,
        subdomains_found=0,
        services_scanned=0,
        vulnerabilities_found=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        findings=[],
        attack_steps=[],
        orient_recommendations=[],
        mitre_coverage={},
    )
    # Use a real ReportGenerator instance to produce the markdown so the
    # to_markdown() path is also exercised.
    real_gen = _RG()
    expected_md = real_gen.to_markdown(mock_report)

    with patch(
        "app.services.report_generator.ReportGenerator",
    ) as MockGen:
        instance = MagicMock()
        MockGen.return_value = instance
        instance.generate = AsyncMock(return_value=mock_report)
        instance.to_markdown = MagicMock(return_value=expected_md)

        resp = await client.get("/api/operations/test-op-1/report/markdown")

    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text" in content_type or "markdown" in content_type
    text = resp.text
    assert len(text) > 0
    assert "# Penetration Test Report" in text


async def test_get_markdown_report_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/report/markdown -> 404."""
    resp = await client.get("/api/operations/nonexistent-op/report/markdown")
    assert resp.status_code == 404

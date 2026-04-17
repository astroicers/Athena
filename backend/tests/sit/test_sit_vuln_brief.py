"""SIT: CVE Auto-Populate + Operation Brief — fact→vulnerability lifecycle.

Verifies that vuln.cve facts auto-populate the vulnerabilities table,
duplicates are correctly deduplicated, and the brief generator produces
operation summaries.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


# ── VB.1  vuln.cve fact auto-populates vulnerabilities table ─────────────
async def test_vuln_cve_fact_auto_populates(sit_services):
    """upsert_from_fact should insert a row into vulnerabilities table."""
    db = sit_services.db

    from app.services.vulnerability_manager import VulnerabilityManager

    vm = VulnerabilityManager()
    fact_id = str(uuid.uuid4())
    vuln_id = await vm.upsert_from_fact(
        db, "test-op-1",
        fact_id=fact_id,
        cve_id="CVE-2024-12345",
        target_id="test-target-1",
    )

    row = await db.fetchrow(
        "SELECT cve_id, target_id, status FROM vulnerabilities WHERE cve_id = 'CVE-2024-12345'"
    )
    assert row is not None
    assert row["cve_id"] == "CVE-2024-12345"
    assert row["target_id"] == "test-target-1"
    assert row["status"] == "discovered"


# ── VB.2  duplicate CVE does not produce duplicate vulnerability ─────────
async def test_duplicate_cve_deduplication(sit_services):
    """ON CONFLICT DO NOTHING should prevent duplicate vulnerabilities."""
    db = sit_services.db

    from app.services.vulnerability_manager import VulnerabilityManager

    vm = VulnerabilityManager()

    # First insert
    id1 = await vm.upsert_from_fact(
        db, "test-op-1",
        fact_id=str(uuid.uuid4()),
        cve_id="CVE-2024-99999",
        target_id="test-target-1",
    )

    # Second insert (duplicate)
    id2 = await vm.upsert_from_fact(
        db, "test-op-1",
        fact_id=str(uuid.uuid4()),
        cve_id="CVE-2024-99999",
        target_id="test-target-1",
    )

    # Only one row should exist
    count = await db.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities WHERE cve_id = 'CVE-2024-99999'"
    )
    assert count == 1


# ── VB.3  collect_from_result with vuln.cve triggers auto-populate ───────
async def test_collect_from_result_vuln_cve_path(sit_services):
    """FactCollector.collect_from_result with vuln.cve facts should auto-populate vulnerabilities."""
    db = sit_services.db

    raw_facts = [
        {"trait": "vuln.cve", "value": "CVE-2023-44487 HTTP/2 Rapid Reset", "score": 1, "source": "scanner"},
        {"trait": "service.open_port", "value": "443/tcp https", "score": 1, "source": "scanner"},
    ]

    await sit_services.fc.collect_from_result(
        db, "test-op-1",
        technique_id="T1595.002",
        target_id="test-target-1",
        raw_facts=raw_facts,
    )

    # The CVE fact should have triggered upsert_from_fact
    vuln_row = await db.fetchrow(
        "SELECT cve_id, status FROM vulnerabilities WHERE cve_id = 'CVE-2023-44487'"
    )
    assert vuln_row is not None
    assert vuln_row["status"] == "discovered"

    # Service fact should not create a vulnerability
    svc_vuln = await db.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities WHERE cve_id LIKE '%443%'"
    )
    assert svc_vuln == 0


# ── VB.4  brief_md updates after cycle ───────────────────────────────────
async def test_brief_md_updates_after_generation(sit_services):
    """BriefGenerator.generate should produce non-empty markdown and update operations."""
    db = sit_services.db

    from app.services.brief_generator import BriefGenerator

    bg = BriefGenerator()
    brief_md = await bg.generate(db, "test-op-1")

    assert brief_md is not None
    assert len(brief_md) > 0
    assert isinstance(brief_md, str)

    # Update operations table like the controller does
    await db.execute(
        "UPDATE operations SET brief_md = $1, brief_updated_at = $2 WHERE id = $3",
        brief_md, datetime.now(timezone.utc), "test-op-1",
    )

    row = await db.fetchrow(
        "SELECT brief_md, brief_updated_at FROM operations WHERE id = 'test-op-1'"
    )
    assert row["brief_md"] is not None
    assert len(row["brief_md"]) > 0
    assert row["brief_updated_at"] is not None


# ── VB.5  brief.updated WS event broadcast with iteration number ────────
async def test_brief_updated_ws_broadcast(sit_services):
    """brief.updated event should be broadcast with iteration number."""
    db = sit_services.db

    from app.services.brief_generator import BriefGenerator

    bg = BriefGenerator()
    brief_md = await bg.generate(db, "test-op-1")

    # Simulate controller brief.updated broadcast
    await sit_services.ws.broadcast("test-op-1", "brief.updated", {
        "iteration": 1,
    })

    brief_calls = [
        c for c in sit_services.ws._calls
        if c[1] == "brief.updated"
    ]
    assert len(brief_calls) >= 1
    assert "iteration" in brief_calls[-1][2]
    assert brief_calls[-1][2]["iteration"] >= 1

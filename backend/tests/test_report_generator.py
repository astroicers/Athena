# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Unit tests for ReportGenerator — A.5 acceptance criteria."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.report_generator import ReportGenerator, _cvss_to_severity
from app.models.report import PentestReport, Finding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db(op_row=None, eng_row=None, targets=None, facts=None, ooda_rows=None, rec_rows=None, mitre_rows=None, recon_rows=None):
    """Build a mock DB that returns predetermined rows for asyncpg direct methods.

    The generate() method now uses db.fetchrow() and db.fetch() directly via
    asyncio.gather. We use side_effect functions that inspect SQL to route results.
    """
    db = AsyncMock()

    # Default empty data
    if targets is None:
        targets = []
    if facts is None:
        facts = []
    if ooda_rows is None:
        ooda_rows = []
    if rec_rows is None:
        rec_rows = []
    if mitre_rows is None:
        mitre_rows = []
    if recon_rows is None:
        recon_rows = []

    def make_row(d):
        """Create a dict-like mock that supports dict(row) and row['key']."""
        row = MagicMock()
        row.__getitem__ = lambda self, k: d[k]
        row.keys = lambda: d.keys()
        for k, v in d.items():
            setattr(row, k, v)
        return row

    # Route fetchrow calls by SQL content
    async def mock_fetchrow(sql, *args):
        sql_lower = sql.lower()
        if "operations" in sql_lower:
            return make_row(op_row) if op_row else None
        if "engagements" in sql_lower:
            return make_row(eng_row) if eng_row else None
        if "osint.subdomain" in sql_lower or "trait = " in sql_lower:
            return make_row({"cnt": 0})
        if "category = " in sql_lower and "service" in sql_lower:
            return make_row({"cnt": 0})
        if "recon_scans" in sql_lower:
            return make_row({"cnt": len(recon_rows)})
        return make_row({"cnt": 0})

    # Route fetch calls by SQL content
    async def mock_fetch(sql, *args):
        sql_lower = sql.lower()
        if "targets" in sql_lower:
            return [make_row(t) for t in targets]
        if "vuln.cve" in sql_lower or "trait = " in sql_lower:
            return [make_row(f) for f in facts]
        if "ooda_iterations" in sql_lower:
            return [make_row(r) for r in ooda_rows]
        if "recommendations" in sql_lower:
            return [make_row(r) for r in rec_rows]
        if "technique_executions" in sql_lower:
            return [make_row(r) for r in mitre_rows]
        return []

    db.fetchrow = AsyncMock(side_effect=mock_fetchrow)
    db.fetch = AsyncMock(side_effect=mock_fetch)
    db.fetchval = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value="INSERT 0 1")
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_returns_pentest_report():
    """generate() assembles and returns a PentestReport instance."""
    op_row = {
        "id": "op-001",
        "name": "Test Operation",
        "codename": "ALPHA",
        "strategic_intent": "test",
        "status": "active",
    }
    db = make_mock_db(op_row=op_row)
    generator = ReportGenerator()
    report = await generator.generate(db, "op-001")

    assert isinstance(report, PentestReport)
    assert report.operation_id == "op-001"
    assert report.operation_name == "Test Operation"
    assert report.codename == "ALPHA"
    assert isinstance(report.findings, list)
    assert isinstance(report.attack_steps, list)
    assert isinstance(report.mitre_coverage, dict)


@pytest.mark.asyncio
async def test_generate_sorts_findings_by_cvss():
    """Findings should be sorted by CVSS score descending."""
    op_row = {
        "id": "op-002",
        "name": "Sort Test",
        "codename": "BRAVO",
        "strategic_intent": "test",
        "status": "active",
    }
    # Two vuln facts with different CVSS scores
    facts = [
        {"value": "CVE-2021-1111:http:Apache_2.4.6:cvss=5.0:exploit=false", "source_target_id": "tgt-001"},
        {"value": "CVE-2016-0777:ssh:OpenSSH_7.4:cvss=9.8:exploit=true", "source_target_id": "tgt-001"},
        {"value": "CVE-2020-2222:ftp:vsftpd_2.3.4:cvss=7.5:exploit=false", "source_target_id": "tgt-001"},
    ]
    targets = [{"id": "tgt-001", "ip_address": "192.168.1.1", "hostname": "host1", "role": "server"}]
    db = make_mock_db(op_row=op_row, targets=targets, facts=facts)
    generator = ReportGenerator()
    report = await generator.generate(db, "op-002")

    assert len(report.findings) == 3
    # First finding should have highest CVSS
    assert report.findings[0].cvss_score == 9.8
    assert report.findings[1].cvss_score == 7.5
    assert report.findings[2].cvss_score == 5.0


@pytest.mark.asyncio
async def test_generate_no_engagement_has_none_client():
    """When no engagement row exists, client_name and contact_email should be None."""
    op_row = {
        "id": "op-003",
        "name": "No Engagement Op",
        "codename": "CHARLIE",
        "strategic_intent": "test",
        "status": "active",
    }
    # eng_row=None means no engagement found
    db = make_mock_db(op_row=op_row, eng_row=None)
    generator = ReportGenerator()
    report = await generator.generate(db, "op-003")

    assert report.client_name is None
    assert report.contact_email is None
    assert report.engagement_status is None
    assert report.in_scope == []
    assert report.out_of_scope == []


def test_parse_vuln_fact_correct_format():
    """_parse_vuln_facts correctly parses a well-formed fact value."""
    generator = ReportGenerator()

    # Simulate a row with known vuln.cve format
    row = MagicMock()
    row.__getitem__ = lambda self, k: {
        "value": "CVE-2016-0777:ssh:OpenSSH_7.4:cvss=9.8:exploit=true",
        "source_target_id": "tgt-001",
    }[k]

    targets_by_id = {
        "tgt-001": {"ip_address": "10.0.0.1", "hostname": "victim", "role": "server"}
    }

    findings = generator._parse_vuln_facts([row], targets_by_id)

    assert len(findings) == 1
    f = findings[0]
    assert f.cve_id == "CVE-2016-0777"
    assert f.service == "ssh"
    assert f.version == "OpenSSH_7.4"
    assert f.cvss_score == 9.8
    assert f.exploit_available is True
    assert f.severity == "critical"
    assert f.target_ip == "10.0.0.1"
    assert f.target_id == "tgt-001"


def test_to_markdown_contains_findings():
    """to_markdown() renders CVE IDs and severity labels."""
    report = PentestReport(
        operation_id="op-test",
        operation_name="Markdown Test Op",
        codename="DELTA",
        generated_at="2026-03-01T00:00:00+00:00",
        client_name="Acme Corp",
        contact_email="sec@acme.com",
        in_scope=["192.168.1.0/24"],
        out_of_scope=[],
        engagement_status="active",
        executive_summary="Test summary.",
        targets_discovered=2,
        subdomains_found=5,
        services_scanned=10,
        vulnerabilities_found=2,
        critical_count=1,
        high_count=1,
        medium_count=0,
        low_count=0,
        findings=[
            Finding(
                cve_id="CVE-2016-0777",
                service="ssh",
                version="OpenSSH_7.4",
                cvss_score=9.8,
                severity="critical",
                description="",
                exploit_available=True,
                target_id="tgt-001",
                target_ip="10.0.0.1",
            ),
            Finding(
                cve_id="CVE-2020-1234",
                service="http",
                version="Apache_2.4.6",
                cvss_score=7.5,
                severity="high",
                description="",
                exploit_available=False,
                target_id="tgt-001",
                target_ip="10.0.0.1",
            ),
        ],
        attack_steps=[],
        orient_recommendations=[],
        mitre_coverage={},
    )

    generator = ReportGenerator()
    md = generator.to_markdown(report)

    assert "CVE-2016-0777" in md
    assert "CRITICAL" in md
    assert "CVE-2020-1234" in md
    assert "HIGH" in md
    assert "Acme Corp" in md
    assert "# Penetration Test Report" in md
    assert "## Findings" in md


def test_cvss_to_severity():
    """_cvss_to_severity maps CVSS score ranges to correct severity labels."""
    assert _cvss_to_severity(9.8) == "critical"
    assert _cvss_to_severity(9.0) == "critical"
    assert _cvss_to_severity(8.9) == "high"
    assert _cvss_to_severity(7.0) == "high"
    assert _cvss_to_severity(6.9) == "medium"
    assert _cvss_to_severity(4.0) == "medium"
    assert _cvss_to_severity(3.9) == "low"
    assert _cvss_to_severity(0.1) == "low"
    assert _cvss_to_severity(0.0) == "info"

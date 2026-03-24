# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Tests for OODA timeline detail and target fields.

Verifies that GET /operations/{op_id}/ooda/timeline returns:
- target_id / target_hostname / target_ip when a technique_execution exists
- detail dict per phase (observe, orient, decide, act)
- Graceful None when data is unavailable
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: insert an OODA iteration with linked data
# ---------------------------------------------------------------------------

async def _seed_iteration(
    db,
    *,
    operation_id: str = "test-op-1",
    target_id: str = "test-target-1",
    iteration_number: int = 1,
    observe: str | None = "Observed host scanning activity",
    orient: str | None = "Oriented on credential access opportunity",
    decide: str | None = "Decided to run LSASS dump",
    act: str | None = "Executed T1003.001 via SSH",
    with_recommendation: bool = False,
    with_execution: bool = False,
    with_facts: bool = False,
) -> dict:
    """Insert a full OODA iteration and optional related rows. Returns IDs."""
    iter_id = str(uuid4())
    rec_id = str(uuid4()) if with_recommendation else None
    exec_id = str(uuid4()) if with_execution else None

    # Insert recommendation first if needed (for orient detail)
    if with_recommendation:
        await db.execute(
            "INSERT INTO recommendations "
            "(id, operation_id, ooda_iteration_id, situation_assessment, "
            "recommended_technique_id, confidence, options, reasoning_text, accepted) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            rec_id, operation_id, iter_id,
            "Host DC-01 shows credential access opportunity",
            "T1003.001", 0.85,
            json.dumps([{"technique": "T1003.001", "confidence": 0.85}]),
            "LSASS memory dump is most likely to succeed",
            True,
        )

    # Insert technique execution if needed (for act detail + target resolution)
    if with_execution:
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, result_summary, error_message, facts_collected_count, "
            "started_at, completed_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())",
            exec_id, "T1003.001", target_id, operation_id, iter_id,
            "mcp_ssh", "success", "Dumped 3 credentials", None, 3,
        )

    # Insert facts if needed (for observe detail)
    if with_facts:
        for i in range(3):
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, operation_id) "
                "VALUES ($1, $2, $3, $4, $5)",
                str(uuid4()), f"host.port.{i}", f"{80 + i}", "host", operation_id,
            )

    # Insert the OODA iteration
    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, "
        "observe_summary, orient_summary, decide_summary, act_summary, "
        "recommendation_id, technique_execution_id, started_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())",
        iter_id, operation_id, iteration_number, "act",
        observe, orient, decide, act,
        rec_id, exec_id,
    )

    return {
        "iter_id": iter_id,
        "rec_id": rec_id,
        "exec_id": exec_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_timeline_includes_detail_field(client, seeded_db):
    """Timeline entries have a detail field (dict or None)."""
    await _seed_iteration(seeded_db, observe="Scan complete", orient=None, decide=None, act=None)
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    ooda_entries = [e for e in data if e["phase"] != "recon"]
    assert len(ooda_entries) >= 1
    for entry in ooda_entries:
        assert "detail" in entry


async def test_timeline_target_fields_present_with_execution(client, seeded_db):
    """When a technique_execution links to a target, target_id/hostname/ip are populated."""
    await _seed_iteration(
        seeded_db,
        with_execution=True,
        observe="Scan done",
        orient=None,
        decide=None,
        act="Ran technique",
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    ooda_entries = [e for e in data if e["phase"] != "recon"]
    assert len(ooda_entries) >= 1
    # At least one entry should have target info
    has_target = any(e["target_id"] is not None for e in ooda_entries)
    assert has_target, "Expected at least one entry with target_id set"
    targeted = [e for e in ooda_entries if e["target_id"] is not None]
    for entry in targeted:
        assert entry["target_hostname"] is not None
        assert entry["target_ip"] is not None


async def test_timeline_target_fields_none_without_execution(client, seeded_db):
    """When no technique_execution exists, target fields are None."""
    await _seed_iteration(
        seeded_db,
        with_execution=False,
        observe="Initial scan",
        orient=None,
        decide=None,
        act=None,
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    ooda_entries = [e for e in data if e["phase"] != "recon"]
    # The entry without execution should have None targets
    no_exec_entries = [e for e in ooda_entries if e["target_id"] is None]
    assert len(no_exec_entries) >= 1
    for entry in no_exec_entries:
        assert entry["target_hostname"] is None
        assert entry["target_ip"] is None


async def test_observe_detail_has_facts(client, seeded_db):
    """OBSERVE phase detail includes facts array and facts_count."""
    await _seed_iteration(
        seeded_db,
        with_facts=True,
        observe="Observed 3 ports",
        orient=None,
        decide=None,
        act=None,
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    observe_entries = [e for e in data if e["phase"] == "observe"]
    assert len(observe_entries) >= 1
    detail = observe_entries[-1]["detail"]
    assert detail is not None
    assert "facts_count" in detail
    assert "facts" in detail
    assert isinstance(detail["facts"], list)
    assert detail["facts_count"] >= 3
    assert "raw_summary" in detail


async def test_orient_detail_has_recommendation(client, seeded_db):
    """ORIENT phase detail includes recommendation data when available."""
    await _seed_iteration(
        seeded_db,
        with_recommendation=True,
        observe="Scan done",
        orient="Credential access recommended",
        decide=None,
        act=None,
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    orient_entries = [e for e in data if e["phase"] == "orient"]
    assert len(orient_entries) >= 1
    detail = orient_entries[-1]["detail"]
    assert detail is not None
    assert detail["situation_assessment"] == "Host DC-01 shows credential access opportunity"
    assert detail["recommended_technique_id"] == "T1003.001"
    assert detail["confidence"] == pytest.approx(0.85, abs=0.01)
    assert detail["reasoning_text"] == "LSASS memory dump is most likely to succeed"
    assert isinstance(detail["options"], list)


async def test_decide_detail_has_reason(client, seeded_db):
    """DECIDE phase detail includes reason field."""
    await _seed_iteration(
        seeded_db,
        observe="Scan done",
        orient=None,
        decide="Proceed with LSASS dump",
        act=None,
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    decide_entries = [e for e in data if e["phase"] == "decide"]
    assert len(decide_entries) >= 1
    detail = decide_entries[-1]["detail"]
    assert detail is not None
    assert detail["reason"] == "Proceed with LSASS dump"


async def test_act_detail_has_execution_info(client, seeded_db):
    """ACT phase detail includes technique execution data."""
    await _seed_iteration(
        seeded_db,
        with_execution=True,
        observe="Scan done",
        orient=None,
        decide=None,
        act="Executed T1003.001",
    )
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    act_entries = [e for e in data if e["phase"] == "act"]
    assert len(act_entries) >= 1
    detail = act_entries[-1]["detail"]
    assert detail is not None
    assert detail["technique_id"] == "T1003.001"
    assert detail["engine"] == "mcp_ssh"
    assert detail["status"] == "success"
    assert detail["result_summary"] == "Dumped 3 credentials"
    assert detail["facts_collected_count"] == 3


async def test_empty_timeline_returns_empty_list(client, seeded_db):
    """Timeline with no iterations returns an empty list (or only recon entries)."""
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    ooda_entries = [e for e in data if e["phase"] != "recon"]
    assert ooda_entries == []


async def test_timeline_backward_compatible(client, seeded_db):
    """All original fields (iteration_number, phase, summary, timestamp) still present."""
    await _seed_iteration(seeded_db, observe="Backward compat test")
    resp = await client.get("/api/operations/test-op-1/ooda/timeline")
    assert resp.status_code == 200
    data = resp.json()
    ooda_entries = [e for e in data if e["phase"] != "recon"]
    assert len(ooda_entries) >= 1
    entry = ooda_entries[0]
    assert "iteration_number" in entry
    assert "phase" in entry
    assert "summary" in entry
    assert "timestamp" in entry

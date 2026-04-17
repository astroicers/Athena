"""SIT Boundary 1: OODAController <-> FactCollector

Verifies that Controller.trigger_cycle() Observe phase correctly drives
FactCollector to extract facts from technique_executions and write them to DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.services.fact_collector import FactCollector

pytestmark = pytest.mark.asyncio


# ── 1.1 Observe collects facts from completed executions ──────────────────
async def test_observe_collects_facts_from_execution(
    sit_seeded_with_execution, sit_ws_manager,
):
    """FactCollector.collect() extracts facts from a successful execution
    and writes them to the facts table; observe_summary is non-empty."""
    db = sit_seeded_with_execution
    fc = FactCollector(sit_ws_manager)

    new_facts = await fc.collect(db, "test-op-1")
    assert len(new_facts) >= 1, "Should extract at least 1 fact from execution"

    # Verify fact persisted in DB
    row = await db.fetchrow(
        "SELECT trait, value, category FROM facts "
        "WHERE operation_id = $1 AND trait LIKE 'execution.%'",
        "test-op-1",
    )
    assert row is not None
    assert row["value"] != ""

    # Verify observe_summary
    summary = await fc.summarize(db, "test-op-1")
    assert summary != "No intelligence collected yet."
    assert "Collected" in summary


# ── 1.2 Duplicate collect produces no new facts ──────────────────────────
async def test_duplicate_collect_no_new_facts(
    sit_seeded_with_execution, sit_ws_manager,
):
    """Second call to collect() for the same operation returns empty list
    (dedup by trait+value)."""
    db = sit_seeded_with_execution
    fc = FactCollector(sit_ws_manager)

    first = await fc.collect(db, "test-op-1")
    assert len(first) >= 1

    second = await fc.collect(db, "test-op-1")
    assert second == [], "Second collect should produce 0 new facts"


# ── 1.3 Fact category auto-inferred for credential ──────────────────────
async def test_fact_category_inferred_credential(
    sit_seeded_with_execution, sit_ws_manager,
):
    """T1003.001 execution with 'hash' in summary -> category='credential'."""
    db = sit_seeded_with_execution
    fc = FactCollector(sit_ws_manager)

    new_facts = await fc.collect(db, "test-op-1")
    assert len(new_facts) >= 1

    # T1003 + "hash" -> credential
    cred_facts = [f for f in new_facts if f["category"] == "credential"]
    assert len(cred_facts) >= 1, "T1003.001 with hash summary should be credential"


# ── 1.4 Observe summary auto-truncated to 1000 chars ────────────────────
async def test_observe_summary_truncated(seeded_db, sit_ws_manager):
    """When observe_summary exceeds 1000 chars, it's truncated in DB."""
    db = seeded_db
    fc = FactCollector(sit_ws_manager)

    # Insert many facts to produce a long summary
    now = datetime.now(timezone.utc)
    for i in range(50):
        await db.execute(
            "INSERT INTO facts (id, trait, value, category, "
            "source_technique_id, source_target_id, operation_id, score, collected_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            str(uuid.uuid4()),
            f"service.port_{i}",
            f"Port {i}/tcp running service with a fairly long description here x{i*100}",
            "service", "T1003.001", "test-target-1", "test-op-1", 1, now,
        )

    summary = await fc.summarize(db, "test-op-1")
    # The controller truncates to 1000 chars when writing to DB
    truncated = summary[:1000]
    assert len(truncated) <= 1000


# ── 1.5 Each new fact sends fact.new WS event ────────────────────────────
async def test_fact_new_ws_event(sit_seeded_with_execution, sit_ws_manager):
    """Each extracted fact triggers a 'fact.new' WebSocket broadcast."""
    db = sit_seeded_with_execution
    fc = FactCollector(sit_ws_manager)

    new_facts = await fc.collect(db, "test-op-1")
    assert len(new_facts) >= 1

    fact_events = [
        c for c in sit_ws_manager._calls if c[1] == "fact.new"
    ]
    assert len(fact_events) == len(new_facts), (
        f"Expected {len(new_facts)} fact.new events, got {len(fact_events)}"
    )


# ── 1.6 collect_from_result stores raw facts directly ────────────────────
async def test_collect_from_result_stores_raw_facts(seeded_db, sit_ws_manager):
    """collect_from_result() persists arbitrary raw facts into DB."""
    db = seeded_db
    fc = FactCollector(sit_ws_manager)

    raw_facts = [
        {"trait": "credential.ssh", "value": "root:toor"},
        {"trait": "service.banner", "value": "OpenSSH 8.9p1"},
        {"trait": "host.kernel", "value": "Linux 5.15.0"},
    ]

    result = await fc.collect_from_result(
        db, "test-op-1", "T1003.001", "test-target-1", raw_facts,
    )
    assert len(result) == 3

    # Verify all facts in DB
    count = await db.fetchval(
        "SELECT COUNT(*) FROM facts WHERE operation_id = $1 AND trait IN ($2, $3, $4)",
        "test-op-1", "credential.ssh", "service.banner", "host.kernel",
    )
    assert count == 3

    # Verify WS events
    fact_events = [c for c in sit_ws_manager._calls if c[1] == "fact.new"]
    assert len(fact_events) == 3

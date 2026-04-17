"""SIT Boundary 5: EngineRouter <-> FactCollector

Verifies that execution results feed back through FactCollector to persist
extracted facts in the DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import BaseEngineClient, ExecutionResult
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector

pytestmark = pytest.mark.asyncio


async def _setup_for_execution(db):
    """Prepare DB state for execution."""
    ooda_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, started_at) "
        "VALUES ($1, $2, 1, 'act', $3)",
        ooda_id, "test-op-1", now,
    )
    # Add credential for mcp_ssh path
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, "
        "source_technique_id, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT DO NOTHING",
        str(uuid.uuid4()), "credential.ssh", "root:toor", "credential",
        "T1003.001", "test-target-1", "test-op-1", 1, now,
    )
    return ooda_id


# ── 5.1 Execution result facts stored in DB ─────────────────────────────
async def test_execution_result_facts_stored(seeded_db, sit_ws_manager):
    """Facts from ExecutionResult.facts are persisted via FactCollector."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)

    # Engine returns facts in the execution result
    client = MagicMock(spec=BaseEngineClient)
    client.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="exec-001",
        output="NTLM hash: aad3b435b51404ee",
        facts=[
            {"trait": "credential.ntlm", "value": "Administrator:aad3b435b51404ee"},
            {"trait": "host.privilege", "value": "SeDebugPrivilege enabled"},
        ],
    ))
    client.is_available = AsyncMock(return_value=True)

    fc = FactCollector(sit_ws_manager)
    router = EngineRouter(
        c2_engine=client, fact_collector=fc,
        ws_manager=sit_ws_manager, mcp_engine=client,
    )

    result = await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )
    assert result["status"] == "success"

    # Verify facts in DB
    rows = await db.fetch(
        "SELECT trait, value FROM facts "
        "WHERE operation_id = $1 AND trait IN ($2, $3)",
        "test-op-1", "credential.ntlm", "host.privilege",
    )
    traits = {r["trait"] for r in rows}
    assert "credential.ntlm" in traits, "credential.ntlm fact should be in DB"
    assert "host.privilege" in traits, "host.privilege fact should be in DB"


# ── 5.2 fact.new WS event for each execution fact ───────────────────────
async def test_fact_new_ws_events_from_execution(seeded_db, sit_ws_manager):
    """Each fact from execution triggers a fact.new WS broadcast."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)

    client = MagicMock(spec=BaseEngineClient)
    client.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="exec-002",
        output="Found open ports",
        facts=[
            {"trait": "service.http", "value": "80/tcp Apache 2.4"},
            {"trait": "service.https", "value": "443/tcp nginx 1.20"},
        ],
    ))
    client.is_available = AsyncMock(return_value=True)

    fc = FactCollector(sit_ws_manager)
    router = EngineRouter(
        c2_engine=client, fact_collector=fc,
        ws_manager=sit_ws_manager, mcp_engine=client,
    )

    await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    fact_events = [c for c in sit_ws_manager._calls if c[1] == "fact.new"]
    assert len(fact_events) >= 2, f"Expected >= 2 fact.new events, got {len(fact_events)}"


# ── 5.3 Successful execution writes poc.* fact ──────────────────────────
async def test_success_writes_poc_fact(seeded_db, sit_ws_manager):
    """Successful execution with PoC output writes poc.* trait to facts."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)

    client = MagicMock(spec=BaseEngineClient)
    client.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="exec-003",
        output="Proof of concept: LSASS dump successful",
        facts=[
            {"trait": "poc.lsass_dump", "value": "NTLM hashes extracted from memory"},
        ],
    ))
    client.is_available = AsyncMock(return_value=True)

    fc = FactCollector(sit_ws_manager)
    router = EngineRouter(
        c2_engine=client, fact_collector=fc,
        ws_manager=sit_ws_manager, mcp_engine=client,
    )

    await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    poc_row = await db.fetchrow(
        "SELECT trait, value FROM facts "
        "WHERE operation_id = $1 AND trait LIKE 'poc.%'",
        "test-op-1",
    )
    assert poc_row is not None, "poc.* fact should be in DB"
    assert poc_row["trait"].startswith("poc.")

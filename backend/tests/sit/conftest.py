"""SIT-specific fixtures — real services + real PostgreSQL, only external systems mocked."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.clients import BaseEngineClient, ExecutionResult
from app.services.c5isr_mapper import C5ISRMapper
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.orient_engine import OrientEngine
from app.services.agent_swarm import SwarmExecutor


# ---------------------------------------------------------------------------
# sit_ws_manager — recording WebSocket mock
# ---------------------------------------------------------------------------
@pytest.fixture
def sit_ws_manager():
    """WebSocket manager that records all broadcast calls for assertion."""
    manager = MagicMock()
    manager._calls: list[tuple[str, str, dict]] = []

    async def _broadcast(op_id: str, event_type: str, payload: dict = None):
        manager._calls.append((op_id, event_type, payload or {}))

    manager.broadcast = AsyncMock(side_effect=_broadcast)
    manager.active_connection_count = MagicMock(return_value=0)
    manager._broadcast_total = 0
    manager._broadcast_success = 0
    return manager


# ---------------------------------------------------------------------------
# Mock engine client — simulates C2/MCP engines
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_engine_client():
    """Mock BaseEngineClient that returns success by default."""
    client = MagicMock(spec=BaseEngineClient)
    client.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="mock-exec-001",
        output="Mock execution completed successfully",
        facts=[],
    ))
    client.is_available = AsyncMock(return_value=True)
    return client


# ---------------------------------------------------------------------------
# sit_services — full service stack with real DB, mock externals
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sit_services(seeded_db, sit_ws_manager, mock_engine_client):
    """Complete OODA service stack wired to real DB.

    External systems (LLM, C2, MCP) are mocked; services interact via real PostgreSQL.
    """
    fc = FactCollector(sit_ws_manager)
    orient = OrientEngine(sit_ws_manager)
    decision = DecisionEngine()
    router = EngineRouter(
        c2_engine=mock_engine_client,
        fact_collector=fc,
        ws_manager=sit_ws_manager,
        mcp_engine=mock_engine_client,
    )
    c5isr = C5ISRMapper(sit_ws_manager)
    swarm = SwarmExecutor(engine_router=router, ws_manager=sit_ws_manager)

    from app.services.ooda_controller import OODAController
    controller = OODAController(
        fact_collector=fc,
        orient_engine=orient,
        decision_engine=decision,
        engine_router=router,
        c5isr_mapper=c5isr,
        ws_manager=sit_ws_manager,
        swarm_executor=swarm,
    )

    return SimpleNamespace(
        controller=controller,
        fc=fc,
        orient=orient,
        decision=decision,
        router=router,
        c5isr=c5isr,
        swarm=swarm,
        ws=sit_ws_manager,
        db=seeded_db,
        engine_client=mock_engine_client,
    )


# ---------------------------------------------------------------------------
# sit_seeded_with_execution — seeded_db + 1 completed technique execution
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sit_seeded_with_execution(seeded_db):
    """Extends seeded_db with a completed technique execution that has result_summary.

    This lets FactCollector.collect() find data to extract.
    """
    exec_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await seeded_db.execute(
        "INSERT INTO technique_executions "
        "(id, technique_id, target_id, operation_id, engine, status, "
        "result_summary, started_at, completed_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        exec_id, "T1003.001", "test-target-1", "test-op-1", "mcp_ssh",
        "success",
        "Dumped LSASS memory: found NTLM hash for Administrator (aad3b435...)",
        now, now,
    )
    yield seeded_db


# ---------------------------------------------------------------------------
# sit_seeded_with_facts — seeded_db + pre-existing facts for Orient/Decide
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sit_seeded_with_facts(seeded_db):
    """Extends seeded_db with facts so Orient and Decide have data to work with."""
    now = datetime.now(timezone.utc)
    facts_data = [
        ("service.open_port", "22/tcp SSH OpenSSH 8.9", "service"),
        ("service.open_port", "445/tcp SMB", "service"),
        ("credential.ntlm_hash", "Administrator:aad3b435...", "credential"),
        ("host.os_version", "Windows Server 2022 Build 20348", "host"),
        ("network.subnet", "10.0.1.0/24", "network"),
    ]
    for trait, value, category in facts_data:
        await seeded_db.execute(
            "INSERT INTO facts (id, trait, value, category, "
            "source_technique_id, source_target_id, operation_id, score, collected_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            str(uuid.uuid4()), trait, value, category,
            "T1003.001", "test-target-1", "test-op-1", 1, now,
        )
    yield seeded_db

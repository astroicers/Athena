"""SIT: Compromise Gate — Act success + credential facts update target state.

Verifies that the OODA controller's Act phase correctly updates target
is_compromised, activates pending agents, and increments operation counters
when shell-capable credential facts exist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ── CG.1  credential.ssh fact -> is_compromised=TRUE ─────────────────────
async def test_ssh_credential_marks_compromised(sit_services):
    """Successful execution + credential.ssh fact -> target.is_compromised=TRUE."""
    db = sit_services.db

    # Insert a credential.ssh fact for the seeded target
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, 'credential.ssh', 'root:toor@10.0.1.5:22', 'credential', "
        "'test-target-1', 'test-op-1', 1, $2)",
        str(uuid.uuid4()), datetime.now(timezone.utc),
    )

    # Mock orient to recommend a technique, decision to auto-approve
    mock_rec = {
        "situation_assessment": "SSH credential found",
        "recommended_technique_id": "T1021.004",
        "confidence": 0.9,
        "reasoning_text": "test",
        "options": [{
            "technique_id": "T1021.004",
            "technique_name": "Remote Services: SSH",
            "reasoning": "test",
            "risk_level": "low",
            "recommended_engine": "mcp_ssh",
            "confidence": 0.9,
            "prerequisites": [],
        }],
    }
    sit_services.orient.analyze = AsyncMock(return_value=mock_rec)

    # Engine client returns success
    from app.clients import ExecutionResult
    sit_services.engine_client.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="exec-cg1",
        output="uid=0(root)", facts=[],
    ))

    await sit_services.controller.trigger_cycle(db, "test-op-1")

    row = await db.fetchrow(
        "SELECT is_compromised FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is True


# ── CG.2  success but no shell credential -> is_compromised unchanged ────
async def test_recon_success_no_compromise(sit_services):
    """Successful recon execution without shell credential does NOT set is_compromised."""
    db = sit_services.db

    # Ensure target starts as not compromised
    await db.execute(
        "UPDATE targets SET is_compromised = FALSE WHERE id = 'test-target-1'"
    )

    # No credential.ssh facts — only service facts
    mock_rec = {
        "situation_assessment": "Port scan complete",
        "recommended_technique_id": "T1046",
        "confidence": 0.8,
        "reasoning_text": "test",
        "options": [{
            "technique_id": "T1046",
            "technique_name": "Network Service Discovery",
            "reasoning": "test",
            "risk_level": "low",
            "recommended_engine": "mcp_recon",
            "confidence": 0.8,
            "prerequisites": [],
        }],
    }
    sit_services.orient.analyze = AsyncMock(return_value=mock_rec)

    from app.clients import ExecutionResult
    sit_services.engine_client.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="exec-cg2",
        output="22/tcp open ssh", facts=[],
    ))

    await sit_services.controller.trigger_cycle(db, "test-op-1")

    row = await db.fetchrow(
        "SELECT is_compromised FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is False


# ── CG.3  credential.mysql (non-shell) does NOT trigger compromise ───────
async def test_mysql_credential_no_compromise(sit_services):
    """Data-plane credential (credential.mysql) does not mark target compromised."""
    db = sit_services.db

    await db.execute(
        "UPDATE targets SET is_compromised = FALSE WHERE id = 'test-target-1'"
    )

    # Insert a non-shell credential
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, 'credential.mysql', 'admin:password@10.0.1.5:3306', 'credential', "
        "'test-target-1', 'test-op-1', 1, $2)",
        str(uuid.uuid4()), datetime.now(timezone.utc),
    )

    mock_rec = {
        "situation_assessment": "MySQL found",
        "recommended_technique_id": "T1078.001",
        "confidence": 0.85,
        "reasoning_text": "test",
        "options": [{
            "technique_id": "T1078.001",
            "technique_name": "Valid Accounts",
            "reasoning": "test",
            "risk_level": "low",
            "recommended_engine": "mcp_ssh",
            "confidence": 0.85,
            "prerequisites": [],
        }],
    }
    sit_services.orient.analyze = AsyncMock(return_value=mock_rec)

    from app.clients import ExecutionResult
    sit_services.engine_client.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="exec-cg3",
        output="MySQL 5.7", facts=[],
    ))

    await sit_services.controller.trigger_cycle(db, "test-op-1")

    row = await db.fetchrow(
        "SELECT is_compromised FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is False


# ── CG.4  successful execution activates pending agent ───────────────────
async def test_success_activates_pending_agent(sit_services):
    """Successful execution should set one pending agent to alive."""
    db = sit_services.db

    # Insert a pending agent
    await db.execute(
        "INSERT INTO agents (id, paw, operation_id, status, platform) "
        "VALUES ($1, 'agent-paw-001', 'test-op-1', 'pending', 'linux')",
        str(uuid.uuid4()),
    )

    # Add shell credential for compromise gate
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, 'credential.ssh', 'root:pass@10.0.1.5:22', 'credential', "
        "'test-target-1', 'test-op-1', 1, $2)",
        str(uuid.uuid4()), datetime.now(timezone.utc),
    )

    mock_rec = {
        "situation_assessment": "test",
        "recommended_technique_id": "T1021.004",
        "confidence": 0.9,
        "reasoning_text": "test",
        "options": [{
            "technique_id": "T1021.004",
            "technique_name": "SSH",
            "reasoning": "test",
            "risk_level": "low",
            "recommended_engine": "mcp_ssh",
            "confidence": 0.9,
            "prerequisites": [],
        }],
    }
    sit_services.orient.analyze = AsyncMock(return_value=mock_rec)

    from app.clients import ExecutionResult
    sit_services.engine_client.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="exec-cg4",
        output="ok", facts=[],
    ))

    await sit_services.controller.trigger_cycle(db, "test-op-1")

    agent_row = await db.fetchrow(
        "SELECT status FROM agents WHERE paw = 'agent-paw-001'"
    )
    assert agent_row is not None
    assert agent_row["status"] == "alive"


# ── CG.5  techniques_executed counter increments ─────────────────────────
async def test_techniques_executed_increments(sit_services):
    """Successful execution increments operations.techniques_executed."""
    db = sit_services.db

    before = await db.fetchval(
        "SELECT techniques_executed FROM operations WHERE id = 'test-op-1'"
    )

    mock_rec = {
        "situation_assessment": "test",
        "recommended_technique_id": "T1046",
        "confidence": 0.8,
        "reasoning_text": "test",
        "options": [{
            "technique_id": "T1046",
            "technique_name": "Discovery",
            "reasoning": "test",
            "risk_level": "low",
            "recommended_engine": "mcp_recon",
            "confidence": 0.8,
            "prerequisites": [],
        }],
    }
    sit_services.orient.analyze = AsyncMock(return_value=mock_rec)

    from app.clients import ExecutionResult
    sit_services.engine_client.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="exec-cg5",
        output="ok", facts=[],
    ))

    await sit_services.controller.trigger_cycle(db, "test-op-1")

    after = await db.fetchval(
        "SELECT techniques_executed FROM operations WHERE id = 'test-op-1'"
    )
    assert after >= (before or 0) + 1

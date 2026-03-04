# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for AgentCapabilityMatcher — SPEC-022, ADR-021."""

import uuid

import aiosqlite
import pytest

from app.services.agent_capability_matcher import AgentCapabilityMatcher


# ---------------------------------------------------------------------------
# DB helpers — insert parent rows before inserting agents
# ---------------------------------------------------------------------------

async def _ensure_operation(db: aiosqlite.Connection, operation_id: str) -> None:
    """Insert an operation row if it doesn't already exist."""
    await db.execute(
        "INSERT OR IGNORE INTO operations "
        "(id, code, name, codename, strategic_intent, status, current_ooda_phase) "
        "VALUES (?, ?, ?, ?, ?, 'active', 'observe')",
        (operation_id, f"CODE-{operation_id}", f"Op {operation_id}",
         f"CN-{operation_id}", "test intent"),
    )
    await db.commit()


async def _ensure_target(
    db: aiosqlite.Connection,
    host_id: str,
    operation_id: str,
) -> None:
    """Insert a target row if it doesn't already exist."""
    await _ensure_operation(db, operation_id)
    await db.execute(
        "INSERT OR IGNORE INTO targets "
        "(id, hostname, ip_address, os, role, operation_id) "
        "VALUES (?, ?, '10.0.0.1', 'Windows', 'server', ?)",
        (host_id, f"host-{host_id}", operation_id),
    )
    await db.commit()


async def _insert_agent(
    db: aiosqlite.Connection,
    paw: str,
    host_id: str,
    operation_id: str,
    status: str = "alive",
    privilege: str = "User",
    platform: str = "windows",
) -> None:
    """Insert an agent; ensures parent operation and target rows exist first."""
    await _ensure_target(db, host_id, operation_id)
    await db.execute(
        "INSERT INTO agents (id, paw, host_id, operation_id, status, privilege, platform) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), paw, host_id, operation_id, status, privilege, platform),
    )
    await db.commit()


async def _insert_playbook(
    db: aiosqlite.Connection,
    mitre_id: str,
    platform: str,
) -> None:
    """Insert a technique_playbooks row."""
    await db.execute(
        "INSERT OR IGNORE INTO technique_playbooks (id, mitre_id, platform, command) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), mitre_id, platform, "whoami"),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def matcher():
    return AgentCapabilityMatcher()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Test 1: No agents → None
async def test_no_agents_returns_none(seeded_db, matcher):
    result = await matcher.select_agent_for_technique(
        seeded_db, "op-1", "target-1", "T9999.001"
    )
    assert result is None


# Test 2: One alive agent, platform matches → returns paw
async def test_single_alive_agent_platform_match(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-A", "tgt-1", "op-1", platform="windows")
    await _insert_playbook(seeded_db, "T1059.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-1", "T1059.001")
    assert result == "paw-A"


# Test 3: One alive agent, platform does NOT match → None
async def test_platform_mismatch_returns_none(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-B", "tgt-2", "op-1", platform="linux")
    await _insert_playbook(seeded_db, "T1053.005", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-2", "T1053.005")
    assert result is None


# Test 4: Two agents, SYSTEM vs User, both platform match → SYSTEM
async def test_prefers_system_over_user(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-user", "tgt-3", "op-1", privilege="User", platform="windows")
    await _insert_agent(seeded_db, "paw-system", "tgt-3", "op-1", privilege="SYSTEM", platform="windows")
    await _insert_playbook(seeded_db, "T1003.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-3", "T1003.001")
    assert result == "paw-system"


# Test 5: Two agents, Admin vs User → Admin
async def test_prefers_admin_over_user(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-user2", "tgt-4", "op-1", privilege="User", platform="windows")
    await _insert_agent(seeded_db, "paw-admin", "tgt-4", "op-1", privilege="Admin", platform="windows")
    await _insert_playbook(seeded_db, "T1136.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-4", "T1136.001")
    assert result == "paw-admin"


# Test 6: Dead agent only → None
async def test_dead_agent_returns_none(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-dead", "tgt-5", "op-1", status="dead", platform="windows")
    await _insert_playbook(seeded_db, "T1059.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-5", "T1059.001")
    assert result is None


# Test 7: No playbook for technique → skip platform filter, return highest privilege
async def test_no_playbook_skips_platform_filter(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-sys", "tgt-6", "op-1", privilege="SYSTEM", platform="linux")
    # No playbook entry for T9998 — platform filter is skipped
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-6", "T9998")
    assert result == "paw-sys"


# Test 8: Windows technique, Linux agent → None
async def test_windows_technique_linux_agent_returns_none(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-linux", "tgt-7", "op-1", platform="linux")
    await _insert_playbook(seeded_db, "T1021.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-7", "T1021.001")
    assert result is None


# Test 9: Linux technique, Windows agent → None
async def test_linux_technique_windows_agent_returns_none(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-win", "tgt-8", "op-1", platform="windows")
    await _insert_playbook(seeded_db, "T1053.003", "linux")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-8", "T1053.003")
    assert result is None


# Test 10: Case-insensitive platform match ("Windows" agent vs "windows" playbook)
async def test_platform_case_insensitive(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-C", "tgt-9", "op-1", platform="Windows")
    await _insert_playbook(seeded_db, "T1021.002", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-9", "T1021.002")
    assert result == "paw-C"


# Test 11: Case-insensitive privilege ("SYSTEM" stored, ranks correctly)
async def test_privilege_case_insensitive(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-SYS", "tgt-10", "op-1", privilege="SYSTEM", platform="windows")
    await _insert_agent(seeded_db, "paw-ADM", "tgt-10", "op-1", privilege="admin", platform="windows")
    await _insert_playbook(seeded_db, "T1055.001", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-10", "T1055.001")
    assert result == "paw-SYS"


# Test 12: Multiple SYSTEM privilege agents → returns one of them (any)
async def test_multiple_system_agents_returns_one(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-sys1", "tgt-11", "op-1", privilege="SYSTEM", platform="windows")
    await _insert_agent(seeded_db, "paw-sys2", "tgt-11", "op-1", privilege="SYSTEM", platform="windows")
    await _insert_playbook(seeded_db, "T1003.002", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-11", "T1003.002")
    assert result in {"paw-sys1", "paw-sys2"}


# Test 13: operation_id isolation — different operation's agents not returned
async def test_operation_isolation(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-other-op", "tgt-12", "op-OTHER", platform="windows")
    await _insert_playbook(seeded_db, "T1021.003", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-12", "T1021.003")
    assert result is None


# Test 14: Mixed alive/dead agents → only alive returned
async def test_returns_only_alive_agent(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-dead2", "tgt-13", "op-1", status="dead", platform="linux")
    await _insert_agent(seeded_db, "paw-alive", "tgt-13", "op-1", status="alive", platform="linux")
    await _insert_playbook(seeded_db, "T1053.003", "linux")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-13", "T1053.003")
    assert result == "paw-alive"


# Test 15: Unknown privilege → rank 0 → SYSTEM preferred
async def test_unknown_privilege_lowest_rank(seeded_db, matcher):
    await _insert_agent(seeded_db, "paw-unknown", "tgt-14", "op-1", privilege="NetworkService", platform="windows")
    await _insert_agent(seeded_db, "paw-sys3", "tgt-14", "op-1", privilege="SYSTEM", platform="windows")
    await _insert_playbook(seeded_db, "T1021.004", "windows")
    result = await matcher.select_agent_for_technique(seeded_db, "op-1", "tgt-14", "T1021.004")
    assert result == "paw-sys3"

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests: lateral movement topology edges + orient multi-protocol credentials."""

import uuid

import pytest


async def test_orient_includes_rdp_winrm_creds(seeded_db):
    """Section 7.7 should pick up credential.rdp and credential.winrm facts."""
    import aiosqlite
    from unittest.mock import AsyncMock, MagicMock
    from app.services.orient_engine import OrientEngine

    seeded_db.row_factory = aiosqlite.Row

    # Insert multi-protocol credential facts
    for trait in ("credential.rdp", "credential.winrm"):
        await seeded_db.execute(
            "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
            "VALUES (?, 'test-op-1', 'test-target-1', ?, 'admin:pass@10.0.0.1', 'credential', 1)",
            (str(uuid.uuid4()), trait),
        )
    await seeded_db.commit()

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    engine = OrientEngine(ws_manager=ws)
    _system, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "Test observe summary")

    # The lateral section should mention available credentials
    assert "Available credentials" in user_prompt
    assert "T1021.001 (WinRM/RDP)" in user_prompt


async def test_topology_lateral_edges(seeded_db, client):
    """Topology should include host-to-host lateral edges when credentials + agents exist."""
    import aiosqlite

    seeded_db.row_factory = aiosqlite.Row

    # Add a second target
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('test-target-2', 'WS-01', '10.0.1.10', 'Windows 10', 'Workstation', 'test-op-1')"
    )
    # Add an alive agent on target-2
    await seeded_db.execute(
        "INSERT INTO agents (id, paw, host_id, status, operation_id) "
        "VALUES ('test-agent-2', 'def456', 'test-target-2', 'alive', 'test-op-1')"
    )
    # Add credential fact on target-1 (source) that enables pivoting
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.1.10:22', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    resp = await client.get("/api/operations/test-op-1/topology")
    assert resp.status_code == 200
    data = resp.json()

    lateral_edges = [e for e in data["edges"] if e.get("data", {}).get("phase") == "lateral"]
    assert len(lateral_edges) >= 1

    edge = lateral_edges[0]
    assert edge["source"] == "test-target-1"
    assert edge["target"] == "test-target-2"
    assert edge["label"] == "Lateral"


async def test_topology_no_false_lateral_edges(seeded_db, client):
    """No lateral edges should appear when there are no agents on other targets."""
    import aiosqlite

    seeded_db.row_factory = aiosqlite.Row

    # Add a second target but NO agent on it
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('test-target-3', 'WS-02', '10.0.1.11', 'Windows 10', 'Workstation', 'test-op-1')"
    )
    # Credential fact exists but no alive agent on target-3
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.rdp', 'admin:pass@10.0.1.11:3389', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    resp = await client.get("/api/operations/test-op-1/topology")
    assert resp.status_code == 200
    data = resp.json()

    lateral_edges = [e for e in data["edges"] if e.get("data", {}).get("phase") == "lateral"]
    assert len(lateral_edges) == 0

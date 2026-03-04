# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Integration tests for Tool Registry CRUD API (GET/POST/PATCH/DELETE)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import (
    _CREATE_TABLES,
    _seed_technique_playbooks,
    _seed_tool_registry,
    get_db,
)
from app.main import app

import aiosqlite


# ---------------------------------------------------------------------------
# Seed SQL — minimal data for operations (required by foreign key schema)
# ---------------------------------------------------------------------------
_SEED_STATEMENTS: list[str] = [
    """
    INSERT INTO operations (id, code, name, codename, strategic_intent, status, current_ooda_phase)
    VALUES ('test-op-1', 'OP-TEST-001', 'Test Operation', 'PHANTOM-TEST',
            'Test strategic intent', 'active', 'observe');
    """,
    """
    INSERT INTO targets (id, hostname, ip_address, os, role, operation_id)
    VALUES ('test-target-1', 'DC-01', '10.0.1.5', 'Windows Server 2022',
            'Domain Controller', 'test-op-1');
    """,
    """
    INSERT INTO agents (id, paw, host_id, status, operation_id)
    VALUES ('test-agent-1', 'abc123', 'test-target-1', 'alive', 'test-op-1');
    """,
    """
    INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
    VALUES ('test-tech-1', 'T1003.001', 'LSASS Memory', 'Credential Access',
            'TA0006', 'medium');
    """,
]


# ---------------------------------------------------------------------------
# Fixture: tools_client — httpx.AsyncClient with tool_registry seeded
# ---------------------------------------------------------------------------
@pytest.fixture
async def tools_client():
    """Async HTTP client with seeded tool_registry for tool API tests.

    Creates an isolated in-memory SQLite database, applies the full schema,
    seeds both technique_playbooks and tool_registry, and overrides the
    ``get_db`` dependency so every request uses this test database.
    """
    db = await aiosqlite.connect(":memory:")
    await db.execute("PRAGMA foreign_keys = ON;")
    for ddl in _CREATE_TABLES:
        await db.execute(ddl)
    await db.commit()

    # Seed minimal operation data (some tables have foreign key constraints)
    for stmt in _SEED_STATEMENTS:
        await db.execute(stmt)
    await db.commit()

    # Seed technique_playbooks and tool_registry
    await _seed_technique_playbooks(db)
    await _seed_tool_registry(db)
    await db.commit()

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await db.close()


# ---------------------------------------------------------------------------
# 1. GET /api/tools — list all seeded tools
# ---------------------------------------------------------------------------
async def test_list_tools(tools_client: AsyncClient):
    """GET /api/tools returns the 10 seeded tools."""
    resp = await tools_client.get("/api/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 10


# ---------------------------------------------------------------------------
# 2. GET /api/tools?kind=tool — filter by kind=tool
# ---------------------------------------------------------------------------
async def test_list_tools_filter_kind(tools_client: AsyncClient):
    """GET /api/tools?kind=tool returns only the 4 tool-kind entries."""
    resp = await tools_client.get("/api/tools", params={"kind": "tool"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    assert all(t["kind"] == "tool" for t in data)


# ---------------------------------------------------------------------------
# 3. GET /api/tools?kind=engine — filter by kind=engine
# ---------------------------------------------------------------------------
async def test_list_tools_filter_engine(tools_client: AsyncClient):
    """GET /api/tools?kind=engine returns only the 6 engine entries."""
    resp = await tools_client.get("/api/tools", params={"kind": "engine"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    assert all(t["kind"] == "engine" for t in data)


# ---------------------------------------------------------------------------
# 4. GET /api/tools/{tool_id} — get by slug
# ---------------------------------------------------------------------------
async def test_get_tool_by_id(tools_client: AsyncClient):
    """GET /api/tools/nmap returns the Nmap tool with correct fields."""
    resp = await tools_client.get("/api/tools/nmap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_id"] == "nmap"
    assert data["name"] == "Nmap"
    assert data["kind"] == "tool"
    assert data["source"] == "seed"
    assert data["enabled"] is True


# ---------------------------------------------------------------------------
# 5. GET /api/tools/{tool_id} — not found
# ---------------------------------------------------------------------------
async def test_get_tool_not_found(tools_client: AsyncClient):
    """GET /api/tools/nonexistent returns 404."""
    resp = await tools_client.get("/api/tools/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. POST /api/tools — create a new user tool
# ---------------------------------------------------------------------------
async def test_create_tool(tools_client: AsyncClient):
    """POST /api/tools creates a user tool and returns 201."""
    payload = {
        "tool_id": "custom-scanner",
        "name": "Custom Scanner",
        "description": "A custom vulnerability scanner",
        "kind": "tool",
        "category": "vulnerability_scanning",
        "risk_level": "medium",
        "mitre_techniques": ["T1595"],
        "output_traits": ["scan.result"],
    }
    resp = await tools_client.post("/api/tools", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool_id"] == "custom-scanner"
    assert data["name"] == "Custom Scanner"
    assert data["source"] == "user"
    assert data["enabled"] is True
    assert data["id"]  # UUID should be present


# ---------------------------------------------------------------------------
# 7. POST /api/tools — duplicate tool_id returns 409
# ---------------------------------------------------------------------------
async def test_create_tool_duplicate(tools_client: AsyncClient):
    """POST /api/tools with an existing tool_id returns 409 Conflict."""
    payload = {
        "tool_id": "nmap",
        "name": "Duplicate Nmap",
    }
    resp = await tools_client.post("/api/tools", json=payload)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 8. PATCH /api/tools/{tool_id} — update description
# ---------------------------------------------------------------------------
async def test_update_tool(tools_client: AsyncClient):
    """PATCH /api/tools/nmap updates the description field."""
    resp = await tools_client.patch(
        "/api/tools/nmap",
        json={"description": "Updated Nmap description"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Updated Nmap description"
    assert data["tool_id"] == "nmap"


# ---------------------------------------------------------------------------
# 9. PATCH /api/tools/{tool_id} — toggle enabled flag
# ---------------------------------------------------------------------------
async def test_toggle_enabled(tools_client: AsyncClient):
    """PATCH /api/tools/nmap with enabled=false disables the tool."""
    resp = await tools_client.patch(
        "/api/tools/nmap",
        json={"enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False

    # Verify it persisted via GET
    get_resp = await tools_client.get("/api/tools/nmap")
    assert get_resp.json()["enabled"] is False


# ---------------------------------------------------------------------------
# 10. DELETE /api/tools/{tool_id} — seed tool returns 403
# ---------------------------------------------------------------------------
async def test_delete_seed_tool(tools_client: AsyncClient):
    """DELETE /api/tools/nmap returns 403 because seed tools cannot be deleted."""
    resp = await tools_client.delete("/api/tools/nmap")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 11. DELETE /api/tools/{tool_id} — user tool returns 204
# ---------------------------------------------------------------------------
async def test_delete_user_tool(tools_client: AsyncClient):
    """Create a user tool, then delete it — returns 204 and tool is gone."""
    # Create
    create_resp = await tools_client.post(
        "/api/tools",
        json={
            "tool_id": "disposable-tool",
            "name": "Disposable Tool",
        },
    )
    assert create_resp.status_code == 201

    # Delete
    del_resp = await tools_client.delete("/api/tools/disposable-tool")
    assert del_resp.status_code == 204

    # Verify it is gone
    get_resp = await tools_client.get("/api/tools/disposable-tool")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# 12. DELETE /api/tools/{tool_id} — not found returns 404
# ---------------------------------------------------------------------------
async def test_delete_not_found(tools_client: AsyncClient):
    """DELETE /api/tools/nonexistent returns 404."""
    resp = await tools_client.delete("/api/tools/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 13. POST /api/tools/{tool_id}/check — health check stub
# ---------------------------------------------------------------------------
async def test_check_tool(tools_client: AsyncClient):
    """POST /api/tools/nmap/check returns available status for an enabled tool."""
    resp = await tools_client.post("/api/tools/nmap/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_id"] == "nmap"
    assert data["available"] is True
    assert "Nmap" in data["detail"]

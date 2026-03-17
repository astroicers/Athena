# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Recommendations router."""

import pytest
import pytest_asyncio
import asyncpg
from httpx import ASGITransport, AsyncClient
from uuid import uuid4


# ---------------------------------------------------------------------------
# Local fixture: client_with_db — provides both client and db using SAME connection
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client_with_db(seeded_db: asyncpg.Connection):
    """Return (client, db) sharing the same seeded_db connection.

    This avoids the double-truncate issue that happens when both ``client``
    and ``seeded_db`` are requested as separate test parameters (pytest-asyncio
    creates two separate instances, the second of which TRUNCATEs away the
    first's seed data).
    """
    from app.database import get_db
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from app.main import app

    count = await seeded_db.fetchval("SELECT COUNT(*) FROM technique_playbooks")
    if count == 0:
        for seed in TECHNIQUE_PLAYBOOK_SEEDS:
            await seeded_db.execute(
                """INSERT INTO technique_playbooks
                   (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
                   VALUES ($1, $2, $3, $4, $5, $6, 'seed', $7)
                   ON CONFLICT DO NOTHING""",
                str(uuid4()), seed["mitre_id"], seed["platform"],
                seed["command"], seed.get("output_parser"),
                seed["facts_traits"], seed["tags"],
            )

    async def _override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, seeded_db

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_get_latest_recommendation_none(client: AsyncClient):
    """GET /api/operations/test-op-1/recommendations/latest returns 200 with null when empty."""
    resp = await client.get("/api/operations/test-op-1/recommendations/latest")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_latest_recommendation_with_data(client_with_db):
    """GET /api/operations/test-op-1/recommendations/latest returns the inserted recommendation."""
    client, db = client_with_db

    await db.execute("""
        INSERT INTO ooda_iterations (id, operation_id, iteration_number, phase, started_at)
        VALUES ('ooda-1', 'test-op-1', 1, 'orient', NOW())
    """)
    await db.execute("""
        INSERT INTO recommendations (
            id, operation_id, ooda_iteration_id,
            situation_assessment, recommended_technique_id,
            confidence, options, reasoning_text, created_at
        )
        VALUES (
            'rec-1', 'test-op-1', 'ooda-1',
            'Initial assessment', 'T1003.001',
            0.85, '[]', 'Because reasons', NOW()
        )
    """)

    resp = await client.get("/api/operations/test-op-1/recommendations/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["id"] == "rec-1"
    assert data["operation_id"] == "test-op-1"
    assert data["ooda_iteration_id"] == "ooda-1"
    assert data["recommended_technique_id"] == "T1003.001"


async def test_list_recommendations_empty(client: AsyncClient):
    """GET /api/operations/test-op-1/recommendations returns 200 with empty list when empty."""
    resp = await client.get("/api/operations/test-op-1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_list_recommendations_with_data(client_with_db):
    """GET /api/operations/test-op-1/recommendations returns all inserted recommendations."""
    client, db = client_with_db

    await db.execute("""
        INSERT INTO ooda_iterations (id, operation_id, iteration_number, phase, started_at)
        VALUES ('ooda-2', 'test-op-1', 2, 'orient', NOW())
    """)
    await db.execute("""
        INSERT INTO recommendations (
            id, operation_id, ooda_iteration_id,
            situation_assessment, recommended_technique_id,
            confidence, options, reasoning_text, created_at
        )
        VALUES
        (
            'rec-2a', 'test-op-1', 'ooda-2',
            'Assessment A', 'T1003.001',
            0.80, '[]', 'Reasoning A', NOW() - INTERVAL '1 minute'
        ),
        (
            'rec-2b', 'test-op-1', 'ooda-2',
            'Assessment B', 'T1059.001',
            0.75, '[]', 'Reasoning B', NOW()
        )
    """)

    resp = await client.get("/api/operations/test-op-1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_accept_recommendation(client_with_db):
    """POST /api/operations/test-op-1/recommendations/{id}/accept sets accepted=true."""
    client, db = client_with_db

    await db.execute("""
        INSERT INTO ooda_iterations (id, operation_id, iteration_number, phase, started_at)
        VALUES ('ooda-3', 'test-op-1', 3, 'orient', NOW())
    """)
    await db.execute("""
        INSERT INTO recommendations (
            id, operation_id, ooda_iteration_id,
            situation_assessment, recommended_technique_id,
            confidence, options, reasoning_text, accepted, created_at
        )
        VALUES (
            'rec-3', 'test-op-1', 'ooda-3',
            'Accept test', 'T1003.001',
            0.90, '[]', 'Good reasoning', FALSE, NOW()
        )
    """)

    resp = await client.post(
        "/api/operations/test-op-1/recommendations/rec-3/accept"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "rec-3"
    assert data["accepted"] is True


async def test_accept_recommendation_not_found(client: AsyncClient):
    """POST /api/operations/test-op-1/recommendations/{bad_id}/accept returns 404."""
    resp = await client.post(
        "/api/operations/test-op-1/recommendations/nonexistent-rec-id/accept"
    )
    assert resp.status_code == 404

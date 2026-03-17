# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Engagements router."""

import pytest
from httpx import AsyncClient

BASE_URL = "/api/operations/test-op-1/engagement"

ENGAGEMENT_PAYLOAD = {
    "client_name": "Test Corp",
    "contact_email": "test@example.com",
    "in_scope": ["10.0.1.0/24"],
    "out_of_scope": [],
    "start_time": None,
    "end_time": None,
    "emergency_contact": "sec@test.com",
}


async def test_create_engagement_happy_path(client: AsyncClient, seeded_db):
    """POST creates an engagement and returns 201 with correct fields."""
    resp = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["client_name"] == "Test Corp"
    assert body["contact_email"] == "test@example.com"
    assert body["in_scope"] == ["10.0.1.0/24"]
    assert body["out_of_scope"] == []
    assert body["status"] == "draft"
    assert body["operation_id"] == "test-op-1"
    assert body["id"]


async def test_create_engagement_duplicate_returns_409(client: AsyncClient, seeded_db):
    """POSTing a second engagement for the same operation returns 409."""
    first = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert first.status_code == 201, first.text

    second = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


async def test_create_engagement_unknown_op_returns_404(client: AsyncClient):
    """POST to an unknown operation_id returns 404."""
    resp = await client.post(
        "/api/operations/nonexistent-op/engagement",
        json=ENGAGEMENT_PAYLOAD,
    )
    assert resp.status_code == 404


async def test_get_engagement_happy_path(client: AsyncClient, seeded_db):
    """GET returns the previously created engagement."""
    create = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert create.status_code == 201, create.text

    resp = await client.get(BASE_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body["client_name"] == "Test Corp"
    assert body["operation_id"] == "test-op-1"


async def test_get_engagement_none_returns_404(client: AsyncClient):
    """GET when no engagement exists for the operation returns 404."""
    resp = await client.get(BASE_URL)
    assert resp.status_code == 404


async def test_activate_engagement(client: AsyncClient, seeded_db):
    """PATCH /activate transitions status from draft to active."""
    create = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert create.status_code == 201, create.text
    assert create.json()["status"] == "draft"

    resp = await client.patch(f"{BASE_URL}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_activate_already_active_is_idempotent(client: AsyncClient, seeded_db):
    """PATCH /activate on an already-active engagement returns 200 without error."""
    create = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert create.status_code == 201, create.text

    first = await client.patch(f"{BASE_URL}/activate")
    assert first.status_code == 200
    assert first.json()["status"] == "active"

    second = await client.patch(f"{BASE_URL}/activate")
    assert second.status_code == 200
    assert second.json()["status"] == "active"


async def test_suspend_engagement(client: AsyncClient, seeded_db):
    """PATCH /suspend sets the engagement status to suspended."""
    create = await client.post(BASE_URL, json=ENGAGEMENT_PAYLOAD)
    assert create.status_code == 201, create.text

    resp = await client.patch(f"{BASE_URL}/suspend")
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"

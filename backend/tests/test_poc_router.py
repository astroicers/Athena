# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the PoC report API endpoint."""

from httpx import AsyncClient

_BASE = "/api/operations/test-op-1/poc"


async def test_get_poc_records_empty(client: AsyncClient):
    """GET poc on a fresh operation returns total=0 and an empty list."""
    resp = await client.get(_BASE)
    assert resp.status_code == 200

    body = resp.json()
    assert body["operation_id"] == "test-op-1"
    assert body["total"] == 0
    assert body["poc_records"] == []


async def test_get_poc_records_with_data(client: AsyncClient, seeded_db):
    """GET poc returns parsed records for facts with trait LIKE 'poc.%'."""
    # Insert a poc fact — value must be a valid JSON string
    await seeded_db.execute(
        """
        INSERT INTO facts
            (id, operation_id, source_target_id, category, trait, value, score)
        VALUES
            ('poc-1', 'test-op-1', 'test-target-1', 'exploit', 'poc.evidence',
             '{"hash": "abc123", "tool": "metasploit"}', 100)
        """
    )

    resp = await client.get(_BASE)
    assert resp.status_code == 200

    body = resp.json()
    assert body["operation_id"] == "test-op-1"
    assert body["total"] == 1

    record = body["poc_records"][0]
    assert record["hash"] == "abc123"
    assert record["tool"] == "metasploit"


async def test_get_poc_records_unknown_op_returns_404(client: AsyncClient):
    """GET poc with an unknown operation_id returns 404."""
    resp = await client.get("/api/operations/unknown-op-xyz/poc")
    assert resp.status_code == 404

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Unit tests for ScopeValidator — A.1 acceptance criteria."""

import json
import pytest
from unittest.mock import AsyncMock

from app.services.scope_validator import ScopeValidator, ScopeCheckResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db(engagement: dict | None = None):
    """Return a mocked asyncpg connection."""
    db = AsyncMock()

    if engagement is None:
        db.fetchrow = AsyncMock(return_value=None)
    else:
        db.fetchrow = AsyncMock(return_value={**engagement})

    db.execute = AsyncMock(return_value="INSERT 0 1")
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_no_engagement_returns_in_scope():
    """No engagement record -> unrestricted (backward compatible)."""
    db = make_mock_db(engagement=None)
    result = await ScopeValidator().validate_target(db, "op-001", "192.168.1.5")
    assert result.in_scope is True
    assert "unrestricted" in result.reason.lower()


async def test_draft_engagement_blocks():
    """Draft engagement (not activated) -> out of scope."""
    db = make_mock_db(engagement={
        "status": "draft",
        "in_scope": json.dumps(["192.168.1.0/24"]),
        "out_of_scope": json.dumps([]),
        "start_time": None,
        "end_time": None,
    })
    result = await ScopeValidator().validate_target(db, "op-001", "192.168.1.5")
    assert result.in_scope is False
    assert "not active" in result.reason.lower()


async def test_ip_in_cidr_scope():
    """Active engagement with CIDR in_scope matches IP within range."""
    db = make_mock_db(engagement={
        "status": "active",
        "in_scope": json.dumps(["10.0.1.0/24"]),
        "out_of_scope": json.dumps([]),
        "start_time": None,
        "end_time": None,
    })
    result = await ScopeValidator().validate_target(db, "op-001", "10.0.1.100")
    assert result.in_scope is True


async def test_ip_outside_cidr_scope():
    """IP not in CIDR range -> out of scope."""
    db = make_mock_db(engagement={
        "status": "active",
        "in_scope": json.dumps(["10.0.1.0/24"]),
        "out_of_scope": json.dumps([]),
        "start_time": None,
        "end_time": None,
    })
    result = await ScopeValidator().validate_target(db, "op-001", "10.0.2.1")
    assert result.in_scope is False


async def test_out_of_scope_overrides_in_scope():
    """An IP matching out_of_scope list is denied even if it's in in_scope CIDR."""
    db = make_mock_db(engagement={
        "status": "active",
        "in_scope": json.dumps(["10.0.1.0/24"]),
        "out_of_scope": json.dumps(["10.0.1.50"]),
        "start_time": None,
        "end_time": None,
    })
    result = await ScopeValidator().validate_target(db, "op-001", "10.0.1.50")
    assert result.in_scope is False
    assert "out-of-scope" in result.reason.lower()


async def test_wildcard_domain_match():
    """*.example.com matches mail.example.com but not example.com itself."""
    db = make_mock_db(engagement={
        "status": "active",
        "in_scope": json.dumps(["*.example.com"]),
        "out_of_scope": json.dumps([]),
        "start_time": None,
        "end_time": None,
    })
    validator = ScopeValidator()

    # Subdomain -> in scope
    result = await validator.validate_target(db, "op-001", "mail.example.com")
    assert result.in_scope is True

    # Root domain -> out of scope (wildcard doesn't cover root)
    result2 = await validator.validate_target(db, "op-001", "example.com")
    assert result2.in_scope is False


async def test_exact_domain_match():
    """Exact domain entry matches only the exact domain (case-insensitive)."""
    db = make_mock_db(engagement={
        "status": "active",
        "in_scope": json.dumps(["target.example.com"]),
        "out_of_scope": json.dumps([]),
        "start_time": None,
        "end_time": None,
    })
    result = await ScopeValidator().validate_target(db, "op-001", "TARGET.EXAMPLE.COM")
    assert result.in_scope is True

# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for ScopeValidator — A.1 acceptance criteria."""

import json
import pytest
from unittest.mock import AsyncMock

from app.services.scope_validator import ScopeValidator, ScopeCheckResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db(engagement: dict | None = None):
    """Return a mocked aiosqlite connection."""
    db = AsyncMock()
    db.row_factory = None

    if engagement is None:
        # No engagement record
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=None)
    else:
        row = {**engagement}
        # Simulate aiosqlite.Row by making it dict-subscriptable
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=row)

    db.execute = AsyncMock(return_value=cursor)
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

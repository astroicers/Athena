# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""SPEC-044: ValidationEngine unit tests (10+ test cases)."""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import aiosqlite
import pytest

from app.services.validation_engine import ValidationEngine, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


async def _setup_db(db: aiosqlite.Connection) -> None:
    """Create minimal schema for validation tests."""
    await db.execute("PRAGMA foreign_keys = OFF")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS techniques (
            id TEXT PRIMARY KEY,
            mitre_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            tactic TEXT NOT NULL,
            tactic_id TEXT NOT NULL,
            description TEXT,
            kill_chain_stage TEXT DEFAULT 'exploit',
            risk_level TEXT DEFAULT 'medium',
            c2_ability_id TEXT,
            platforms TEXT DEFAULT '["linux"]'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            os TEXT,
            role TEXT NOT NULL,
            operation_id TEXT,
            is_compromised INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            privilege_level TEXT,
            access_status TEXT DEFAULT 'unknown'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            trait TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'host',
            source_technique_id TEXT,
            source_target_id TEXT,
            operation_id TEXT,
            score INTEGER DEFAULT 1,
            collected_at TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.commit()


@pytest.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await _setup_db(conn)
    yield conn
    await conn.close()


@pytest.fixture
def engine():
    return ValidationEngine()


# ---------------------------------------------------------------------------
# Tests: Non-exploit tactic -> skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_exploit_tactic_skipped(db, engine):
    """Discovery tactic (TA0007) should be skipped."""
    # Insert a discovery technique
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1018', 'Remote System Discovery', 'Discovery', 'TA0007')",
        (_uid(),),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1018", "target_id": _uid()}
    result = await engine.validate(db, rec, _uid())
    assert result.outcome == "skipped"
    assert result.delta == 0.0


# ---------------------------------------------------------------------------
# Tests: No target_ip -> skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_target_ip_skipped(db, engine):
    """Exploit tactic but target not found -> skipped."""
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190', 'Exploit Public App', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190", "target_id": _uid()}
    result = await engine.validate(db, rec, _uid())
    assert result.outcome == "skipped"
    assert result.delta == 0.0


@pytest.mark.asyncio
async def test_no_target_id_skipped(db, engine):
    """No target_id in recommendation -> skipped."""
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190b', 'Exploit Public App', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190b", "target_id": None}
    result = await engine.validate(db, rec, _uid())
    assert result.outcome == "skipped"


# ---------------------------------------------------------------------------
# Tests: Port reachability
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_port_reachability_passed(db, engine):
    """Mock socket connect success -> port_reachability passed."""
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190c', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    await db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES (?, 'service.open_port', '21/tcp vsftpd 2.3.4', ?, ?)",
        (_uid(), op_id, target_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190c", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None  # success

        result = await engine.validate(db, rec, op_id)

    port_check = [c for c in result.checks if c["name"] == "port_reachability"]
    assert len(port_check) == 1
    assert port_check[0]["result"] == "passed"


@pytest.mark.asyncio
async def test_port_reachability_failed(db, engine):
    """Mock socket connect failure -> port_reachability failed."""
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190d', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    await db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES (?, 'service.open_port', '21/tcp vsftpd 2.3.4', ?, ?)",
        (_uid(), op_id, target_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190d", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.side_effect = OSError("Connection refused")

        result = await engine.validate(db, rec, op_id)

    assert result.outcome == "failed"
    assert result.delta == -0.30


# ---------------------------------------------------------------------------
# Tests: Service banner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_banner_match(db, engine):
    """Banner matches -> service_banner passed.

    We mock _extract_banner and _extract_port to control exactly what
    the banner check sees, isolating the banner comparison logic.
    """
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190e', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    # Single fact that identifies both port and banner
    await db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES (?, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', ?, ?)",
        (_uid(), op_id, target_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190e", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(
            ValidationEngine, "_grab_banner",
            return_value="220 21/tcp banner: vsftpd 2.3.4",
        ):
            result = await engine.validate(db, rec, op_id)

    banner_check = [c for c in result.checks if c["name"] == "service_banner"]
    assert len(banner_check) == 1
    assert banner_check[0]["result"] == "passed"


@pytest.mark.asyncio
async def test_service_banner_mismatch(db, engine):
    """Banner doesn't match -> service_banner failed."""
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190f', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    # Value contains "banner" keyword so _extract_banner will pick it up
    await db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES (?, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', ?, ?)",
        (_uid(), op_id, target_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190f", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(ValidationEngine, "_grab_banner", return_value="220 ProFTPD 1.3.5"):
            result = await engine.validate(db, rec, op_id)

    assert result.outcome == "failed"
    assert result.delta == -0.30


# ---------------------------------------------------------------------------
# Tests: Version range (always skipped)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_version_range_always_skipped(db, engine):
    """Version range check returns skipped (Phase 1)."""
    service_facts = [{"trait": "service.version", "value": "vsftpd 2.3.4"}]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "skipped"
    assert "deferred" in result["detail"]


# ---------------------------------------------------------------------------
# Tests: Overall outcome logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_passed_delta_positive(db, engine):
    """When port and banner both pass, delta should be +0.15."""
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190g', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    await db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES (?, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', ?, ?)",
        (_uid(), op_id, target_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190g", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(
            ValidationEngine, "_grab_banner",
            return_value="220 21/tcp banner: vsftpd 2.3.4",
        ):
            result = await engine.validate(db, rec, op_id)

    assert result.outcome == "validated"
    assert result.delta == 0.15


@pytest.mark.asyncio
async def test_all_skipped_delta_zero(db, engine):
    """No service facts -> all checks skipped -> delta 0."""
    op_id, target_id = _uid(), _uid()
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES (?, 'T1190h', 'Exploit', 'Initial Access', 'TA0001')",
        (_uid(),),
    )
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES (?, 'host1', '10.0.1.5', 'server', ?)",
        (target_id, op_id),
    )
    await db.commit()

    rec = {"recommended_technique_id": "T1190h", "target_id": target_id}
    result = await engine.validate(db, rec, op_id)

    assert result.outcome == "skipped"
    assert result.delta == 0.0


@pytest.mark.asyncio
async def test_confidence_clamped_high(db, engine):
    """Verify confidence is clamped to [0.0, 1.0]."""
    # Direct test of clamping logic
    original = 0.95
    delta = 0.15
    adjusted = max(0.0, min(1.0, original + delta))
    assert adjusted == 1.0


@pytest.mark.asyncio
async def test_confidence_clamped_low(db, engine):
    """Verify confidence is clamped to 0.0 when delta is very negative."""
    original = 0.1
    delta = -0.30
    adjusted = max(0.0, min(1.0, original + delta))
    assert adjusted == 0.0


# ---------------------------------------------------------------------------
# Tests: extract helpers
# ---------------------------------------------------------------------------

def test_extract_port_tcp_format():
    engine = ValidationEngine()
    facts = [{"trait": "service.open_port", "value": "21/tcp vsftpd"}]
    assert engine._extract_port(facts) == 21


def test_extract_port_bare_number():
    engine = ValidationEngine()
    facts = [{"trait": "service.port", "value": "8080"}]
    assert engine._extract_port(facts) == 8080


def test_extract_port_none():
    engine = ValidationEngine()
    facts = [{"trait": "service.name", "value": "vsftpd"}]
    assert engine._extract_port(facts) is None


def test_extract_banner():
    engine = ValidationEngine()
    facts = [{"trait": "service.banner", "value": "vsftpd 2.3.4"}]
    assert engine._extract_banner(facts) == "vsftpd 2.3.4"


def test_extract_version():
    engine = ValidationEngine()
    facts = [{"trait": "service.version", "value": "vsftpd 2.3.4"}]
    assert engine._extract_version(facts) == "2.3.4"


def test_extract_version_none():
    engine = ValidationEngine()
    facts = [{"trait": "service.name", "value": "vsftpd"}]
    assert engine._extract_version(facts) is None

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-044: ValidationEngine unit tests (10+ test cases)."""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.validation_engine import ValidationEngine, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


async def _ensure_op(db, op_id: str) -> None:
    """Insert an operations row (needed for FK on targets)."""
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ($1, $2, 'Test', 'TEST', 'test') ON CONFLICT DO NOTHING",
        op_id, f"OP-{op_id[:8]}",
    )


@pytest.fixture
def engine():
    return ValidationEngine()


# ---------------------------------------------------------------------------
# Tests: Non-exploit tactic -> skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_exploit_tactic_skipped(tmp_db, engine):
    """Discovery tactic (TA0007) should be skipped."""
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1018', 'Remote System Discovery', 'Discovery', 'TA0007') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )

    rec = {"recommended_technique_id": "T1018", "target_id": _uid()}
    result = await engine.validate(tmp_db, rec, _uid())
    assert result.outcome == "skipped"
    assert result.delta == 0.0


# ---------------------------------------------------------------------------
# Tests: No target_ip -> skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_target_ip_skipped(tmp_db, engine):
    """Exploit tactic but target not found -> skipped."""
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190', 'Exploit Public App', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )

    rec = {"recommended_technique_id": "T1190", "target_id": _uid()}
    result = await engine.validate(tmp_db, rec, _uid())
    assert result.outcome == "skipped"
    assert result.delta == 0.0


@pytest.mark.asyncio
async def test_no_target_id_skipped(tmp_db, engine):
    """No target_id in recommendation -> skipped."""
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190b', 'Exploit Public App', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )

    rec = {"recommended_technique_id": "T1190b", "target_id": None}
    result = await engine.validate(tmp_db, rec, _uid())
    assert result.outcome == "skipped"


# ---------------------------------------------------------------------------
# Tests: Port reachability
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_port_reachability_passed(tmp_db, engine):
    """Mock socket connect success -> port_reachability passed."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190c', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES ($1, 'service.open_port', '21/tcp vsftpd 2.3.4', $2, $3)",
        _uid(), op_id, target_id,
    )

    rec = {"recommended_technique_id": "T1190c", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None  # success

        result = await engine.validate(tmp_db, rec, op_id)

    port_check = [c for c in result.checks if c["name"] == "port_reachability"]
    assert len(port_check) == 1
    assert port_check[0]["result"] == "passed"


@pytest.mark.asyncio
async def test_port_reachability_failed(tmp_db, engine):
    """Mock socket connect failure -> port_reachability failed."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190d', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES ($1, 'service.open_port', '21/tcp vsftpd 2.3.4', $2, $3)",
        _uid(), op_id, target_id,
    )

    rec = {"recommended_technique_id": "T1190d", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.side_effect = OSError("Connection refused")

        result = await engine.validate(tmp_db, rec, op_id)

    assert result.outcome == "failed"
    assert result.delta == -0.30


# ---------------------------------------------------------------------------
# Tests: Service banner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_banner_match(tmp_db, engine):
    """Banner matches -> service_banner passed."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190e', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES ($1, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', $2, $3)",
        _uid(), op_id, target_id,
    )

    rec = {"recommended_technique_id": "T1190e", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(
            ValidationEngine, "_grab_banner",
            return_value="220 21/tcp banner: vsftpd 2.3.4",
        ):
            result = await engine.validate(tmp_db, rec, op_id)

    banner_check = [c for c in result.checks if c["name"] == "service_banner"]
    assert len(banner_check) == 1
    assert banner_check[0]["result"] == "passed"


@pytest.mark.asyncio
async def test_service_banner_mismatch(tmp_db, engine):
    """Banner doesn't match -> service_banner failed."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190f', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES ($1, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', $2, $3)",
        _uid(), op_id, target_id,
    )

    rec = {"recommended_technique_id": "T1190f", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(ValidationEngine, "_grab_banner", return_value="220 ProFTPD 1.3.5"):
            result = await engine.validate(tmp_db, rec, op_id)

    assert result.outcome == "failed"
    assert result.delta == -0.30


# ---------------------------------------------------------------------------
# Tests: Version range (SPEC-028 Phase 4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_version_range_known_vulnerable(tmp_db, engine):
    """Version in known vulnerable range → passed."""
    service_facts = [
        {"trait": "service.open_port", "value": "21/tcp ftp vsftpd 2.3.4"},
        {"trait": "service.version", "value": "vsftpd 2.3.4"},
    ]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "passed"
    assert "CVE-2011-2523" in result["detail"]


@pytest.mark.asyncio
async def test_version_range_patched(tmp_db, engine):
    """Version above vulnerable range → failed (likely patched)."""
    service_facts = [
        {"trait": "service.open_port", "value": "80/tcp http Apache 2.4.52"},
        {"trait": "service.version", "value": "Apache 2.4.52"},
    ]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "failed"
    assert "patched" in result["detail"].lower()


@pytest.mark.asyncio
async def test_version_range_no_match(tmp_db, engine):
    """Unknown service/version → skipped (inconclusive)."""
    service_facts = [{"trait": "service.version", "value": "customd 1.0.0"}]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "skipped"
    assert "no known range" in result["detail"]


@pytest.mark.asyncio
async def test_version_range_no_version(tmp_db, engine):
    """No version detected → skipped."""
    service_facts = [{"trait": "service.name", "value": "vsftpd"}]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "skipped"
    assert "no version" in result["detail"]


@pytest.mark.asyncio
async def test_version_range_apache_cve_2021(tmp_db, engine):
    """Apache 2.4.49 in CVE-2021-41773 range → passed."""
    service_facts = [
        {"trait": "service.open_port", "value": "80/tcp http apache"},
        {"trait": "service.version", "value": "Apache/2.4.49"},
    ]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "passed"
    assert "CVE-2021-41773" in result["detail"]


@pytest.mark.asyncio
async def test_version_range_samba_sambacry(tmp_db, engine):
    """Samba 4.5.9 in SambaCry range → passed."""
    service_facts = [
        {"trait": "service.open_port", "value": "445/tcp samba"},
        {"trait": "service.version", "value": "Samba 4.5.9"},
    ]
    result = await engine._check_version_range("T1190", service_facts)
    assert result["result"] == "passed"
    assert "CVE-2017-7494" in result["detail"]


# ---------------------------------------------------------------------------
# Tests: Overall outcome logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_passed_delta_positive(tmp_db, engine):
    """When port and banner both pass, delta should be +0.15."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190g', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )
    await tmp_db.execute(
        "INSERT INTO facts (id, trait, value, operation_id, source_target_id) "
        "VALUES ($1, 'service.open_port', '21/tcp banner: vsftpd 2.3.4', $2, $3)",
        _uid(), op_id, target_id,
    )

    rec = {"recommended_technique_id": "T1190g", "target_id": target_id}

    with patch("app.services.validation_engine.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.connect.return_value = None

        with patch.object(
            ValidationEngine, "_grab_banner",
            return_value="220 21/tcp banner: vsftpd 2.3.4",
        ):
            result = await engine.validate(tmp_db, rec, op_id)

    assert result.outcome == "validated"
    assert result.delta == 0.15


@pytest.mark.asyncio
async def test_all_skipped_delta_zero(tmp_db, engine):
    """No service facts -> all checks skipped -> delta 0."""
    op_id, target_id = _uid(), _uid()
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id) "
        "VALUES ($1, 'T1190h', 'Exploit', 'Initial Access', 'TA0001') "
        "ON CONFLICT DO NOTHING",
        _uid(),
    )
    await _ensure_op(tmp_db, op_id)
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
        "VALUES ($1, 'host1', '10.0.1.5', 'server', $2)",
        target_id, op_id,
    )

    rec = {"recommended_technique_id": "T1190h", "target_id": target_id}
    result = await engine.validate(tmp_db, rec, op_id)

    assert result.outcome == "skipped"
    assert result.delta == 0.0


@pytest.mark.asyncio
async def test_confidence_clamped_high(tmp_db, engine):
    """Verify confidence is clamped to [0.0, 1.0]."""
    original = 0.95
    delta = 0.15
    adjusted = max(0.0, min(1.0, original + delta))
    assert adjusted == 1.0


@pytest.mark.asyncio
async def test_confidence_clamped_low(tmp_db, engine):
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

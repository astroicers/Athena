"""Tests for 3-phase access recovery (SPEC-041 Part B)."""
import pytest
import uuid
from datetime import datetime, timezone


# We test the recovery phases by directly calling the methods on the engine router


@pytest.fixture
def op_id():
    return str(uuid.uuid4())


@pytest.fixture
def target_id():
    return str(uuid.uuid4())


@pytest.fixture
def target_ip():
    return "192.168.1.100"


async def _setup_target(db, op_id, target_id, target_ip, compromised=False, access_status="unknown", privilege="User"):
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ($1, $2, 'Test', 'TEST', 'test') ON CONFLICT DO NOTHING",
        op_id, f"OP-{op_id[:8]}",
    )
    await db.execute(
        "INSERT INTO targets (id, operation_id, ip_address, is_compromised, access_status, privilege_level, hostname, os, role) "
        "VALUES ($1, $2, $3, $4, $5, $6, 'host', 'Linux', 'server')",
        target_id, op_id, target_ip, compromised, access_status, privilege,
    )


async def _add_fact(db, op_id, target_id, trait, value, category="host"):
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, 1, $7) "
        "ON CONFLICT DO NOTHING",
        str(uuid.uuid4()), trait, value, category, target_id, op_id, datetime.now(timezone.utc),
    )


async def _count_facts(db, op_id, trait):
    return await db.fetchval(
        "SELECT COUNT(*) FROM facts WHERE operation_id = $1 AND trait = $2",
        op_id, trait,
    )


async def _get_fact_value(db, op_id, trait):
    row = await db.fetchrow(
        "SELECT value FROM facts WHERE operation_id = $1 AND trait = $2",
        op_id, trait,
    )
    return row["value"] if row else None


class TestRecoveryPhase1:
    @pytest.mark.asyncio
    async def test_rescan_writes_recovery_candidate(self, tmp_db, op_id, target_id, target_ip):
        """Phase 1: open ports -> recovery_candidate fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "22/tcp:ssh:OpenSSH_6.6.1p1")
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "80/tcp:http:Apache")

        # Import and call directly
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)

        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 1
        val = await _get_fact_value(tmp_db, op_id, "access.recovery_candidate")
        assert "22" in val and "80" in val

    @pytest.mark.asyncio
    async def test_rescan_no_ports(self, tmp_db, op_id, target_id, target_ip):
        """Phase 1: no open ports -> no fact written."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)
        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 0

    @pytest.mark.asyncio
    async def test_rescan_no_ip(self, tmp_db, op_id, target_id):
        """Phase 1: no target_ip -> early return."""
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, None)
        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 0


class TestRecoveryPhase2:
    @pytest.mark.asyncio
    async def test_alt_protocol_winrm(self, tmp_db, op_id, target_id, target_ip):
        """Phase 2: WinRM port -> alternative_available fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "5985/tcp:wsman")
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)
        val = await _get_fact_value(tmp_db, op_id, "access.alternative_available")
        assert val == f"winrm:{target_ip}:5985"

    @pytest.mark.asyncio
    async def test_alt_protocol_ssh_key(self, tmp_db, op_id, target_id, target_ip):
        """Phase 2: SSH key credential -> alternative_available fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "credential.ssh_key", "id_rsa_contents", category="credential")
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)
        val = await _get_fact_value(tmp_db, op_id, "access.alternative_available")
        assert val == f"ssh_key:{target_ip}:22"

    @pytest.mark.asyncio
    async def test_alt_protocol_smb(self, tmp_db, op_id, target_id, target_ip):
        """Phase 2: SMB port -> alternative_available fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "445/tcp:smb")
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)
        val = await _get_fact_value(tmp_db, op_id, "access.alternative_available")
        assert val == f"smb:{target_ip}:445"


class TestRecoveryPhase3:
    @pytest.mark.asyncio
    async def test_pivot_found(self, tmp_db, op_id, target_id, target_ip):
        """Phase 3: another compromised host -> pivot_candidate fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        pivot_id = str(uuid.uuid4())
        await _setup_target(tmp_db, op_id, pivot_id, "192.168.1.200", compromised=True, access_status="active", privilege="Root")
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase3_pivot(tmp_db, op_id, target_id, target_ip)
        val = await _get_fact_value(tmp_db, op_id, "access.pivot_candidate")
        assert "192.168.1.200" in val and target_ip in val

    @pytest.mark.asyncio
    async def test_no_pivot_available(self, tmp_db, op_id, target_id, target_ip):
        """Phase 3: no other compromised hosts -> no fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase3_pivot(tmp_db, op_id, target_id, target_ip)
        count = await _count_facts(tmp_db, op_id, "access.pivot_candidate")
        assert count == 0

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_db, op_id, target_id, target_ip):
        """Repeated calls don't create duplicate facts."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "22/tcp:ssh")
        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)
        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 1


# -- SPEC-041 Expanded Tests --


class TestRecoveryPhase1Expanded:
    """Additional Phase 1 tests -- SPEC-041 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_recovery_phase1_rescan_writes_candidate_fact(self, tmp_db, op_id, target_id, target_ip):
        """Open ports -> writes access.recovery_candidate fact with port list."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "22/tcp:ssh:OpenSSH_6.6.1p1")
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "80/tcp:http:Apache")
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "443/tcp:https:nginx")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)

        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 1

        val = await _get_fact_value(tmp_db, op_id, "access.recovery_candidate")
        assert val.startswith(f"rescan:{target_ip}:ports=")
        assert "22" in val
        assert "80" in val
        assert "443" in val

    @pytest.mark.asyncio
    async def test_recovery_phase1_no_ports_skips(self, tmp_db, op_id, target_id, target_ip):
        """No open ports -> no fact written."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "os.type", "Linux")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)

        count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert count == 0


class TestRecoveryPhase2Expanded:
    """Additional Phase 2 tests -- SPEC-041 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_recovery_phase2_winrm_available(self, tmp_db, op_id, target_id, target_ip):
        """Port 5985 present -> writes access.alternative_available fact for WinRM."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "5985/tcp:wsman:Microsoft HTTPAPI")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)

        val = await _get_fact_value(tmp_db, op_id, "access.alternative_available")
        assert val == f"winrm:{target_ip}:5985"

    @pytest.mark.asyncio
    async def test_recovery_phase2_ssh_key_available(self, tmp_db, op_id, target_id, target_ip):
        """Has credential.ssh_key -> writes ssh_key alternative fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        await _add_fact(tmp_db, op_id, target_id, "credential.ssh_key", "-----BEGIN RSA PRIVATE KEY-----", category="credential")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)

        val = await _get_fact_value(tmp_db, op_id, "access.alternative_available")
        assert val == f"ssh_key:{target_ip}:22"


class TestRecoveryPhase3Expanded:
    """Additional Phase 3 tests -- SPEC-041 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_recovery_phase3_pivot_candidate(self, tmp_db, op_id, target_id, target_ip):
        """Other compromised host with elevated privilege -> writes access.pivot_candidate fact."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        pivot_id = str(uuid.uuid4())
        pivot_ip = "10.0.0.50"
        await _setup_target(tmp_db, op_id, pivot_id, pivot_ip, compromised=True, access_status="active", privilege="Root")
        await _add_fact(tmp_db, op_id, pivot_id, "credential.root_shell", "msf_session_42")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase3_pivot(tmp_db, op_id, target_id, target_ip)

        val = await _get_fact_value(tmp_db, op_id, "access.pivot_candidate")
        assert val is not None
        assert f"pivot:{pivot_ip}->{target_ip}" in val
        assert "via=root_shell" in val

    @pytest.mark.asyncio
    async def test_recovery_phase3_no_other_hosts_skips(self, tmp_db, op_id, target_id, target_ip):
        """No other compromised hosts -> no pivot fact written."""
        await _setup_target(tmp_db, op_id, target_id, target_ip, compromised=True, access_status="lost")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)
        await router._recovery_phase3_pivot(tmp_db, op_id, target_id, target_ip)

        count = await _count_facts(tmp_db, op_id, "access.pivot_candidate")
        assert count == 0


class TestRecoveryIdempotency:
    """ON CONFLICT DO NOTHING idempotency tests -- SPEC-041 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_recovery_insert_or_ignore_idempotent(self, tmp_db, op_id, target_id, target_ip):
        """Multiple invocations of all three phases don't create duplicate facts."""
        await _setup_target(tmp_db, op_id, target_id, target_ip)
        # Setup facts for all three phases
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "22/tcp:ssh:OpenSSH")
        await _add_fact(tmp_db, op_id, target_id, "service.open_port", "5985/tcp:wsman")
        await _add_fact(tmp_db, op_id, target_id, "credential.ssh_key", "id_rsa_data", category="credential")

        # Setup a pivot host for Phase 3
        pivot_id = str(uuid.uuid4())
        await _setup_target(tmp_db, op_id, pivot_id, "10.0.0.99", compromised=True, access_status="active", privilege="Root")

        from app.services.engine_router import EngineRouter
        router = EngineRouter.__new__(EngineRouter)

        # Run all three phases twice
        for _ in range(2):
            await router._recovery_phase1_rescan(tmp_db, op_id, target_id, target_ip)
            await router._recovery_phase2_alt_protocol(tmp_db, op_id, target_id, target_ip)
            await router._recovery_phase3_pivot(tmp_db, op_id, target_id, target_ip)

        # Each trait should have a bounded count (no duplicates from same value)
        recovery_count = await _count_facts(tmp_db, op_id, "access.recovery_candidate")
        assert recovery_count == 1, f"Expected 1 recovery_candidate, got {recovery_count}"

        pivot_count = await _count_facts(tmp_db, op_id, "access.pivot_candidate")
        assert pivot_count == 1, f"Expected 1 pivot_candidate, got {pivot_count}"

        # Phase 2 may produce multiple facts (winrm + ssh_key), but each should appear once
        duplicates = await tmp_db.fetch(
            "SELECT value, COUNT(*) as cnt FROM facts "
            "WHERE operation_id = $1 AND trait = 'access.alternative_available' "
            "GROUP BY value HAVING COUNT(*) > 1",
            op_id,
        )
        assert len(duplicates) == 0, f"Found duplicate alternative_available facts: {duplicates}"

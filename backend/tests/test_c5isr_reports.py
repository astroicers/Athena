# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for SPEC-038: C5ISR Domain Assessment Reports."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.c5isr_mapper import (
    C5ISRMapper,
    DomainMetric,
    DomainReport,
    RiskSeverity,
    RiskVector,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _mock_ws(*, connection_count: int = 0, broadcast_total: int = 0,
             broadcast_success: int = 0):
    """Create a mock WebSocketManager with configurable counters."""
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    ws.active_connection_count = MagicMock(return_value=connection_count)
    ws._broadcast_total = broadcast_total
    ws._broadcast_success = broadcast_success
    return ws


OP_ID = "test-op-1"


async def _seed_operation(db, *, ooda_count=0, max_iter=20):
    """Insert a minimal operation row."""
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, "
        "status, current_ooda_phase, ooda_iteration_count, max_iterations) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        OP_ID, "OP-001", "Test", "PHANTOM", "intent", "active", "observe",
        ooda_count, max_iter,
    )


async def _insert_recommendation(db, *, accepted=None, confidence=0.8,
                                 created_at=None):
    rid = str(uuid.uuid4())
    ts = created_at or datetime.now(timezone.utc)
    # Convert integer 0/1 to bool for PG BOOLEAN column
    accepted_bool = bool(accepted) if accepted is not None else None
    await db.execute(
        "INSERT INTO recommendations (id, operation_id, situation_assessment, "
        "recommended_technique_id, confidence, options, reasoning_text, "
        "accepted, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        rid, OP_ID, "assess", "T1003.001", confidence, "[]", "reason",
        accepted_bool, ts,
    )


async def _insert_directive(db, *, consumed=False):
    did = str(uuid.uuid4())
    consumed_at = datetime.now(timezone.utc) if consumed else None
    await db.execute(
        "INSERT INTO ooda_directives (id, operation_id, directive, consumed_at) "
        "VALUES ($1, $2, $3, $4)",
        did, OP_ID, "test directive", consumed_at,
    )


async def _insert_agent(db, *, status="alive", last_beacon=None):
    aid = str(uuid.uuid4())
    paw = f"paw-{aid[:8]}"
    await db.execute(
        "INSERT INTO agents (id, paw, status, last_beacon, operation_id) "
        "VALUES ($1, $2, $3, $4, $5)",
        aid, paw, status, last_beacon, OP_ID,
    )


async def _insert_target(db, *, compromised=False, privilege="User",
                         access_status="unknown"):
    tid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, role, is_compromised, "
        "privilege_level, access_status, operation_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        tid, f"host-{tid[:6]}", f"10.0.0.{hash(tid) % 255}", "target",
        compromised, privilege, access_status, OP_ID,
    )
    return tid


async def _insert_technique(db, *, mitre_id="T1003.001", tactic="Credential Access",
                            kill_chain="exploit"):
    """Insert or ignore a technique row."""
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, "
        "kill_chain_stage) VALUES ($1, $2, $3, $4, $5, $6) "
        "ON CONFLICT DO NOTHING",
        f"tech-{mitre_id}", mitre_id, f"Tech {mitre_id}", tactic,
        "TA0006", kill_chain,
    )


async def _insert_execution(db, *, technique_id="T1003.001", status="success",
                            created_at=None):
    eid = str(uuid.uuid4())
    ts = created_at or datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO technique_executions (id, technique_id, operation_id, "
        "status, created_at) VALUES ($1, $2, $3, $4, $5)",
        eid, technique_id, OP_ID, status, ts,
    )


async def _insert_fact(db, *, category="host", trait="os.version"):
    fid = str(uuid.uuid4())
    # Use unique value per fact to avoid idx_facts_dedup constraint
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, operation_id) "
        "VALUES ($1, $2, $3, $4, $5)",
        fid, trait, f"value-{fid[:8]}", category, OP_ID,
    )


async def _insert_attack_graph_node(db, *, status="unreachable"):
    nid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO attack_graph_nodes (id, operation_id, technique_id, "
        "tactic_id, status) VALUES ($1, $2, $3, $4, $5)",
        nid, OP_ID, "T1003.001", "TA0006", status,
    )


async def _insert_tool(db, *, enabled=True):
    tid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO tool_registry (id, tool_id, name, kind, enabled) "
        "VALUES ($1, $2, $3, $4, $5)",
        tid, f"tool-{tid[:6]}", f"Tool {tid[:6]}", "tool", enabled,
    )


# ===========================================================================
#  DomainReport serialization
# ===========================================================================

class TestDomainReportSerialization:
    def test_to_json_from_json_roundtrip(self):
        report = DomainReport(
            executive_summary="test summary",
            health_pct=72.5,
            status="nominal",
            metrics=[
                DomainMetric("m1", 80.0, 0.5, 4, 5),
                DomainMetric("m2", 60.0, 0.5, None, None),
            ],
            risk_vectors=[
                RiskVector(RiskSeverity.WARN, "warning msg"),
            ],
            recommended_actions=["action 1"],
            cross_domain_impacts=["impact 1"],
            tactical_assessment="tactical text",
            asset_roster=[{"type": "agent", "paw": "abc"}],
        )
        json_str = report.to_json()
        restored = DomainReport.from_json(json_str)
        assert restored.executive_summary == report.executive_summary
        assert restored.health_pct == report.health_pct
        assert restored.status == report.status
        assert len(restored.metrics) == 2
        assert restored.metrics[0].name == "m1"
        assert restored.metrics[0].numerator == 4
        assert len(restored.risk_vectors) == 1
        assert restored.risk_vectors[0].severity == RiskSeverity.WARN
        assert restored.recommended_actions == ["action 1"]
        assert restored.cross_domain_impacts == ["impact 1"]
        assert restored.tactical_assessment == "tactical text"
        assert restored.asset_roster == [{"type": "agent", "paw": "abc"}]

    def test_from_json_corrupted_json(self):
        report = DomainReport.from_json("not valid json{{{")
        assert report.health_pct == 0.0
        assert report.status == "critical"
        assert report.executive_summary == ""

    def test_from_json_none_input(self):
        report = DomainReport.from_json(None)  # type: ignore
        assert report.health_pct == 0.0
        assert report.status == "critical"


# ===========================================================================
#  _build_command_report
# ===========================================================================

class TestBuildCommandReport:
    @pytest.mark.asyncio
    async def test_normal_data(self, tmp_db):
        await _seed_operation(tmp_db, ooda_count=10, max_iter=20)
        await _insert_recommendation(tmp_db, accepted=1)
        await _insert_recommendation(tmp_db, accepted=1)
        await _insert_recommendation(tmp_db, accepted=0)
        await _insert_directive(tmp_db, consumed=True)
        await _insert_directive(tmp_db, consumed=False)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_command_report(tmp_db, OP_ID)

        assert report.executive_summary
        assert len(report.metrics) == 3
        assert report.metrics[0].name == "decision_throughput"
        assert report.metrics[0].value == 50.0  # 10/20 * 100
        assert report.metrics[1].name == "acceptance_rate"
        # 2/3 accepted
        assert abs(report.metrics[1].value - 66.7) < 1.0
        assert report.metrics[2].name == "directive_consumption"
        assert report.metrics[2].value == 50.0  # 1/2

        # health = 50*0.4 + 66.7*0.35 + 50*0.25
        expected_health = round(50.0 * 0.4 + report.metrics[1].value * 0.35 + 50.0 * 0.25, 1)
        assert abs(report.health_pct - expected_health) <= 0.1

    @pytest.mark.asyncio
    async def test_empty_no_inflate(self, tmp_db):
        """Command health must NOT auto-inflate: no recs -> health_pct < 50."""
        await _seed_operation(tmp_db, ooda_count=0, max_iter=20)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_command_report(tmp_db, OP_ID)

        # dt=0, ar=50 (baseline), dc=100 (no directives)
        # health = 0*0.4 + 50*0.35 + 100*0.25 = 0 + 17.5 + 25 = 42.5
        assert report.health_pct < 50
        assert report.health_pct == 42.5

    @pytest.mark.asyncio
    async def test_stall_penalty(self, tmp_db):
        """Stall penalty: old recommendations reduce decision_throughput."""
        await _seed_operation(tmp_db, ooda_count=5, max_iter=20)
        # Insert old recommendations (well beyond stall threshold)
        old_time = (datetime.now(timezone.utc) - timedelta(hours=1))
        await _insert_recommendation(tmp_db, accepted=1, created_at=old_time)
        await _insert_recommendation(tmp_db, accepted=1, created_at=old_time)
        await _insert_recommendation(tmp_db, accepted=1, created_at=old_time)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_command_report(tmp_db, OP_ID)

        # dt would be 5/20*100=25, minus 20 stall = 5
        assert report.metrics[0].value == 5.0


# ===========================================================================
#  _build_control_report
# ===========================================================================

class TestBuildControlReport:
    @pytest.mark.asyncio
    async def test_normal_agents(self, tmp_db):
        await _seed_operation(tmp_db)
        beacon_time = datetime.now(timezone.utc)
        await _insert_agent(tmp_db, status="alive", last_beacon=beacon_time)
        await _insert_agent(tmp_db, status="alive", last_beacon=beacon_time)
        await _insert_agent(tmp_db, status="dead")
        await _insert_target(tmp_db, access_status="active")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_control_report(tmp_db, OP_ID)

        assert report.metrics[0].name == "agent_liveness"
        assert abs(report.metrics[0].value - 66.7) < 1.0  # 2/3
        assert report.metrics[1].name == "access_stability"
        assert report.metrics[1].value == 100.0  # 1/1 active
        assert report.metrics[2].name == "beacon_freshness"

    @pytest.mark.asyncio
    async def test_no_agents(self, tmp_db):
        await _seed_operation(tmp_db)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_control_report(tmp_db, OP_ID)

        assert report.metrics[0].value == 0.0  # no agents
        assert report.health_pct == 0.0
        assert any(rv.severity == RiskSeverity.CRIT for rv in report.risk_vectors)

    @pytest.mark.asyncio
    async def test_stale_beacon_penalty(self, tmp_db):
        await _seed_operation(tmp_db)
        old_beacon = (datetime.now(timezone.utc) - timedelta(minutes=10))
        await _insert_agent(tmp_db, status="alive", last_beacon=old_beacon)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_control_report(tmp_db, OP_ID)

        # Beacon freshness should be penalized
        assert report.metrics[2].value < 50.0


# ===========================================================================
#  _build_comms_report
# ===========================================================================

class TestBuildCommsReport:
    @pytest.mark.asyncio
    async def test_normal(self, tmp_db):
        await _seed_operation(tmp_db)
        await _insert_tool(tmp_db, enabled=True)
        await _insert_tool(tmp_db, enabled=True)
        await _insert_tool(tmp_db, enabled=False)

        ws = _mock_ws(connection_count=2, broadcast_total=10, broadcast_success=9)
        mapper = C5ISRMapper(ws)
        report = await mapper._build_comms_report(tmp_db, OP_ID)

        assert report.metrics[0].name == "ws_connections"
        assert report.metrics[0].value == 100.0  # 2*50 = 100
        assert report.metrics[1].name == "mcp_availability"
        assert abs(report.metrics[1].value - 66.7) < 1.0  # 2/3
        assert report.metrics[2].name == "broadcast_success"
        assert report.metrics[2].value == 90.0

    @pytest.mark.asyncio
    async def test_no_ws_but_mcp_available(self, tmp_db):
        """Comms not hardcoded 60%: ws=0 but MCP available -> health_pct > 0."""
        await _seed_operation(tmp_db)
        await _insert_tool(tmp_db, enabled=True)
        await _insert_tool(tmp_db, enabled=True)

        ws = _mock_ws(connection_count=0)
        mapper = C5ISRMapper(ws)
        report = await mapper._build_comms_report(tmp_db, OP_ID)

        assert report.metrics[0].value == 0.0  # ws_connections
        assert report.metrics[1].value == 100.0  # mcp all enabled
        assert report.health_pct > 0  # not zero thanks to mcp + broadcast

    @pytest.mark.asyncio
    async def test_no_broadcasts_yet(self, tmp_db):
        """Broadcast success = 100% when no broadcasts attempted."""
        await _seed_operation(tmp_db)

        ws = _mock_ws(connection_count=0, broadcast_total=0, broadcast_success=0)
        mapper = C5ISRMapper(ws)
        report = await mapper._build_comms_report(tmp_db, OP_ID)

        assert report.metrics[2].value == 100.0


# ===========================================================================
#  _build_computers_report
# ===========================================================================

class TestBuildComputersReport:
    @pytest.mark.asyncio
    async def test_normal(self, tmp_db):
        await _seed_operation(tmp_db)
        await _insert_target(tmp_db, compromised=True, privilege="Root")
        await _insert_target(tmp_db, compromised=True, privilege="User")
        await _insert_target(tmp_db, compromised=False)
        await _insert_technique(tmp_db, kill_chain="exploit")
        await _insert_execution(tmp_db, status="success")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_computers_report(tmp_db, OP_ID)

        assert report.metrics[0].name == "compromise_rate"
        assert abs(report.metrics[0].value - 66.7) < 1.0  # 2/3
        assert report.metrics[1].name == "privilege_depth"
        assert report.metrics[1].value == 50.0  # 1/2 root
        assert report.metrics[2].name == "killchain_advancement"
        assert report.metrics[2].value == 50  # exploit stage

    @pytest.mark.asyncio
    async def test_no_targets(self, tmp_db):
        await _seed_operation(tmp_db)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_computers_report(tmp_db, OP_ID)

        assert report.metrics[0].value == 0.0
        assert report.health_pct == 0.0

    @pytest.mark.asyncio
    async def test_all_compromised_root(self, tmp_db):
        await _seed_operation(tmp_db)
        await _insert_target(tmp_db, compromised=True, privilege="Root")
        await _insert_target(tmp_db, compromised=True, privilege="Root")
        await _insert_technique(tmp_db, kill_chain="action")
        await _insert_execution(tmp_db, status="success")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_computers_report(tmp_db, OP_ID)

        assert report.metrics[0].value == 100.0
        assert report.metrics[1].value == 100.0
        assert report.metrics[2].value == 100  # action stage
        assert any("fully controlled" in rv.message for rv in report.risk_vectors)


# ===========================================================================
#  _build_cyber_report
# ===========================================================================

class TestBuildCyberReport:
    @pytest.mark.asyncio
    async def test_normal(self, tmp_db):
        await _seed_operation(tmp_db)
        await _insert_technique(tmp_db, mitre_id="T1595", tactic="Reconnaissance")
        await _insert_technique(tmp_db, mitre_id="T1003.001", tactic="Credential Access")
        await _insert_execution(tmp_db, technique_id="T1595", status="success")
        await _insert_execution(tmp_db, technique_id="T1595", status="failed")
        await _insert_execution(tmp_db, technique_id="T1003.001", status="success")
        await _insert_execution(tmp_db, technique_id="T1003.001", status="success")
        await _insert_execution(tmp_db, technique_id="T1003.001", status="failed")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_cyber_report(tmp_db, OP_ID)

        assert report.metrics[0].name == "recon_success"
        assert report.metrics[0].value == 50.0  # 1/2
        assert report.metrics[1].name == "exploit_success"
        assert abs(report.metrics[1].value - 66.7) < 1.0  # 2/3
        assert report.metrics[2].name == "recent_trend"

    @pytest.mark.asyncio
    async def test_no_executions(self, tmp_db):
        await _seed_operation(tmp_db)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_cyber_report(tmp_db, OP_ID)

        assert report.health_pct == 0.0
        assert all(m.value == 0.0 for m in report.metrics)

    @pytest.mark.asyncio
    async def test_declining_trend(self, tmp_db):
        """Declining trend: recent 5 all fail, overall has some success."""
        await _seed_operation(tmp_db)
        await _insert_technique(tmp_db, mitre_id="T1003.001")
        # 10 old successes
        old_time = (datetime.now(timezone.utc) - timedelta(hours=1))
        for _ in range(10):
            await _insert_execution(tmp_db, status="success", created_at=old_time)
        # 5 recent failures
        now = datetime.now(timezone.utc)
        for _ in range(5):
            await _insert_execution(tmp_db, status="failed", created_at=now)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_cyber_report(tmp_db, OP_ID)

        # recent_rate = 0/5 = 0.0, overall_rate = 10/15 = 0.667
        # 0.0 < 0.667 - 0.20 = 0.467 -> declining trend -> recent_trend = 0
        assert report.metrics[2].value == 0.0
        assert any("Declining" in rv.message for rv in report.risk_vectors)


# ===========================================================================
#  _build_isr_report
# ===========================================================================

class TestBuildISRReport:
    @pytest.mark.asyncio
    async def test_normal(self, tmp_db):
        await _seed_operation(tmp_db)
        await _insert_recommendation(tmp_db, confidence=0.8)
        await _insert_recommendation(tmp_db, confidence=0.9)
        await _insert_fact(tmp_db, category="host")
        await _insert_fact(tmp_db, category="credential")
        await _insert_fact(tmp_db, category="network")
        await _insert_attack_graph_node(tmp_db, status="reachable")
        await _insert_attack_graph_node(tmp_db, status="completed")
        await _insert_attack_graph_node(tmp_db, status="unreachable")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_isr_report(tmp_db, OP_ID)

        assert report.metrics[0].name == "confidence_trend"
        assert report.metrics[0].value == 85.0  # avg(0.8, 0.9) * 100
        assert report.metrics[1].name == "fact_coverage"
        assert abs(report.metrics[1].value - 42.9) < 1.0  # 3/7 * 100
        assert report.metrics[2].name == "graph_coverage"
        assert abs(report.metrics[2].value - 66.7) < 1.0  # 2/3

    @pytest.mark.asyncio
    async def test_empty(self, tmp_db):
        await _seed_operation(tmp_db)

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_isr_report(tmp_db, OP_ID)

        assert report.health_pct == 0.0

    @pytest.mark.asyncio
    async def test_fact_coverage_distinct(self, tmp_db):
        """fact_coverage counts distinct categories, not total facts."""
        await _seed_operation(tmp_db)
        # Multiple facts in same category
        await _insert_fact(tmp_db, category="host", trait="os.version")
        await _insert_fact(tmp_db, category="host", trait="hostname")
        await _insert_fact(tmp_db, category="host", trait="arch")
        # One fact in another
        await _insert_fact(tmp_db, category="credential", trait="password")

        mapper = C5ISRMapper(_mock_ws())
        report = await mapper._build_isr_report(tmp_db, OP_ID)

        # Only 2 distinct categories despite 4 facts
        assert report.metrics[1].numerator == 2
        assert abs(report.metrics[1].value - 2 / 7 * 100) < 0.2


# ===========================================================================
#  Full update() integration
# ===========================================================================

class TestC5ISRMapperUpdate:
    @pytest.mark.asyncio
    async def test_full_update_produces_six_reports(self, tmp_db):
        """Full OODA iteration produces all 6 structured reports."""
        await _seed_operation(tmp_db, ooda_count=5, max_iter=20)
        await _insert_recommendation(tmp_db, accepted=1, confidence=0.75)
        beacon = datetime.now(timezone.utc)
        await _insert_agent(tmp_db, status="alive", last_beacon=beacon)
        await _insert_target(tmp_db, compromised=True, privilege="Root",
                            access_status="active")
        await _insert_technique(tmp_db, mitre_id="T1003.001")
        await _insert_execution(tmp_db, status="success")
        await _insert_fact(tmp_db, category="host")
        await _insert_fact(tmp_db, category="credential")
        await _insert_tool(tmp_db, enabled=True)
        await _insert_attack_graph_node(tmp_db, status="reachable")

        ws = _mock_ws(connection_count=1)
        mapper = C5ISRMapper(ws)
        results = await mapper.update(tmp_db, OP_ID)

        assert len(results) == 6
        domains = {r["domain"] for r in results}
        assert domains == {"command", "control", "comms", "computers", "cyber", "isr"}

        # Every result has report field
        for r in results:
            assert "report" in r
            report = r["report"]
            assert report["executive_summary"]
            assert len(report["metrics"]) >= 2
            assert isinstance(report["health_pct"], float)
            # health_pct matches weighted sum
            expected_h = round(
                sum(m["value"] * m["weight"] for m in report["metrics"]), 1
            )
            assert abs(report["health_pct"] - expected_h) <= 0.1

        # Verify broadcast was called
        ws.broadcast.assert_awaited_once()
        call_args = ws.broadcast.call_args
        assert call_args[0][1] == "c5isr.update"
        assert "domains" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_detail_stores_json(self, tmp_db):
        """DB detail column stores JSON-serialized DomainReport."""
        await _seed_operation(tmp_db)

        mapper = C5ISRMapper(_mock_ws())
        await mapper.update(tmp_db, OP_ID)

        rows = await tmp_db.fetch(
            "SELECT detail FROM c5isr_statuses WHERE operation_id = $1",
            OP_ID,
        )
        for row in rows:
            # Should be valid JSON
            data = json.loads(row["detail"])
            assert "executive_summary" in data
            assert "metrics" in data
            # Should be deserializable
            report = DomainReport.from_json(row["detail"])
            assert isinstance(report.health_pct, float)

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Tests for SPEC-047: Constraint Engine."""

import json
import uuid
from datetime import datetime, timezone

import pytest


async def _setup_operation(db, op_id):
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, mission_profile) "
        "VALUES ($1, $2, 'Test', 'TEST', 'test', 'SP') ON CONFLICT DO NOTHING",
        op_id, f"OP-{op_id[:8]}",
    )


async def _set_c5isr(db, op_id, domain, health_pct, status="operational"):
    cid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO c5isr_statuses (id, operation_id, domain, health_pct, status) "
        "VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT DO NOTHING",
        cid, op_id, domain, health_pct, status,
    )


async def _add_override(db, op_id, domain):
    eid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO event_store (id, operation_id, event_type, payload, actor) "
        "VALUES ($1, $2, 'constraint.override', $3, 'commander')",
        eid, op_id, json.dumps({"domain": domain}),
    )


class TestConstraintEngineEvaluate:
    @pytest.mark.asyncio
    async def test_no_c5isr_data_returns_clean_constraints(self, tmp_db):
        """No C5ISR data → no warnings or hard limits."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert len(constraints.warnings) == 0
        assert len(constraints.hard_limits) == 0
        assert constraints.orient_max_options == 3  # SP default

    @pytest.mark.asyncio
    async def test_warning_threshold_triggers_warning(self, tmp_db):
        """Health below WARNING threshold → warning generated."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        # SP command warning threshold = 50
        await _set_c5isr(tmp_db, op_id, "command", 45.0)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert len(constraints.warnings) >= 1
        domains = [w.domain for w in constraints.warnings]
        assert "command" in domains
        assert constraints.orient_max_options == 2  # command warning reduces to 2

    @pytest.mark.asyncio
    async def test_critical_threshold_triggers_hard_limit(self, tmp_db):
        """Health below CRITICAL threshold → hard limit."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        # SP command critical threshold = 25
        await _set_c5isr(tmp_db, op_id, "command", 20.0)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert len(constraints.hard_limits) >= 1
        rules = [hl.rule for hl in constraints.hard_limits]
        assert "orient_single_option" in rules
        assert constraints.orient_max_options == 1

    @pytest.mark.asyncio
    async def test_control_critical_forces_recovery_mode(self, tmp_db):
        """Control domain CRITICAL → forced_mode=recovery."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        # SP control critical = 25
        await _set_c5isr(tmp_db, op_id, "control", 10.0)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert constraints.forced_mode == "recovery"
        assert constraints.is_recovery_mode is True

    @pytest.mark.asyncio
    async def test_comms_critical_limits_parallel(self, tmp_db):
        """Comms domain CRITICAL → max_parallel=1."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        await _set_c5isr(tmp_db, op_id, "comms", 10.0)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert constraints.max_parallel_override == 1

    @pytest.mark.asyncio
    async def test_cyber_critical_raises_confidence(self, tmp_db):
        """Cyber domain CRITICAL → min_confidence=0.75."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        await _set_c5isr(tmp_db, op_id, "cyber", 10.0)

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert constraints.min_confidence_override == 0.75

    @pytest.mark.asyncio
    async def test_override_skips_domain(self, tmp_db):
        """Active override → domain constraint skipped."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        await _set_c5isr(tmp_db, op_id, "command", 10.0)  # would be CRITICAL
        await _add_override(tmp_db, op_id, "command")

        constraints = await evaluate(tmp_db, op_id, "SP")
        # command should be skipped due to override
        command_warnings = [w for w in constraints.warnings if w.domain == "command"]
        command_limits = [hl for hl in constraints.hard_limits if hl.domain == "command"]
        assert len(command_warnings) == 0
        assert len(command_limits) == 0
        assert "command" in constraints.active_overrides

    @pytest.mark.asyncio
    async def test_multiple_domains_degraded(self, tmp_db):
        """Multiple domains below threshold → multiple constraints."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        await _set_c5isr(tmp_db, op_id, "command", 10.0)  # CRITICAL
        await _set_c5isr(tmp_db, op_id, "cyber", 10.0)    # CRITICAL
        await _set_c5isr(tmp_db, op_id, "isr", 40.0)      # WARNING for SP

        constraints = await evaluate(tmp_db, op_id, "SP")
        assert constraints.orient_max_options == 1  # command critical
        assert constraints.min_confidence_override == 0.75  # cyber critical
        assert any(w.domain == "isr" for w in constraints.warnings)

    @pytest.mark.asyncio
    async def test_sr_profile_stricter_thresholds(self, tmp_db):
        """SR profile has stricter thresholds (command warning=70)."""
        from app.services.constraint_engine import evaluate

        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        # SR command warning = 70, SP command warning = 50
        await _set_c5isr(tmp_db, op_id, "command", 65.0)

        # Under SP: no warning (65 > 50)
        constraints_sp = await evaluate(tmp_db, op_id, "SP")
        sp_cmd_warnings = [w for w in constraints_sp.warnings if w.domain == "command"]
        assert len(sp_cmd_warnings) == 0

        # Under SR: warning (65 < 70)
        constraints_sr = await evaluate(tmp_db, op_id, "SR")
        sr_cmd_warnings = [w for w in constraints_sr.warnings if w.domain == "command"]
        assert len(sr_cmd_warnings) >= 1


class TestConstraintOverrideAPI:
    @pytest.mark.asyncio
    async def test_override_creates_event(self, tmp_db):
        """Override writes to event_store."""
        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)
        await _add_override(tmp_db, op_id, "comms")

        row = await tmp_db.fetchrow(
            "SELECT * FROM event_store WHERE operation_id = $1 AND event_type = 'constraint.override'",
            op_id,
        )
        assert row is not None
        payload = json.loads(row["payload"])
        assert payload["domain"] == "comms"
        assert row["actor"] == "commander"


class TestC5ISRHistoryRecording:
    @pytest.mark.asyncio
    async def test_history_table_exists(self, tmp_db):
        """c5isr_status_history table should accept inserts."""
        op_id = str(uuid.uuid4())
        await _setup_operation(tmp_db, op_id)

        hist_id = str(uuid.uuid4())
        await tmp_db.execute(
            "INSERT INTO c5isr_status_history (id, operation_id, domain, health_pct, status) "
            "VALUES ($1, $2, $3, $4, $5)",
            hist_id, op_id, "command", 85.0, "operational",
        )

        row = await tmp_db.fetchrow(
            "SELECT * FROM c5isr_status_history WHERE id = $1", hist_id,
        )
        assert row is not None
        assert abs(row["health_pct"] - 85.0) < 0.01

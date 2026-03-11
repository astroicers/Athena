# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Tests for SPEC-046: Mission Profile & Technique Noise/Risk Tagging."""

import pytest
from unittest.mock import AsyncMock

from app.services.mission_profile_loader import (
    get_profile,
    get_all_profiles,
    noise_allowed,
    NOISE_RANKS,
    VALID_PROFILE_CODES,
)


# ---------------------------------------------------------------------------
# MissionProfileLoader tests (unit — no DB)
# ---------------------------------------------------------------------------


class TestMissionProfileLoader:
    def test_load_all_profiles(self):
        profiles = get_all_profiles()
        assert len(profiles) == 4
        for code in ("SR", "CO", "SP", "FA"):
            assert code in profiles

    def test_get_sr_profile(self):
        p = get_profile("SR")
        assert p["max_noise"] == "low"
        assert p["max_parallel"] == 1
        assert p["min_confidence"] == 0.8
        assert p["noise_budget_10min"] == 10

    def test_get_co_profile(self):
        p = get_profile("CO")
        assert p["max_noise"] == "medium"
        assert p["max_parallel"] == 2

    def test_get_sp_profile(self):
        p = get_profile("SP")
        assert p["max_noise"] == "high"
        assert p["max_parallel"] == 5

    def test_get_fa_profile(self):
        p = get_profile("FA")
        assert p["max_noise"] == "all"
        assert p["max_parallel"] == 8

    def test_unknown_profile_falls_back_to_sp(self):
        p = get_profile("XX")
        assert p["max_noise"] == "high"  # SP defaults

    def test_valid_profile_codes(self):
        assert VALID_PROFILE_CODES == ("SR", "CO", "SP", "FA")

    def test_c5isr_thresholds_present(self):
        for code in VALID_PROFILE_CODES:
            p = get_profile(code)
            thresholds = p["c5isr_thresholds"]
            for domain in ("command", "control", "comms", "computers", "cyber", "isr"):
                assert domain in thresholds
                assert "warning" in thresholds[domain]
                assert "critical" in thresholds[domain]


class TestNoiseAllowed:
    def test_sr_allows_low_only(self):
        assert noise_allowed("SR", "low") is True
        assert noise_allowed("SR", "medium") is False
        assert noise_allowed("SR", "high") is False

    def test_co_allows_low_and_medium(self):
        assert noise_allowed("CO", "low") is True
        assert noise_allowed("CO", "medium") is True
        assert noise_allowed("CO", "high") is False

    def test_sp_allows_all_standard(self):
        assert noise_allowed("SP", "low") is True
        assert noise_allowed("SP", "medium") is True
        assert noise_allowed("SP", "high") is True

    def test_fa_allows_everything(self):
        assert noise_allowed("FA", "low") is True
        assert noise_allowed("FA", "medium") is True
        assert noise_allowed("FA", "high") is True

    def test_noise_ranks_ordering(self):
        assert NOISE_RANKS["low"] < NOISE_RANKS["medium"] < NOISE_RANKS["high"] < NOISE_RANKS["all"]


# ---------------------------------------------------------------------------
# Orient noise filtering tests (unit — mocked DB)
# ---------------------------------------------------------------------------


class TestOrientNoiseFiltering:
    @pytest.mark.asyncio
    async def test_filter_removes_high_noise_in_co_mode(self):
        """CO mode should exclude noise:high techniques from options."""
        from app.services.orient_engine import OrientEngine

        ws = AsyncMock()
        engine = OrientEngine(ws)

        db = AsyncMock()
        # Mock: technique noise lookups
        db.fetch = AsyncMock(return_value=[
            {"mitre_id": "T1003.001", "noise_level": "medium"},
            {"mitre_id": "T1046", "noise_level": "high"},
            {"mitre_id": "T1087", "noise_level": "low"},
        ])

        parsed = {
            "situation_assessment": "test",
            "recommended_technique_id": "T1046",
            "confidence": 0.9,
            "options": [
                {"technique_id": "T1046", "confidence": 0.9},
                {"technique_id": "T1003.001", "confidence": 0.8},
                {"technique_id": "T1087", "confidence": 0.7},
            ],
        }

        result = await engine._filter_options_by_noise(db, parsed, "CO")
        tech_ids = [o["technique_id"] for o in result["options"]]
        assert "T1046" not in tech_ids  # high noise excluded
        assert "T1003.001" in tech_ids  # medium allowed
        assert "T1087" in tech_ids  # low allowed
        # recommended should shift since T1046 was removed
        assert result["recommended_technique_id"] == "T1003.001"

    @pytest.mark.asyncio
    async def test_filter_keeps_all_in_fa_mode(self):
        """FA mode should not filter any options."""
        from app.services.orient_engine import OrientEngine

        ws = AsyncMock()
        engine = OrientEngine(ws)
        db = AsyncMock()

        parsed = {
            "situation_assessment": "test",
            "recommended_technique_id": "T1046",
            "confidence": 0.9,
            "options": [
                {"technique_id": "T1046", "confidence": 0.9},
                {"technique_id": "T1003.001", "confidence": 0.8},
            ],
        }

        result = await engine._filter_options_by_noise(db, parsed, "FA")
        assert len(result["options"]) == 2  # all kept

    @pytest.mark.asyncio
    async def test_filter_sr_only_low_noise(self):
        """SR mode should only keep noise:low techniques."""
        from app.services.orient_engine import OrientEngine

        ws = AsyncMock()
        engine = OrientEngine(ws)

        db = AsyncMock()
        db.fetch = AsyncMock(return_value=[
            {"mitre_id": "T1595.001", "noise_level": "low"},
            {"mitre_id": "T1003.001", "noise_level": "medium"},
            {"mitre_id": "T1046", "noise_level": "high"},
        ])

        parsed = {
            "situation_assessment": "test",
            "recommended_technique_id": "T1003.001",
            "confidence": 0.85,
            "options": [
                {"technique_id": "T1003.001", "confidence": 0.85},
                {"technique_id": "T1046", "confidence": 0.8},
                {"technique_id": "T1595.001", "confidence": 0.7},
            ],
        }

        result = await engine._filter_options_by_noise(db, parsed, "SR")
        tech_ids = [o["technique_id"] for o in result["options"]]
        assert tech_ids == ["T1595.001"]  # only low noise
        assert result["recommended_technique_id"] == "T1595.001"

    @pytest.mark.asyncio
    async def test_filter_fallback_when_all_excluded(self):
        """If all options exceed noise limit, keep only the lowest-noise option."""
        from app.services.orient_engine import OrientEngine

        ws = AsyncMock()
        engine = OrientEngine(ws)

        db = AsyncMock()
        db.fetch = AsyncMock(return_value=[
            {"mitre_id": "T1046", "noise_level": "high"},
            {"mitre_id": "T1110", "noise_level": "high"},
        ])

        parsed = {
            "situation_assessment": "test",
            "recommended_technique_id": "T1046",
            "confidence": 0.9,
            "options": [
                {"technique_id": "T1046", "confidence": 0.9},
                {"technique_id": "T1110", "confidence": 0.8},
            ],
        }

        result = await engine._filter_options_by_noise(db, parsed, "SR")
        # NR4 fix: fallback keeps only 1 lowest-noise option (not all)
        assert len(result["options"]) == 1
        assert result["options"][0].get("noise_override") is True


# ---------------------------------------------------------------------------
# Operation mission_profile DB integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_operation_with_mission_profile(tmp_db):
    """Creating an operation with mission_profile stores it."""
    import uuid
    from datetime import datetime, timezone

    op_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await tmp_db.execute(
        "INSERT INTO operations "
        "(id, code, name, codename, strategic_intent, mission_profile, status, "
        "current_ooda_phase, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, 'planning', 'observe', $7, $8)",
        op_id, "OP-TEST", "Test", "PHANTOM", "test intent", "CO", now, now,
    )

    row = await tmp_db.fetchrow("SELECT mission_profile FROM operations WHERE id = $1", op_id)
    assert row["mission_profile"] == "CO"


@pytest.mark.asyncio
async def test_operation_default_mission_profile(tmp_db):
    """Default mission_profile should be SP."""
    import uuid
    from datetime import datetime, timezone

    op_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await tmp_db.execute(
        "INSERT INTO operations "
        "(id, code, name, codename, strategic_intent, status, "
        "current_ooda_phase, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, 'planning', 'observe', $6, $7)",
        op_id, "OP-TEST", "Test", "PHANTOM", "test intent", now, now,
    )

    row = await tmp_db.fetchrow("SELECT mission_profile FROM operations WHERE id = $1", op_id)
    assert row["mission_profile"] == "SP"


@pytest.mark.asyncio
async def test_technique_noise_level_column(tmp_db):
    """Techniques table should have noise_level column with default medium."""
    import uuid

    tech_id = str(uuid.uuid4())
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ($1, $2, 'Test Tech', 'Discovery', 'TA0007', 'low')",
        tech_id, "T9999",
    )

    row = await tmp_db.fetchrow("SELECT noise_level FROM techniques WHERE id = $1", tech_id)
    assert row["noise_level"] == "medium"  # default


@pytest.mark.asyncio
async def test_technique_noise_level_explicit(tmp_db):
    """Can explicitly set noise_level on a technique."""
    import uuid

    tech_id = str(uuid.uuid4())
    await tmp_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level, noise_level) "
        "VALUES ($1, $2, 'Noisy Scan', 'Discovery', 'TA0007', 'low', 'high')",
        tech_id, "T9998",
    )

    row = await tmp_db.fetchrow("SELECT noise_level FROM techniques WHERE id = $1", tech_id)
    assert row["noise_level"] == "high"

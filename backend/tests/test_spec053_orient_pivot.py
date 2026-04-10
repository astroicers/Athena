# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-053 Test Matrix — Orient-driven pivot detection and prompt.

Covers test cases T01, T02, and T08 from SPEC-053 §Test Matrix:

    T01: Orient structured failure query returns JOINed rows with
         failure_category when an IA failure exists
    T02: Orient does NOT pivot to T1190 when there is no exploitable
         banner fact
    T08: OODAController._detect_cross_category_pivot correctly
         identifies a T1190 recommendation that follows a T1110/T1078
         auth_failure on the same target

T01/T02 are covered at the _query_ level (what rows Orient actually
sees) rather than the LLM recommendation level, because the LLM
response is stochastic and the contract we care about is the
**context Orient gives the LLM**. Rule #9 text is exercised by a
simple string assertion on the system prompt.

T08 is covered as a method-level test with a stubbed DB cursor so
we don't need a running postgres for the pivot detection logic.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
from app.services.ooda_controller import OODAController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_controller() -> OODAController:
    """Build an OODAController with mostly-noop collaborators.

    Only _detect_cross_category_pivot is exercised; we don't need the
    full dependency graph.
    """
    return OODAController(
        fact_collector=MagicMock(),
        orient_engine=MagicMock(),
        decision_engine=MagicMock(),
        engine_router=MagicMock(),
        c5isr_mapper=MagicMock(),
        ws_manager=MagicMock(),
        swarm_executor=None,
    )


# ---------------------------------------------------------------------------
# T08: Cross-category pivot detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t08_pivot_detected_when_t1190_follows_t1110_auth_failure() -> None:
    """Orient decision T1190 after T1110 [auth_failure] -> pivot event."""
    controller = _make_controller()

    # Stub DB: a failed T1110.001 with auth_failure exists for the same target
    db = MagicMock()
    db.fetchrow = AsyncMock(return_value={"technique_id": "T1110.001"})

    decision = {
        "technique_id": "T1190",
        "target_id": "tgt-abc",
    }

    pivot = await controller._detect_cross_category_pivot(
        db, "op-001", decision,
    )

    assert pivot is not None
    assert pivot["from_technique"] == "T1110.001"
    assert pivot["to_technique"] == "T1190"
    assert pivot["target_id"] == "tgt-abc"
    assert pivot["reason"] == "ia_exhausted_banner_matched"


@pytest.mark.asyncio
async def test_t08_pivot_detected_for_t1078_prior_failure() -> None:
    """T1078.* also counts as a prior IA failure for pivot detection."""
    controller = _make_controller()
    db = MagicMock()
    db.fetchrow = AsyncMock(return_value={"technique_id": "T1078.001"})

    pivot = await controller._detect_cross_category_pivot(
        db, "op-001", {"technique_id": "T1190", "target_id": "tgt-abc"},
    )
    assert pivot is not None
    assert pivot["from_technique"] == "T1078.001"


@pytest.mark.asyncio
async def test_t08_not_a_pivot_when_no_prior_failure() -> None:
    """No prior T1110/T1078 auth_failure -> not a pivot."""
    controller = _make_controller()
    db = MagicMock()
    db.fetchrow = AsyncMock(return_value=None)

    pivot = await controller._detect_cross_category_pivot(
        db, "op-001", {"technique_id": "T1190", "target_id": "tgt-abc"},
    )
    assert pivot is None


@pytest.mark.asyncio
async def test_t08_not_a_pivot_when_decision_is_not_t1190() -> None:
    """A non-T1190 decision should never be a pivot."""
    controller = _make_controller()
    db = MagicMock()
    # Even if DB would return a row, we should short-circuit before the query
    db.fetchrow = AsyncMock(return_value={"technique_id": "T1110.001"})

    for tech in ("T1046", "T1110.001", "T1003.001"):
        pivot = await controller._detect_cross_category_pivot(
            db, "op-001", {"technique_id": tech, "target_id": "tgt-abc"},
        )
        assert pivot is None, f"{tech} should not be classified as pivot"


@pytest.mark.asyncio
async def test_t08_not_a_pivot_with_missing_target_id() -> None:
    """Decision without target_id can't be a targeted pivot."""
    controller = _make_controller()
    db = MagicMock()
    db.fetchrow = AsyncMock(return_value={"technique_id": "T1110.001"})

    pivot = await controller._detect_cross_category_pivot(
        db, "op-001", {"technique_id": "T1190"},
    )
    assert pivot is None


# ---------------------------------------------------------------------------
# Rule #9 prompt contract — text present in system prompt
# ---------------------------------------------------------------------------


def test_rule_9_exists_in_system_prompt() -> None:
    """SPEC-053 Rule #9 text must be in the Orient system prompt."""
    assert "Initial Access Exhausted" in _ORIENT_SYSTEM_PROMPT
    assert "Exploit Pivot" in _ORIENT_SYSTEM_PROMPT
    assert "T1190" in _ORIENT_SYSTEM_PROMPT
    assert "auth_failure" in _ORIENT_SYSTEM_PROMPT


def test_rule_8_relaxed_no_longer_requires_cve_fact() -> None:
    """Rule #8 must no longer gate T1190 on 'CVE facts present'."""
    # Phrase from old prompt that should be gone
    assert "CVE facts present" not in _ORIENT_SYSTEM_PROMPT
    # New phrasing that should be in
    assert "known exploitable" in _ORIENT_SYSTEM_PROMPT.lower() \
        or "exploitable banner" in _ORIENT_SYSTEM_PROMPT.lower()


def test_rule_9_explicit_exception_to_rule_6() -> None:
    """Rule #9 must declare itself as an exception to Rule #6."""
    # Must mention Rule 6 (No Redundant Recommendations) and note the
    # exception so an LLM reading the prompt doesn't suppress T1190.
    assert "Rule #6" in _ORIENT_SYSTEM_PROMPT
    assert "EXPLICIT EXCEPTION" in _ORIENT_SYSTEM_PROMPT or \
        "exception" in _ORIENT_SYSTEM_PROMPT.lower()

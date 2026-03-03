# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0
"""Tests for OrientEngine prompt building."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_ws():
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    return ws


async def test_section_77_appears_when_creds_available(seeded_db):
    """有 credential.ssh fact 時，prompt 應包含 Section 7.7 橫移機會資訊。"""
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row

    await seeded_db.execute(
        "INSERT INTO facts "
        "(id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh', "
        "'admin:password@10.0.1.5:22', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    assert "7.7" in user_prompt
    assert "lateral" in user_prompt.lower() or "credential" in user_prompt.lower()


async def test_section_77_idle_when_no_creds(seeded_db):
    """無 credential.ssh fact 時，Section 7.7 應顯示 no opportunities。"""
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    assert "No lateral movement opportunities" in user_prompt

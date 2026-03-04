# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for OrientEngine prompt building."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.orient_engine import OrientEngine


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


async def test_section_76_shows_windows_playbooks_for_windows_target(seeded_db):
    """Windows target → Section 7.6 shows Windows playbooks (T1021.001 or T1053.005).

    seeded_db has test-target-1 as 'Windows Server 2022', so platform detection
    should resolve to 'windows' and query windows-platform playbooks.
    """
    import aiosqlite
    from app.database import _seed_technique_playbooks
    seeded_db.row_factory = aiosqlite.Row

    # Seed playbooks so Section 7.6 has data to return
    await _seed_technique_playbooks(seeded_db)
    await seeded_db.commit()

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    # Windows-specific technique IDs should appear (from platform="windows" playbooks)
    assert "T1021.001" in user_prompt or "T1053.005" in user_prompt or "T1059.001" in user_prompt
    # Linux-specific technique IDs should NOT appear
    assert "T1053.003" not in user_prompt  # linux-only cron playbook


async def test_section_76_shows_linux_playbooks_for_linux_target(seeded_db):
    """Linux target → Section 7.6 shows Linux playbooks (not Windows-only techniques).

    Inserts a second Linux target and verifies linux playbooks appear.
    """
    import aiosqlite
    from app.database import _seed_technique_playbooks
    seeded_db.row_factory = aiosqlite.Row

    # Insert a Linux-only operation and target
    await seeded_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, status, current_ooda_phase) "
        "VALUES ('test-op-linux', 'OP-LNX-001', 'Linux Op', 'SHADOW-LNX', "
        "'Test linux intent', 'active', 'observe')"
    )
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('test-target-linux', 'LX-01', '10.0.2.1', 'Ubuntu 22.04', "
        "'Web Server', 'test-op-linux')"
    )
    await seeded_db.commit()

    # Seed playbooks
    await _seed_technique_playbooks(seeded_db)
    await seeded_db.commit()

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-linux", "observe")
    # Linux-specific technique IDs should appear (from platform="linux" playbooks)
    assert "T1053.003" in user_prompt or "T1543.002" in user_prompt or "T1105" in user_prompt
    # Windows-specific technique IDs should NOT appear
    assert "T1021.001" not in user_prompt  # windows-only RDP playbook


async def test_section_77_shows_persistence_status(seeded_db):
    """Section 7.7 should always include 'Persistence status:' line."""
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    assert "Persistence status:" in user_prompt


async def test_section_77_shows_persistence_facts_when_present(seeded_db):
    """When host.persistence facts exist, Section 7.7 reports confirmed persistence vectors."""
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row

    # Insert a persistence fact for the primary target
    await seeded_db.execute(
        "INSERT INTO facts "
        "(id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'host.persistence', "
        "'cron job /etc/cron.d/backdoor', 'host', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    assert "Persistence vectors confirmed:" in user_prompt
    assert "cron job" in user_prompt


async def test_section_77_shows_no_persistence_when_none(seeded_db):
    """When no host.persistence facts exist, Section 7.7 reports no persistence established."""
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row

    from app.services.orient_engine import OrientEngine
    engine = OrientEngine(_make_ws())
    _, user_prompt = await engine._build_prompt(seeded_db, "test-op-1", "test-target-1")
    assert "No persistence established yet." in user_prompt


async def test_orient_prompt_includes_mcp_section_when_enabled(seeded_db):
    """Section 7.8 MCP tools appears when MCP_ENABLED=True."""
    import aiosqlite

    seeded_db.row_factory = aiosqlite.Row

    mock_mgr = MagicMock()
    mock_tool = MagicMock(
        server_name="nmap-scanner", tool_name="nmap_scan", description="Port scan"
    )
    mock_mgr.list_all_tools.return_value = [mock_tool]

    with (
        patch("app.services.orient_engine.settings") as s,
        patch(
            "app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mgr
        ),
    ):
        s.MOCK_LLM = True
        s.MCP_ENABLED = True
        s.LLM_BACKEND = "auto"
        s.ANTHROPIC_API_KEY = ""
        s.ANTHROPIC_AUTH_TOKEN = ""
        engine = OrientEngine(_make_ws())
        _, user_prompt = await engine._build_prompt(
            seeded_db, "test-op-1", "summary"
        )

    assert "7.8" in user_prompt
    assert "nmap_scan" in user_prompt


async def test_orient_prompt_no_mcp_section_when_disabled(seeded_db):
    """Section 7.8 shows (MCP disabled) when MCP_ENABLED=False."""
    import aiosqlite

    seeded_db.row_factory = aiosqlite.Row

    with patch("app.services.orient_engine.settings") as s:
        s.MOCK_LLM = True
        s.MCP_ENABLED = False
        s.LLM_BACKEND = "auto"
        s.ANTHROPIC_API_KEY = ""
        s.ANTHROPIC_AUTH_TOKEN = ""
        engine = OrientEngine(_make_ws())
        _, user_prompt = await engine._build_prompt(
            seeded_db, "test-op-1", "summary"
        )

    assert "(MCP disabled)" in user_prompt

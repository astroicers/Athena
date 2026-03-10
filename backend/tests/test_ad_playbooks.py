# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests: Windows AD technique playbooks — DB seeds + MCP executor mapping."""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


AD_TECHNIQUE_IDS = ["T1069.002", "T1558.003", "T1003.001", "T1003.003", "T1018"]


def test_mcp_attack_executor_has_ad_techniques():
    """MCP attack-executor WINRM_TECHNIQUE_EXECUTORS should contain AD technique IDs."""
    # Add the tools directory to path to import the MCP server module
    tools_dir = Path(__file__).resolve().parent.parent.parent / "tools" / "attack-executor"
    sys.path.insert(0, str(tools_dir))
    try:
        from server import WINRM_TECHNIQUE_EXECUTORS
    finally:
        sys.path.pop(0)

    for tid in AD_TECHNIQUE_IDS:
        # T1003.001 is mapped as T1003.001_win in WinRM executors
        check_tid = "T1003.001_win" if tid == "T1003.001" else tid
        assert check_tid in WINRM_TECHNIQUE_EXECUTORS, f"{check_tid} missing from WINRM_TECHNIQUE_EXECUTORS"


async def test_windows_ad_playbooks_seeded(seeded_db):
    """After seeding, Windows AD playbooks should exist in technique_playbooks."""
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from uuid import uuid4

    count = await seeded_db.fetchval("SELECT COUNT(*) FROM technique_playbooks")
    if count == 0:
        for seed in TECHNIQUE_PLAYBOOK_SEEDS:
            await seeded_db.execute(
                """INSERT INTO technique_playbooks
                   (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
                   VALUES ($1, $2, $3, $4, $5, $6, 'seed', $7)
                   ON CONFLICT DO NOTHING""",
                str(uuid4()), seed["mitre_id"], seed["platform"],
                seed["command"], seed.get("output_parser"),
                seed["facts_traits"], seed["tags"],
            )

    rows = await seeded_db.fetch(
        "SELECT mitre_id FROM technique_playbooks WHERE platform = 'windows'"
    )
    seeded_ids = {r["mitre_id"] for r in rows}

    for tid in ["T1069.002", "T1558.003", "T1003.003", "T1018"]:
        assert tid in seeded_ids, f"{tid} not found in Windows playbook seeds"


async def test_technique_seeds_exist(seeded_db):
    """After seeding, AD technique definitions should exist in techniques table."""
    from app.database.seed import TECHNIQUE_SEEDS
    from uuid import uuid4

    # Seed techniques if needed
    count = await seeded_db.fetchval("SELECT COUNT(*) FROM techniques WHERE mitre_id IN ('T1069.002','T1558.003','T1003.003','T1018')")
    if count == 0:
        for seed in TECHNIQUE_SEEDS:
            if seed.get("mitre_id") in ("T1069.002", "T1558.003", "T1003.003", "T1018"):
                await seeded_db.execute(
                    """INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT DO NOTHING""",
                    str(uuid4()), seed["mitre_id"], seed["name"],
                    seed["tactic"], seed["tactic_id"], seed.get("risk_level", "medium"),
                )

    rows = await seeded_db.fetch(
        "SELECT mitre_id, tactic_id FROM techniques WHERE mitre_id IN ('T1069.002','T1558.003','T1003.003','T1018')"
    )
    found = {r["mitre_id"]: r["tactic_id"] for r in rows}

    assert found.get("T1069.002") == "TA0007"  # Discovery
    assert found.get("T1558.003") == "TA0006"  # Credential Access
    assert found.get("T1003.003") == "TA0006"  # Credential Access
    assert found.get("T1018") == "TA0007"      # Discovery

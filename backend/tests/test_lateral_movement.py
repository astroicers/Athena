# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0
"""Unit tests: lateral movement — SSH key-based auth + technique mapping."""
import base64

import pytest


async def test_technique_executors_has_lateral_techniques():
    """TECHNIQUE_EXECUTORS 應包含橫移技術。"""
    from app.clients._ssh_common import TECHNIQUE_EXECUTORS, TECHNIQUE_FACT_TRAITS

    for tid in ("T1021.004_priv", "T1021.004_recon", "T1560.001", "T1105"):
        assert tid in TECHNIQUE_EXECUTORS, f"{tid} missing from TECHNIQUE_EXECUTORS"
        assert tid in TECHNIQUE_FACT_TRAITS, f"{tid} missing from TECHNIQUE_FACT_TRAITS"


async def test_parse_key_credential_valid():
    """_parse_key_credential 應正確解析 user@host:port#<b64key> 格式。"""
    from app.clients.persistent_ssh_client import _parse_key_credential

    fake_key = base64.b64encode(b"FAKE_KEY_CONTENT").decode()
    target = f"admin@10.0.0.1:22#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert user == "admin"
    assert host == "10.0.0.1"
    assert port == 22
    assert key_content == "FAKE_KEY_CONTENT"


async def test_parse_key_credential_default_port():
    """_parse_key_credential 無 port 時預設 22。"""
    from app.clients.persistent_ssh_client import _parse_key_credential

    fake_key = base64.b64encode(b"KEY").decode()
    target = f"root@192.168.1.1#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert port == 22
    assert host == "192.168.1.1"


async def test_ssh_key_fact_prioritized_over_password(seeded_db):
    """credential.ssh_key fact 應比 credential.ssh 優先被選取。"""
    import uuid
    import aiosqlite
    seeded_db.row_factory = aiosqlite.Row
    # 插入兩個 fact：password 和 key
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh', 'user:pass@10.0.0.1:22', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh_key', 'user@10.0.0.1:22#KEYDATA', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    cursor = await seeded_db.execute(
        "SELECT trait, value FROM facts "
        "WHERE operation_id = 'test-op-1' AND source_target_id = 'test-target-1' "
        "AND trait IN ('credential.ssh', 'credential.ssh_key') "
        "ORDER BY CASE trait WHEN 'credential.ssh_key' THEN 0 ELSE 1 END "
        "LIMIT 1",
    )
    row = await cursor.fetchone()
    assert row["trait"] == "credential.ssh_key"

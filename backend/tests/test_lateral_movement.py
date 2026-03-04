# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests: lateral movement — SSH key-based auth + technique mapping."""
import base64
import uuid

import pytest


def test_technique_executors_has_lateral_techniques():
    """TECHNIQUE_EXECUTORS 應包含橫移技術。"""
    from app.clients._ssh_common import TECHNIQUE_EXECUTORS, TECHNIQUE_FACT_TRAITS

    for tid in ("T1021.004_priv", "T1021.004_recon", "T1560.001", "T1105"):
        assert tid in TECHNIQUE_EXECUTORS, f"{tid} missing from TECHNIQUE_EXECUTORS"
        assert tid in TECHNIQUE_FACT_TRAITS, f"{tid} missing from TECHNIQUE_FACT_TRAITS"


def test_parse_key_credential_valid():
    """_parse_key_credential 應正確解析 user@host:port#<b64key> 格式。"""
    from app.clients.persistent_ssh_client import _parse_key_credential

    fake_key = base64.b64encode(b"FAKE_KEY_CONTENT").decode()
    target = f"admin@10.0.0.1:22#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert user == "admin"
    assert host == "10.0.0.1"
    assert port == 22
    assert key_content == "FAKE_KEY_CONTENT"


def test_parse_key_credential_default_port():
    """_parse_key_credential 無 port 時預設 22。"""
    from app.clients.persistent_ssh_client import _parse_key_credential

    fake_key = base64.b64encode(b"KEY").decode()
    target = f"root@192.168.1.1#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert port == 22
    assert host == "192.168.1.1"


def test_parse_key_credential_invalid_format_raises():
    """格式錯誤的 target 應拋出 ValueError。"""
    from app.clients.persistent_ssh_client import _parse_key_credential

    with pytest.raises(ValueError):
        _parse_key_credential("no_hash_separator_here")

    with pytest.raises(ValueError):
        _parse_key_credential("user@host:22#NOT_VALID_BASE64!!!")


async def test_ssh_key_fact_prioritized_over_password(seeded_db):
    """credential.ssh_key fact 應比 credential.ssh 優先被選取。"""
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


async def test_successful_ssh_marks_target_compromised(seeded_db):
    """SSH 執行成功後，target.is_compromised 應為 1，privilege_level 為 'root'。"""
    import uuid
    import aiosqlite
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    # Insert SSH credential fact so _execute_ssh finds it
    seeded_db.row_factory = aiosqlite.Row
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.0.1:22', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    mock_result = ExecutionResult(
        success=True,
        execution_id="test-exec-1",
        output="uid=0(root) gid=0(root) groups=0(root)",
        facts=[],
    )

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fact_collector = MagicMock()
    fact_collector.collect_from_result = AsyncMock()

    with patch(
        "app.clients.direct_ssh_client.DirectSSHEngine.execute",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        router = EngineRouter(
            c2_engine=MagicMock(),

            fact_collector=fact_collector,
            ws_manager=ws,
        )
        await router._execute_ssh(
            db=seeded_db,
            exec_id="test-exec-99",
            now="2026-01-01T00:00:00",
            ability_id="T1021.004",
            technique_id="T1021.004",
            target_id="test-target-1",
            engine="ssh",
            operation_id="test-op-1",
            ooda_iteration_id=None,
        )

    cursor = await seeded_db.execute(
        "SELECT is_compromised, privilege_level FROM targets WHERE id = 'test-target-1'"
    )
    row = await cursor.fetchone()
    assert row["is_compromised"] == 1
    assert row["privilege_level"] == "root"


async def test_failed_ssh_does_not_mark_compromised(seeded_db):
    """SSH 執行失敗時，target.is_compromised 不應變更。"""
    import uuid
    import aiosqlite
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    # Insert SSH credential fact so _execute_ssh finds it
    seeded_db.row_factory = aiosqlite.Row
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES (?, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.0.1:22', 'credential', 1)",
        (str(uuid.uuid4()),),
    )
    await seeded_db.commit()

    mock_result = ExecutionResult(
        success=False,
        execution_id="test-exec-100",
        output=None,
        error="Connection refused",
        facts=[],
    )

    ws = MagicMock()
    ws.broadcast = AsyncMock()
    fact_collector = MagicMock()
    fact_collector.collect_from_result = AsyncMock()

    with patch(
        "app.clients.direct_ssh_client.DirectSSHEngine.execute",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        router = EngineRouter(
            c2_engine=MagicMock(),

            fact_collector=fact_collector,
            ws_manager=ws,
        )
        await router._execute_ssh(
            db=seeded_db,
            exec_id="test-exec-100",
            now="2026-01-01T00:00:00",
            ability_id="T1021.004",
            technique_id="T1021.004",
            target_id="test-target-1",
            engine="ssh",
            operation_id="test-op-1",
            ooda_iteration_id=None,
        )

    cursor = await seeded_db.execute(
        "SELECT is_compromised FROM targets WHERE id = 'test-target-1'"
    )
    row = await cursor.fetchone()
    assert row["is_compromised"] == 0  # 未改變

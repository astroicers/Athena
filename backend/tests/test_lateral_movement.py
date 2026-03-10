# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests: lateral movement — SSH key-based auth + credential priority."""
import base64
import uuid
from datetime import datetime, timezone

import pytest


def test_parse_key_credential_valid():
    """_parse_key_credential should parse user@host:port#<b64key> correctly."""
    from app.clients._ssh_common import _parse_key_credential

    fake_key = base64.b64encode(b"FAKE_KEY_CONTENT").decode()
    target = f"admin@10.0.0.1:22#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert user == "admin"
    assert host == "10.0.0.1"
    assert port == 22
    assert key_content == "FAKE_KEY_CONTENT"


def test_parse_key_credential_default_port():
    """_parse_key_credential should default to port 22."""
    from app.clients._ssh_common import _parse_key_credential

    fake_key = base64.b64encode(b"KEY").decode()
    target = f"root@192.168.1.1#{fake_key}"
    user, host, port, key_content = _parse_key_credential(target)
    assert port == 22
    assert host == "192.168.1.1"


def test_parse_key_credential_invalid_format_raises():
    """Invalid target should raise ValueError."""
    from app.clients._ssh_common import _parse_key_credential

    with pytest.raises(ValueError):
        _parse_key_credential("no_hash_separator_here")

    with pytest.raises(ValueError):
        _parse_key_credential("user@host:22#NOT_VALID_BASE64!!!")


async def test_ssh_key_fact_prioritized_over_password(seeded_db):
    """credential.ssh_key fact should be prioritized over credential.ssh."""
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential.ssh', 'user:pass@10.0.0.1:22', 'credential', 1)",
        str(uuid.uuid4()),
    )
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential.ssh_key', 'user@10.0.0.1:22#KEYDATA', 'credential', 1)",
        str(uuid.uuid4()),
    )

    row = await seeded_db.fetchrow(
        "SELECT trait, value FROM facts "
        "WHERE operation_id = 'test-op-1' AND source_target_id = 'test-target-1' "
        "AND trait IN ('credential.ssh', 'credential.ssh_key') "
        "ORDER BY CASE trait WHEN 'credential.ssh_key' THEN 0 ELSE 1 END "
        "LIMIT 1",
    )
    assert row["trait"] == "credential.ssh_key"


async def test_mcp_executor_marks_target_compromised(seeded_db):
    """MCP executor success should mark target as compromised with root privilege."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.0.1:22', 'credential', 1)",
        str(uuid.uuid4()),
    )

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

    mcp_engine = AsyncMock()
    mcp_engine.execute = AsyncMock(return_value=mock_result)

    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=fact_collector,
        ws_manager=ws,
        mcp_engine=mcp_engine,
    )
    await router._execute_via_mcp_executor(
        db=seeded_db,
        exec_id="test-exec-99",
        now=datetime.now(timezone.utc),
        ability_id="T1021.004",
        technique_id="T1021.004",
        target_id="test-target-1",
        engine="mcp_ssh",
        operation_id="test-op-1",
        ooda_iteration_id=None,
    )

    row = await seeded_db.fetchrow(
        "SELECT is_compromised, privilege_level FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is True
    assert row["privilege_level"] == "root"


async def test_failed_mcp_executor_does_not_mark_compromised(seeded_db):
    """MCP executor failure should not change target.is_compromised."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.engine_router import EngineRouter
    from app.clients import ExecutionResult

    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ($1, 'test-op-1', 'test-target-1', 'credential.ssh', 'root:pass@10.0.0.1:22', 'credential', 1)",
        str(uuid.uuid4()),
    )

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

    mcp_engine = AsyncMock()
    mcp_engine.execute = AsyncMock(return_value=mock_result)

    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=fact_collector,
        ws_manager=ws,
        mcp_engine=mcp_engine,
    )
    await router._execute_via_mcp_executor(
        db=seeded_db,
        exec_id="test-exec-100",
        now=datetime.now(timezone.utc),
        ability_id="T1021.004",
        technique_id="T1021.004",
        target_id="test-target-1",
        engine="mcp_ssh",
        operation_id="test-op-1",
        ooda_iteration_id=None,
    )

    row = await seeded_db.fetchrow(
        "SELECT is_compromised FROM targets WHERE id = 'test-target-1'"
    )
    assert row["is_compromised"] is False

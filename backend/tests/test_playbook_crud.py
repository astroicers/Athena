# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for Playbook CRUD API."""
from httpx import AsyncClient


async def test_list_playbooks_returns_seeded(client: AsyncClient):
    """GET /api/playbooks returns at least 100 seed playbooks."""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 100


async def test_create_playbook(client: AsyncClient):
    """POST /api/playbooks creates a new user playbook."""
    resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T9999",
            "platform": "linux",
            "command": "whoami",
            "output_parser": "first_line",
            "facts_traits": ["host.user"],
            "tags": ["test"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mitre_id"] == "T9999"
    assert body["id"]
    assert body["source"] == "user"


async def test_get_playbook_by_id(client: AsyncClient):
    """GET /api/playbooks/{id} returns a specific playbook."""
    create = await client.post(
        "/api/playbooks",
        json={"mitre_id": "T8888", "platform": "linux", "command": "id", "facts_traits": []},
    )
    pb_id = create.json()["id"]

    resp = await client.get(f"/api/playbooks/{pb_id}")
    assert resp.status_code == 200
    assert resp.json()["mitre_id"] == "T8888"


async def test_update_playbook(client: AsyncClient):
    """PATCH /api/playbooks/{id} updates the command."""
    create = await client.post(
        "/api/playbooks",
        json={"mitre_id": "T7777", "platform": "linux", "command": "old_cmd", "facts_traits": []},
    )
    pb_id = create.json()["id"]

    resp = await client.patch(f"/api/playbooks/{pb_id}", json={"command": "new_cmd"})
    assert resp.status_code == 200
    assert resp.json()["command"] == "new_cmd"


async def test_delete_playbook(client: AsyncClient):
    """DELETE /api/playbooks/{id} removes a user playbook."""
    create = await client.post(
        "/api/playbooks",
        json={"mitre_id": "T6666", "platform": "linux", "command": "ls", "facts_traits": []},
    )
    pb_id = create.json()["id"]

    assert (await client.delete(f"/api/playbooks/{pb_id}")).status_code == 204
    assert (await client.get(f"/api/playbooks/{pb_id}")).status_code == 404


async def test_cannot_delete_seed_playbook(client: AsyncClient):
    """DELETE seed playbook returns 403 Forbidden."""
    all_pb = (await client.get("/api/playbooks")).json()
    seed = next(p for p in all_pb if p.get("source") == "seed")
    resp = await client.delete(f"/api/playbooks/{seed['id']}")
    assert resp.status_code == 403


async def test_list_filter_by_mitre_id(client: AsyncClient):
    """GET /api/playbooks?mitre_id=T9998 returns only matching playbooks."""
    await client.post(
        "/api/playbooks",
        json={"mitre_id": "T9998", "platform": "linux", "command": "uname", "facts_traits": []},
    )
    resp = await client.get("/api/playbooks?mitre_id=T9998")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(p["mitre_id"] == "T9998" for p in data)


async def test_get_nonexistent_playbook_returns_404(client: AsyncClient):
    """GET /api/playbooks/{nonexistent} returns 404."""
    resp = await client.get("/api/playbooks/nonexistent-id-xyz")
    assert resp.status_code == 404


def _load_attack_executor_server():
    """Load attack-executor server.py via importlib to avoid sys.modules collision."""
    import importlib.util
    from pathlib import Path
    server_path = Path(__file__).resolve().parent.parent.parent / "tools" / "attack-executor" / "server.py"
    spec = importlib.util.spec_from_file_location("attack_executor_server", server_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_stdout_first_line_default():
    """Default output_parser takes first non-empty line."""
    mod = _load_attack_executor_server()
    facts = mod._parse_stdout_to_facts("T1592", "hostname\nsome other line", source="test")
    assert facts[0]["value"] == "hostname"


def test_parse_stdout_json_parser():
    """output_parser='json' parses JSON output."""
    mod = _load_attack_executor_server()
    facts = mod._parse_stdout_to_facts("T1592", '{"user": "root"}', source="test", output_parser="json")
    assert facts[0]["value"].startswith("{")


def test_parse_stdout_regex_parser():
    """output_parser as regex extracts first capture group."""
    mod = _load_attack_executor_server()
    facts = mod._parse_stdout_to_facts("T1592", "uid=0(root) gid=0(root)", source="test", output_parser=r"uid=(\d+)")
    assert facts[0]["value"] == "0"


async def test_patch_can_clear_output_parser(client: AsyncClient):
    """PATCH {"output_parser": null} should clear output_parser to NULL."""
    create_resp = await client.post("/api/playbooks", json={
        "mitre_id": "T5555", "platform": "linux",
        "command": "test_cmd", "facts_traits": [],
        "output_parser": "json",
    })
    assert create_resp.status_code == 201
    pb_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/playbooks/{pb_id}")
    assert get_resp.json()["output_parser"] == "json"

    patch_resp = await client.patch(
        f"/api/playbooks/{pb_id}",
        json={"output_parser": None},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["output_parser"] is None

    get_after = await client.get(f"/api/playbooks/{pb_id}")
    assert get_after.json()["output_parser"] is None


async def test_patch_command_null_is_ignored(client: AsyncClient):
    """PATCH {"command": null} should be ignored, not modify existing command."""
    create = await client.post("/api/playbooks", json={
        "mitre_id": "T4444", "platform": "linux",
        "command": "original_cmd", "facts_traits": [],
    })
    pb_id = create.json()["id"]

    resp = await client.patch(f"/api/playbooks/{pb_id}", json={"command": None})
    assert resp.status_code == 200
    assert resp.json()["command"] == "original_cmd"


async def test_output_parser_read_from_playbook_on_mcp_execute(seeded_db):
    """engine_router._get_output_parser should read output_parser from technique_playbooks
    and _execute_via_mcp_executor should forward it to MCP engine."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from app.clients import ExecutionResult
    from app.services.engine_router import EngineRouter
    from uuid import uuid4

    # Seed playbooks if needed
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

    # Insert a linux-platform T1033 playbook with output_parser='json' if not present
    await seeded_db.execute(
        "INSERT INTO technique_playbooks "
        "(id, mitre_id, platform, command, output_parser, facts_traits, tags, source) "
        "VALUES ('pb-t1033-test', 'T1033', 'linux', 'id', 'json', '[]', '[]', 'seed') "
        "ON CONFLICT DO NOTHING"
    )

    # Verify _get_output_parser returns the DB value
    ws_mock = MagicMock()
    ws_mock.broadcast = AsyncMock()
    mock_mcp = MagicMock()
    mock_mcp.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True, execution_id="mock-exec-id",
            output="root", facts=[], error=None,
        )
    )
    mock_fc = MagicMock()
    mock_fc.collect_from_result = AsyncMock(return_value=[])
    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=mock_fc,
        ws_manager=ws_mock,
        mcp_engine=mock_mcp,
    )

    output_parser = await router._get_output_parser(seeded_db, "T1033")
    assert output_parser == "json", (
        f"Expected 'json' from technique_playbooks for T1033, got {output_parser!r}"
    )

    # Insert required data: SSH credential fact for test target + technique record
    await seeded_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('tech-t1033', 'T1033', 'System Owner/User Discovery', 'Discovery', 'TA0007', 'low') "
        "ON CONFLICT DO NOTHING"
    )
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, score) "
        "VALUES ('fact-ssh-1', 'test-op-1', 'test-target-1', 'credential.ssh', "
        "'root:pass@10.0.1.5:22', 100)"
    )

    with patch("app.services.engine_router.settings") as mock_settings:
        mock_settings.EXECUTION_ENGINE = "mcp_ssh"
        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.PERSISTENCE_ENABLED = False

        result = await router.execute(
            db=seeded_db,
            technique_id="T1033",
            target_id="test-target-1",
            engine="auto",
            operation_id="test-op-1",
        )

    # The MCP engine must have been called with output_parser='json' in params
    mock_mcp.execute.assert_awaited_once()
    call_args = mock_mcp.execute.call_args
    params = call_args[1].get("params", {}) if call_args[1] else call_args[0][2] if len(call_args[0]) > 2 else {}
    assert params.get("output_parser") == "json", (
        f"MCP engine was not called with output_parser='json'; actual params: {params}"
    )


async def test_get_output_parser_windows_platform(seeded_db):
    """_get_output_parser with platform='windows' reads Windows playbook's output_parser."""
    from unittest.mock import MagicMock, AsyncMock
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from app.services.engine_router import EngineRouter
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

    # T1059.001 is seeded with platform='windows', output_parser='first_line'
    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=MagicMock(),
        ws_manager=MagicMock(broadcast=AsyncMock()),
    )
    result = await router._get_output_parser(seeded_db, "T1059.001", platform="windows")
    assert result == "first_line"


async def test_get_output_parser_windows_technique_linux_path_returns_none(seeded_db):
    """Windows-only technique queried with platform='linux' returns None (no linux seed)."""
    from unittest.mock import MagicMock, AsyncMock
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from app.services.engine_router import EngineRouter
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

    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=MagicMock(),
        ws_manager=MagicMock(broadcast=AsyncMock()),
    )
    # T1059.001 only exists as windows; querying linux should return None
    result = await router._get_output_parser(seeded_db, "T1059.001", platform="linux")
    assert result is None


async def test_mcp_executor_uses_windows_output_parser(seeded_db):
    """_execute_via_mcp_executor should pass windows output_parser for WinRM credential."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from app.clients import ExecutionResult
    from app.services.engine_router import EngineRouter
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

    mock_mcp = MagicMock()
    mock_mcp.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True, execution_id="mock-id",
            output="[MOCK WinRM] T1059.001 executed", facts=[], error=None,
        )
    )
    mock_fc = MagicMock()
    mock_fc.collect_from_result = AsyncMock(return_value=[])
    ws_mock = MagicMock(broadcast=AsyncMock())
    router = EngineRouter(
        c2_engine=MagicMock(),
        fact_collector=mock_fc,
        ws_manager=ws_mock,
        mcp_engine=mock_mcp,
    )

    await seeded_db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
        "VALUES ('tech-t1059', 'T1059.001', 'PowerShell', 'Execution', 'TA0002', 'medium') "
        "ON CONFLICT DO NOTHING"
    )
    # Insert WinRM credential so router picks windows platform
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, source_target_id, trait, value, score) "
        "VALUES ('fact-winrm-1', 'test-op-1', 'test-target-1', 'credential.winrm', "
        "'admin:pass@10.0.0.1:5985', 100)"
    )

    with patch("app.services.engine_router.settings") as mock_settings:
        mock_settings.EXECUTION_ENGINE = "mcp_ssh"
        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.PERSISTENCE_ENABLED = False

        result = await router.execute(
            db=seeded_db,
            technique_id="T1059.001",
            target_id="test-target-1",
            engine="auto",
            operation_id="test-op-1",
        )

    mock_mcp.execute.assert_awaited_once()
    call_args = mock_mcp.execute.call_args
    params = call_args[1].get("params", {}) if call_args[1] else call_args[0][2] if len(call_args[0]) > 2 else {}
    assert params.get("output_parser") == "first_line", (
        f"Expected 'first_line' (from windows seed), got {params.get('output_parser')!r}"
    )
    assert params.get("protocol") == "winrm", (
        f"Expected protocol='winrm' for WinRM credential, got {params.get('protocol')!r}"
    )

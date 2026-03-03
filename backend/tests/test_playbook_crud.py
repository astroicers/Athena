# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration tests for Playbook CRUD API."""
from httpx import AsyncClient


async def test_list_playbooks_returns_seeded(client: AsyncClient):
    """GET /api/playbooks returns at least the 13 seed playbooks."""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 13


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


def test_parse_stdout_first_line_default():
    """Default output_parser takes first non-empty line."""
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "hostname\nsome other line", source="test")
    assert facts[0]["value"] == "hostname"


def test_parse_stdout_json_parser():
    """output_parser='json' parses JSON output."""
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", '{"user": "root"}', source="test", output_parser="json")
    assert facts[0]["value"].startswith("{")


def test_parse_stdout_regex_parser():
    """output_parser as regex extracts first capture group."""
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "uid=0(root) gid=0(root)", source="test", output_parser=r"uid=(\d+)")
    assert facts[0]["value"] == "0"


async def test_patch_can_clear_output_parser(client: AsyncClient):
    """PATCH {"output_parser": null} 應能將 output_parser 清空為 NULL。"""
    create_resp = await client.post("/api/playbooks", json={
        "mitre_id": "T5555", "platform": "linux",
        "command": "test_cmd", "facts_traits": [],
        "output_parser": "json",
    })
    assert create_resp.status_code == 201
    pb_id = create_resp.json()["id"]

    # 先確認有值
    get_resp = await client.get(f"/api/playbooks/{pb_id}")
    assert get_resp.json()["output_parser"] == "json"

    # PATCH 清空
    patch_resp = await client.patch(
        f"/api/playbooks/{pb_id}",
        json={"output_parser": None},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["output_parser"] is None

    # 再次 GET 確認持久化
    get_after = await client.get(f"/api/playbooks/{pb_id}")
    assert get_after.json()["output_parser"] is None


async def test_patch_command_null_is_ignored(client: AsyncClient):
    """PATCH {"command": null} 應被忽略，不修改現有 command。"""
    create = await client.post("/api/playbooks", json={
        "mitre_id": "T4444", "platform": "linux",
        "command": "original_cmd", "facts_traits": [],
    })
    pb_id = create.json()["id"]

    resp = await client.patch(f"/api/playbooks/{pb_id}", json={"command": None})
    assert resp.status_code == 200
    # command 不應被清空
    assert resp.json()["command"] == "original_cmd"


async def test_output_parser_read_from_playbook_on_ssh_execute(seeded_db):
    """engine_router._get_output_parser should read output_parser from technique_playbooks
    and engine_router._execute_ssh should forward it to DirectSSHEngine.execute."""
    import aiosqlite
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.database import _seed_technique_playbooks
    from app.clients import ExecutionResult
    from app.services.engine_router import EngineRouter

    # Seed playbooks so the table has data (linux platform rows)
    await _seed_technique_playbooks(seeded_db)

    # Insert a linux-platform T1033 playbook with output_parser='json' if not present
    await seeded_db.execute(
        "INSERT OR IGNORE INTO technique_playbooks "
        "(id, mitre_id, platform, command, output_parser, facts_traits, tags, source) "
        "VALUES ('pb-t1033-test', 'T1033', 'linux', 'id', 'json', '[]', '[]', 'seed')"
    )
    await seeded_db.commit()

    # Verify _get_output_parser returns the DB value
    seeded_db.row_factory = aiosqlite.Row
    ws_mock = MagicMock()
    ws_mock.broadcast = AsyncMock()
    router = EngineRouter(
        c2_engine=MagicMock(),
        adaptive_engine=None,
        fact_collector=MagicMock(),
        ws_manager=ws_mock,
    )

    output_parser = await router._get_output_parser(seeded_db, "T1033")
    assert output_parser == "json", (
        f"Expected 'json' from technique_playbooks for T1033, got {output_parser!r}"
    )

    # Verify that _execute_ssh forwards the output_parser to DirectSSHEngine.execute
    with patch(
        "app.clients.direct_ssh_client.DirectSSHEngine.execute", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = ExecutionResult(
            success=True,
            execution_id="mock-exec-id",
            output="root",
            facts=[],
            error=None,
        )

        # Insert required data: SSH credential fact for test target + technique record
        await seeded_db.execute(
            "INSERT OR IGNORE INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
            "VALUES ('tech-t1033', 'T1033', 'System Owner/User Discovery', 'Discovery', 'TA0007', 'low')"
        )
        await seeded_db.execute(
            "INSERT INTO facts (id, operation_id, source_target_id, trait, value, score) "
            "VALUES ('fact-ssh-1', 'test-op-1', 'test-target-1', 'credential.ssh', "
            "'root:pass@10.0.1.5:22', 100)"
        )
        await seeded_db.commit()

        await router._execute_ssh(
            db=seeded_db,
            exec_id="exec-test-1",
            now="2026-01-01T00:00:00+00:00",
            ability_id="T1033",
            technique_id="T1033",
            target_id="test-target-1",
            engine="ssh",
            operation_id="test-op-1",
            ooda_iteration_id=None,
        )

    # The SSH engine must have been called with output_parser='json'
    mock_exec.assert_awaited_once()
    _, call_kwargs = mock_exec.call_args
    assert call_kwargs.get("output_parser") == "json", (
        f"DirectSSHEngine.execute was not called with output_parser='json'; "
        f"actual kwargs: {call_kwargs}"
    )

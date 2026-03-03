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

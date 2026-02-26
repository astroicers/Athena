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

"""API smoke tests — SPEC-004 acceptance criteria."""

# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------

async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


async def test_health_services_keys(client):
    resp = await client.get("/api/health")
    services = resp.json()["services"]
    for key in ("database", "caldera", "shannon", "websocket", "llm"):
        assert key in services


# ---------------------------------------------------------------------------
# 2. Operations CRUD
# ---------------------------------------------------------------------------

async def test_list_operations(client):
    resp = await client.get("/api/operations")
    assert resp.status_code == 200
    ops = resp.json()
    assert isinstance(ops, list)
    assert len(ops) >= 1  # seeded data


async def test_create_operation(client):
    resp = await client.post("/api/operations", json={
        "code": "OP-NEW-001",
        "name": "New Op",
        "codename": "TEST-NEW",
        "strategic_intent": "Testing",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "OP-NEW-001"
    assert data["status"] == "planning"


async def test_get_operation(client):
    resp = await client.get("/api/operations/test-op-1")
    assert resp.status_code == 200
    assert resp.json()["codename"] == "PHANTOM-TEST"


async def test_get_operation_not_found(client):
    resp = await client.get("/api/operations/nonexistent-id")
    assert resp.status_code == 404


async def test_update_operation(client):
    resp = await client.patch("/api/operations/test-op-1", json={
        "status": "paused",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


# ---------------------------------------------------------------------------
# 3. Techniques
# ---------------------------------------------------------------------------

async def test_list_techniques(client):
    resp = await client.get("/api/techniques")
    assert resp.status_code == 200
    techs = resp.json()
    assert isinstance(techs, list)
    assert len(techs) >= 1


# ---------------------------------------------------------------------------
# 4. Targets
# ---------------------------------------------------------------------------

async def test_list_targets(client):
    resp = await client.get("/api/operations/test-op-1/targets")
    assert resp.status_code == 200
    targets = resp.json()
    assert len(targets) >= 1
    assert targets[0]["hostname"] == "DC-01"


# ---------------------------------------------------------------------------
# 5. Agents
# ---------------------------------------------------------------------------

async def test_list_agents(client):
    resp = await client.get("/api/operations/test-op-1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 1


# ---------------------------------------------------------------------------
# 6. Facts (empty since no executions)
# ---------------------------------------------------------------------------

async def test_list_facts(client):
    resp = await client.get("/api/operations/test-op-1/facts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 7. C5ISR
# ---------------------------------------------------------------------------

async def test_get_c5isr(client):
    resp = await client.get("/api/operations/test-op-1/c5isr")
    assert resp.status_code == 200
    statuses = resp.json()
    assert len(statuses) == 6  # 6 domains seeded


# ---------------------------------------------------------------------------
# 8. Logs (empty, but endpoint works)
# ---------------------------------------------------------------------------

async def test_get_logs(client):
    resp = await client.get("/api/operations/test-op-1/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# ---------------------------------------------------------------------------
# 9. Recommendations (none yet)
# ---------------------------------------------------------------------------

async def test_get_recommendations_latest(client):
    resp = await client.get("/api/operations/test-op-1/recommendations/latest")
    assert resp.status_code == 200
    # No recommendations seeded, should be null/None
    assert resp.json() is None


# ---------------------------------------------------------------------------
# 10. Operation Summary (composite endpoint)
# ---------------------------------------------------------------------------

async def test_get_operation_summary(client):
    resp = await client.get("/api/operations/test-op-1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "operation" in data
    assert "c5isr" in data
    assert data["operation"]["id"] == "test-op-1"

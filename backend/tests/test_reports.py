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

"""Reports API tests — SPEC-018 tech-debt clearance."""


async def test_report_returns_all_10_sections(client):
    """GET /api/operations/test-op-1/report → 200, JSON has 10 keys."""
    resp = await client.get("/api/operations/test-op-1/report")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "operation", "ooda_timeline", "executions", "facts",
        "recommendations", "c5isr", "logs", "mission_steps",
        "targets", "agents",
    }
    assert set(data.keys()) == expected_keys


async def test_report_operation_section(client):
    """Operation section contains correct ID and codename."""
    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert data["operation"]["id"] == "test-op-1"
    assert data["operation"]["codename"] == "PHANTOM-TEST"


async def test_report_seeded_data_counts(client):
    """With default seed: 1 target, 1 agent, 6 c5isr, 0 for empty tables."""
    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert len(data["targets"]) == 1
    assert len(data["agents"]) == 1
    assert len(data["c5isr"]) == 6
    # These tables have no seed data
    assert len(data["ooda_timeline"]) == 0
    assert len(data["executions"]) == 0
    assert len(data["facts"]) == 0
    assert len(data["recommendations"]) == 0
    assert len(data["logs"]) == 0
    assert len(data["mission_steps"]) == 0


async def test_report_with_log_entries(client, seeded_db):
    """After inserting a log entry, report includes it."""
    await seeded_db.execute(
        "INSERT INTO log_entries (id, operation_id, timestamp, severity, source, message) "
        "VALUES ('log-1', 'test-op-1', '2026-01-01T00:00:00Z', 'info', 'test', 'Hello')"
    )
    await seeded_db.commit()
    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert len(data["logs"]) == 1
    assert data["logs"][0]["message"] == "Hello"


async def test_report_nonexistent_operation(client):
    """GET /api/operations/no-such-op/report → 404."""
    resp = await client.get("/api/operations/no-such-op/report")
    assert resp.status_code == 404

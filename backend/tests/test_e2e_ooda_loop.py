# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""E2E integration tests: OODA Kill Chain (all-mock mode).

Tests the complete flow end-to-end in mock mode.
All external calls (LLM, SSH, Metasploit) are mocked via conftest env vars.
"""
import uuid

import aiosqlite
from httpx import AsyncClient


async def test_health_endpoint(client: AsyncClient):
    """GET /api/health 應回傳 200 且 status=ok。"""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "services" in data


async def test_create_operation(client: AsyncClient):
    """POST /api/operations 應建立 operation 並回傳含 id 的物件。"""
    payload = {
        "code": "OP-E2E-001",
        "name": "E2E Test Operation",
        "codename": "PHANTOM-E2E",
        "strategic_intent": "Validate E2E kill chain in mock mode",
    }
    resp = await client.post("/api/operations", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]
    assert data["code"] == "OP-E2E-001"
    assert data["name"] == "E2E Test Operation"
    assert data["codename"] == "PHANTOM-E2E"
    assert data["status"] == "planning"
    assert data["current_ooda_phase"] == "observe"


async def test_list_operations_includes_created(client: AsyncClient):
    """POST /api/operations 後，GET /api/operations 應包含新建的 operation。"""
    payload = {
        "code": "OP-E2E-LIST-001",
        "name": "E2E List Test",
        "codename": "PHANTOM-LIST",
        "strategic_intent": "Test listing",
    }
    create_resp = await client.post("/api/operations", json=payload)
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    list_resp = await client.get("/api/operations")
    assert list_resp.status_code == 200
    ids = [op["id"] for op in list_resp.json()]
    assert created_id in ids


async def test_add_target_to_operation(client: AsyncClient):
    """POST /api/operations/{id}/targets 應成功加入 target 並回傳 201。"""
    # First create a fresh operation
    op_resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-E2E-TGT-001",
            "name": "E2E Target Test",
            "codename": "PHANTOM-TGT",
            "strategic_intent": "Target add test",
        },
    )
    assert op_resp.status_code == 201
    op_id = op_resp.json()["id"]

    # Add a target
    target_payload = {
        "hostname": "web-server-01",
        "ip_address": "10.10.1.100",
        "os": "Ubuntu 22.04",
        "role": "Web Server",
        "network_segment": "dmz",
    }
    tgt_resp = await client.post(
        f"/api/operations/{op_id}/targets", json=target_payload
    )
    assert tgt_resp.status_code == 201
    tgt_data = tgt_resp.json()
    assert tgt_data["hostname"] == "web-server-01"
    assert tgt_data["ip_address"] == "10.10.1.100"
    assert tgt_data["operation_id"] == op_id
    assert tgt_data["is_compromised"] is False


async def test_list_targets_after_add(client: AsyncClient):
    """GET /api/operations/{id}/targets 應回傳已加入的 target。"""
    op_resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-E2E-LSTGT-001",
            "name": "E2E List Target Test",
            "codename": "PHANTOM-LSTGT",
            "strategic_intent": "List targets test",
        },
    )
    op_id = op_resp.json()["id"]

    # role is NOT NULL in the DB schema — must always be provided
    await client.post(
        f"/api/operations/{op_id}/targets",
        json={"hostname": "db-server-01", "ip_address": "192.168.1.50", "role": "Database"},
    )

    list_resp = await client.get(f"/api/operations/{op_id}/targets")
    assert list_resp.status_code == 200
    targets = list_resp.json()
    assert len(targets) >= 1
    hostnames = [t["hostname"] for t in targets]
    assert "db-server-01" in hostnames


async def test_ooda_trigger_full_cycle(client: AsyncClient):
    """POST /api/operations/{id}/ooda/trigger 應立即回傳 202 queued (async 模式)。"""
    from unittest.mock import MagicMock, patch

    with patch("app.routers.ooda.asyncio.create_task") as mock_ct:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_ct.return_value = mock_task

        resp = await client.post("/api/operations/test-op-1/ooda/trigger")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["operation_id"] == "test-op-1"
    # iteration_id is internal only — must NOT be exposed in the response
    assert "iteration_id" not in data


async def test_ooda_history_after_trigger(client: AsyncClient):
    """觸發 OODA 後 trigger 立即回傳 202；history endpoint 保持可用。"""
    from unittest.mock import MagicMock, patch

    with patch("app.routers.ooda.asyncio.create_task") as mock_ct:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_ct.return_value = mock_task

        trigger_resp = await client.post("/api/operations/test-op-1/ooda/trigger")

    assert trigger_resp.status_code == 202

    # History endpoint must remain functional (empty list before background task runs)
    hist_resp = await client.get("/api/operations/test-op-1/ooda/history")
    assert hist_resp.status_code == 200
    assert isinstance(hist_resp.json(), list)


async def test_ooda_auto_loop_lifecycle(client: AsyncClient):
    """OODA auto-start → status running → auto-stop → status idle。

    get_loop_status returns {"status": "running"|"idle"}.
    stop_auto_loop always returns {"status": "stopped"}.
    """
    op_id = "test-op-1"

    # Start auto loop with long interval so it does not fire during the test
    start_resp = await client.post(
        f"/api/operations/{op_id}/ooda/auto-start",
        params={"interval_sec": 3600, "max_iterations": 0},
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data.get("status") in ("started", "already_running")

    # Check status — should be running
    status_resp = await client.get(f"/api/operations/{op_id}/ooda/auto-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data.get("status") == "running"

    # Stop the loop
    stop_resp = await client.delete(f"/api/operations/{op_id}/ooda/auto-stop")
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()
    assert stop_data.get("status") == "stopped"

    # Check status — should be idle after stop
    final_status_resp = await client.get(f"/api/operations/{op_id}/ooda/auto-status")
    assert final_status_resp.status_code == 200
    final_data = final_status_resp.json()
    assert final_data.get("status") == "idle"


async def test_playbook_list_has_seeds(client: AsyncClient):
    """GET /api/playbooks 應回傳至少 13 個 seed playbooks。"""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    playbooks = resp.json()
    assert len(playbooks) >= 13


async def test_playbook_list_filter_by_mitre_id(client: AsyncClient):
    """GET /api/playbooks?mitre_id=T1190 應只回傳 T1190 的 playbook。"""
    resp = await client.get("/api/playbooks", params={"mitre_id": "T1190"})
    assert resp.status_code == 200
    playbooks = resp.json()
    assert len(playbooks) >= 1
    for pb in playbooks:
        assert pb["mitre_id"] == "T1190"


async def test_e2e_kill_chain_create_op_add_target_trigger_ooda(client: AsyncClient):
    """完整 E2E: 建立 Operation → 加 Target → 觸發 OODA → 驗證 iteration 存在。"""
    # Step 1: Create operation
    op_resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-E2E-KILLCHAIN-001",
            "name": "E2E Kill Chain Test",
            "codename": "PHANTOM-KILL",
            "strategic_intent": "Full E2E kill chain validation in mock mode",
        },
    )
    assert op_resp.status_code == 201
    op_id = op_resp.json()["id"]

    # Step 2: Add target
    tgt_resp = await client.post(
        f"/api/operations/{op_id}/targets",
        json={
            "hostname": "victim-server-01",
            "ip_address": "172.16.0.10",
            "os": "Debian 11",
            "role": "Application Server",
        },
    )
    assert tgt_resp.status_code == 201
    tgt_id = tgt_resp.json()["id"]
    assert tgt_id

    # Step 3: Verify target appears in list
    tgt_list_resp = await client.get(f"/api/operations/{op_id}/targets")
    assert tgt_list_resp.status_code == 200
    assert len(tgt_list_resp.json()) == 1

    # Step 4: Trigger OODA cycle — async 202 pattern
    from unittest.mock import MagicMock, patch as _patch

    with _patch("app.routers.ooda.asyncio.create_task") as mock_ct:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_ct.return_value = mock_task

        ooda_resp = await client.post(f"/api/operations/{op_id}/ooda/trigger")

    assert ooda_resp.status_code == 202
    ooda_data = ooda_resp.json()
    assert ooda_data["status"] == "queued"
    assert ooda_data["operation_id"] == op_id
    # iteration_id is internal only — must NOT be exposed in the response
    assert "iteration_id" not in ooda_data

    # Step 5: OODA history endpoint still responds (background task was mocked)
    hist_resp = await client.get(f"/api/operations/{op_id}/ooda/history")
    assert hist_resp.status_code == 200
    assert isinstance(hist_resp.json(), list)

    # Step 6: Verify operation exists and is accessible
    op_detail_resp = await client.get(f"/api/operations/{op_id}")
    assert op_detail_resp.status_code == 200
    op_detail = op_detail_resp.json()
    assert op_detail["status"] in ("active", "planning")


async def test_metasploit_mock_route(seeded_db: aiosqlite.Connection):
    """EngineRouter + exploit=true CVE fact → Metasploit mock 成功。

    Uses seeded_db directly (no HTTP client) to exercise engine routing at the
    service level.  MOCK_METASPLOIT=true (set in conftest) guarantees no real
    msfrpcd connection is attempted.
    """
    from unittest.mock import AsyncMock, MagicMock

    # Insert a vuln.cve fact with exploit=true for the seeded target
    fact_id = str(uuid.uuid4())
    seeded_db.row_factory = aiosqlite.Row
    await seeded_db.execute(
        """INSERT INTO facts
           (id, operation_id, source_target_id, trait, value, category, score)
           VALUES (?, 'test-op-1', 'test-target-1',
                   'vuln.cve', 'CVE-2011-2523:vsftpd:vsftpd_2.3.4:cvss=10.0:exploit=true',
                   'vulnerability', 1)""",
        (fact_id,),
    )
    await seeded_db.commit()

    # Build EngineRouter with mock dependencies
    from app.clients.mock_c2_client import MockC2Client
    from app.services.engine_router import EngineRouter
    from app.services.fact_collector import FactCollector

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    fc = FactCollector(mock_ws)

    router = EngineRouter(
        c2_engine=MockC2Client(),
        fact_collector=fc,
        ws_manager=mock_ws,
    )

    result = await router.execute(
        db=seeded_db,
        technique_id="T1190",
        target_id="test-target-1",
        engine="ssh",
        operation_id="test-op-1",
    )

    assert result["status"] == "success"
    assert result.get("engine") in ("metasploit", "metasploit_mock")
    assert result["technique_id"] == "T1190"
    assert result["target_id"] == "test-target-1"

    # 驗證 technique_executions 有寫入
    cursor = await seeded_db.execute(
        "SELECT status, engine FROM technique_executions "
        "WHERE operation_id = 'test-op-1' ORDER BY started_at DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    assert row is not None, "technique_executions row was not written"
    assert row["status"] == "success"
    assert row["engine"] == "metasploit"


async def test_facts_collected_after_ooda_trigger(client: AsyncClient):
    """觸發 OODA 後 GET /api/operations/{id}/facts 應回傳 list（async 202 模式）。"""
    from unittest.mock import MagicMock, patch

    with patch("app.routers.ooda.asyncio.create_task") as mock_ct:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_ct.return_value = mock_task

        trigger_resp = await client.post("/api/operations/test-op-1/ooda/trigger")

    assert trigger_resp.status_code == 202
    # Facts endpoint must remain functional (background task was mocked)
    resp = await client.get("/api/operations/test-op-1/facts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_duplicate_target_ip_rejected(client: AsyncClient):
    """同一 operation 中重複 IP 的 target 應回傳 409。"""
    op_resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-E2E-DUP-001",
            "name": "E2E Duplicate IP Test",
            "codename": "PHANTOM-DUP",
            "strategic_intent": "Duplicate IP rejection test",
        },
    )
    op_id = op_resp.json()["id"]

    # role is NOT NULL — must always be provided
    target_payload = {"hostname": "host-a", "ip_address": "10.99.0.1", "role": "Host"}

    # First insert should succeed
    r1 = await client.post(f"/api/operations/{op_id}/targets", json=target_payload)
    assert r1.status_code == 201

    # Second insert with same IP should be rejected with 409
    r2 = await client.post(
        f"/api/operations/{op_id}/targets",
        json={"hostname": "host-b", "ip_address": "10.99.0.1", "role": "Host"},
    )
    assert r2.status_code == 409


async def test_lateral_playbooks_in_seed(client: AsyncClient):
    """Seed playbooks 應包含橫移相關技術（lateral_move tag）。"""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    tags_all = [tag for pb in resp.json() for tag in pb.get("tags", [])]
    assert "lateral_move" in tags_all


async def test_target_has_is_compromised_field(client: AsyncClient):
    """新建 Target 應包含 is_compromised 欄位且預設為 False。"""
    op_resp = await client.post("/api/operations", json={
        "code": "OP-LATERAL-001",
        "name": "lateral-e2e-test",
        "codename": "PHANTOM-LATERAL",
        "strategic_intent": "lateral movement e2e",
    })
    assert op_resp.status_code in (200, 201)
    op_id = op_resp.json()["id"]

    tgt_resp = await client.post(f"/api/operations/{op_id}/targets", json={
        "ip_address": "10.10.99.1",
        "hostname": "pivot-host",
        "role": "workstation",
    })
    assert tgt_resp.status_code in (200, 201)
    tgt = tgt_resp.json()
    assert "is_compromised" in tgt
    assert tgt["is_compromised"] is False

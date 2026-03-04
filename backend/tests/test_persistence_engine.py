# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for PersistenceEngine."""
import pytest


async def test_persistence_probe_disabled_by_default():
    """PERSISTENCE_ENABLED=false 時，probe 直接回傳 {cron: False, systemd: False}，不建立 SSH 連線。"""
    from app.services.persistence_engine import PersistenceEngine
    engine = PersistenceEngine()
    result = await engine.probe("/tmp/test_athena.db", "op-1", "tgt-1", "user:pass@10.0.0.1:22")
    assert result == {"cron": False, "systemd": False}


def test_technique_executors_has_persistence_techniques():
    """TECHNIQUE_EXECUTORS 應包含持久化技術 T1053.003 和 T1543.002。"""
    from app.clients._ssh_common import TECHNIQUE_EXECUTORS, TECHNIQUE_FACT_TRAITS
    assert "T1053.003" in TECHNIQUE_EXECUTORS
    assert "T1543.002" in TECHNIQUE_EXECUTORS
    assert "T1136.001" in TECHNIQUE_EXECUTORS
    assert TECHNIQUE_FACT_TRAITS["T1053.003"] == ["host.persistence"]
    assert TECHNIQUE_FACT_TRAITS["T1543.002"] == ["host.service"]


async def test_persistence_playbooks_in_seed(client):
    """GET /api/playbooks 應包含 persistence tag 的技術。"""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    tags_all = [t for pb in resp.json() for t in pb.get("tags", [])]
    assert "persistence" in tags_all


async def test_persistence_probe_enabled_ssh_failure_is_graceful(monkeypatch):
    """PERSISTENCE_ENABLED=true 但 SSH 連線失敗時，probe 應 graceful 回傳 False，不拋出異常。"""
    monkeypatch.setattr("app.config.settings.PERSISTENCE_ENABLED", True)
    from app.services.persistence_engine import PersistenceEngine
    engine = PersistenceEngine()
    # 傳入格式正確但無法連線的目標
    result = await engine.probe("/tmp/test_athena.db", "op-1", "tgt-1", "user:pass@127.0.0.1:19999")
    assert isinstance(result, dict)
    assert "cron" in result
    assert "systemd" in result

"""Tests for PoC Auto Generation (SPEC-043 B1)."""
import json
import pytest
from app.models.poc_record import PoCRecord


class TestPoCRecord:
    def test_to_json(self):
        poc = PoCRecord(
            technique_id="T1003.001",
            target_ip="192.168.1.10",
            commands_executed=["mimikatz.exe"],
            input_params={"engine": "ssh"},
            output_snippet="NTLM hash found",
            environment={"os": "Windows", "engine": "ssh"},
        )
        raw = poc.to_json()
        data = json.loads(raw)
        assert data["technique_id"] == "T1003.001"
        assert data["target_ip"] == "192.168.1.10"
        assert "mimikatz.exe" in data["commands_executed"]

    def test_from_json(self):
        poc = PoCRecord(
            technique_id="T1190",
            target_ip="10.0.0.1",
            commands_executed=["sqlmap"],
            input_params={},
            output_snippet="injection found",
            environment={"os": "Linux"},
        )
        raw = poc.to_json()
        restored = PoCRecord.from_json(raw)
        assert restored.technique_id == "T1190"
        assert restored.target_ip == "10.0.0.1"

    def test_roundtrip(self):
        poc = PoCRecord(
            technique_id="T1021.004",
            target_ip="172.16.0.5",
            commands_executed=["ssh user@target"],
            input_params={"credential": "user:pass"},
            output_snippet="uid=1000(user)",
            environment={"os": "Linux", "engine": "mcp_ssh"},
            reproducible=True,
        )
        raw = poc.to_json()
        restored = PoCRecord.from_json(raw)
        assert restored.to_json() == raw

    def test_default_timestamp(self):
        poc = PoCRecord(
            technique_id="T1190",
            target_ip="10.0.0.1",
            commands_executed=[],
            input_params={},
            output_snippet="",
            environment={},
        )
        assert poc.timestamp is not None
        assert "T" in poc.timestamp  # ISO 8601 format

    def test_empty_output_not_reproducible(self):
        poc = PoCRecord(
            technique_id="T1190",
            target_ip="10.0.0.1",
            commands_executed=["(mock execution)"],
            input_params={},
            output_snippet="",
            environment={},
            reproducible=False,
        )
        assert poc.reproducible is False

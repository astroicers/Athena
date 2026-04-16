"""SPEC-056 — Multi-Protocol Credential Spray Extension.

Tests that MySQL, PostgreSQL, and FTP protocols are registered in the
protocol map / credential store, correctly matched by InitialAccessEngine,
and that Orient Rules #8/#9 reference the new protocols.
"""

import pytest
import yaml
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"


# ─── T01–T02: YAML data files ───────────────────────────────────────────

class TestProtocolMapYAML:
    """T01: protocol_map.yaml includes mysql/postgresql/ftp entries."""

    @pytest.fixture(autouse=True)
    def _load(self):
        with open(DATA_DIR / "protocol_map.yaml") as f:
            self.protocols = yaml.safe_load(f)["protocols"]

    @pytest.mark.parametrize("port,protocol", [
        (3306, "mysql"),
        (5432, "postgresql"),
        (21, "ftp"),
    ])
    def test_protocol_entry_exists(self, port, protocol):
        match = [p for p in self.protocols if p["port"] == port and p["protocol"] == protocol]
        assert len(match) == 1, f"Expected 1 entry for port={port} protocol={protocol}, got {len(match)}"

    @pytest.mark.parametrize("protocol,expected_tool", [
        ("mysql", "mysql_credential_check"),
        ("postgresql", "postgresql_credential_check"),
        ("ftp", "ftp_credential_check"),
    ])
    def test_mcp_tool_assigned(self, protocol, expected_tool):
        entry = next(p for p in self.protocols if p["protocol"] == protocol)
        assert entry["mcp_tool"] == expected_tool

    @pytest.mark.parametrize("protocol,expected_trait", [
        ("mysql", "credential.mysql"),
        ("postgresql", "credential.postgresql"),
        ("ftp", "credential.ftp"),
    ])
    def test_fact_trait_assigned(self, protocol, expected_trait):
        entry = next(p for p in self.protocols if p["protocol"] == protocol)
        assert entry["fact_trait"] == expected_trait


class TestDefaultCredentialsYAML:
    """T02: default_credentials.yaml includes mysql/postgresql/ftp keys."""

    @pytest.fixture(autouse=True)
    def _load(self):
        with open(DATA_DIR / "default_credentials.yaml") as f:
            self.creds = yaml.safe_load(f)["credentials"]

    @pytest.mark.parametrize("key", ["mysql", "postgresql", "ftp"])
    def test_credential_key_exists(self, key):
        assert key in self.creds, f"Missing credential key: {key}"
        assert len(self.creds[key]) > 0, f"Empty credential list for {key}"

    def test_mysql_root_empty_password_first(self):
        """MySQL root no-password should be the first credential tried."""
        first = self.creds["mysql"][0]
        assert first[0] == "root"
        assert first[1] == ""

    def test_postgresql_postgres_empty_password_first(self):
        """PostgreSQL postgres no-password should be the first credential tried."""
        first = self.creds["postgresql"][0]
        assert first[0] == "postgres"
        assert first[1] == ""

    def test_ftp_anonymous_first(self):
        """FTP anonymous should be the first credential tried."""
        first = self.creds["ftp"][0]
        assert first[0] == "anonymous"


# ─── T03–T05: InitialAccessEngine protocol matching ─────────────────────

class TestProtocolMapMatching:
    """T03-T05: InitialAccessEngine correctly matches new protocols."""

    def test_mysql_service_matches(self):
        from app.services.knowledge_base import get_protocol_map
        pm = get_protocol_map()
        mysql_entry = next((p for p in pm if p["protocol"] == "mysql"), None)
        assert mysql_entry is not None
        services = [{"port": 3306, "service": "mysql"}]
        assert any(
            s["port"] == mysql_entry["port"] and s["service"] in mysql_entry["service_keywords"]
            for s in services
        )

    def test_postgresql_service_matches(self):
        from app.services.knowledge_base import get_protocol_map
        pm = get_protocol_map()
        pg_entry = next((p for p in pm if p["protocol"] == "postgresql"), None)
        assert pg_entry is not None
        services = [{"port": 5432, "service": "postgresql"}]
        assert any(
            s["port"] == pg_entry["port"] and s["service"] in pg_entry["service_keywords"]
            for s in services
        )

    def test_ftp_service_matches(self):
        from app.services.knowledge_base import get_protocol_map
        pm = get_protocol_map()
        ftp_entry = next((p for p in pm if p["protocol"] == "ftp"), None)
        assert ftp_entry is not None
        services = [{"port": 21, "service": "ftp"}]
        assert any(
            s["port"] == ftp_entry["port"] and s["service"] in ftp_entry["service_keywords"]
            for s in services
        )


# ─── T06: Orient prompt includes new protocols ──────────────────────────

class TestOrientPromptProtocols:
    """T06: Orient system prompt mentions MySQL/PostgreSQL/FTP."""

    def test_orient_prompt_mentions_mysql(self):
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "MySQL" in _ORIENT_SYSTEM_PROMPT
        assert "3306" in _ORIENT_SYSTEM_PROMPT

    def test_orient_prompt_mentions_postgresql(self):
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "PostgreSQL" in _ORIENT_SYSTEM_PROMPT
        assert "5432" in _ORIENT_SYSTEM_PROMPT

    def test_orient_prompt_mentions_ftp_in_rule8(self):
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "FTP" in _ORIENT_SYSTEM_PROMPT
        assert "credential.ftp" in _ORIENT_SYSTEM_PROMPT

    def test_orient_prompt_mentions_multi_protocol_pivot(self):
        """Rule #9 should mention SPEC-056 multi-protocol credential pivot."""
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "SPEC-056" in _ORIENT_SYSTEM_PROMPT
        assert "Multi-Protocol" in _ORIENT_SYSTEM_PROMPT

    def test_orient_prompt_mentions_credential_mysql(self):
        """Orient should know to check for credential.mysql absence."""
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "credential.mysql" in _ORIENT_SYSTEM_PROMPT

    def test_orient_prompt_mentions_credential_postgresql(self):
        from app.services.orient_engine import _ORIENT_SYSTEM_PROMPT
        assert "credential.postgresql" in _ORIENT_SYSTEM_PROMPT

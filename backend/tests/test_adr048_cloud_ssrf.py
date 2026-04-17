# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""ADR-048 — Cloud SSRF-to-IMDS Credential Exfiltration.

Tests for Orient Rules #10/#11, engine_router web exploit routing,
and fact_collector cloud trait categorization.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import orient_engine as orient_module
from app.services.engine_router import _is_web_exploit_technique
from app.services.fact_collector import FactCollector
from app.models.enums import FactCategory


# ---------------------------------------------------------------------------
# 2a. Orient Rule Tests (static system prompt assertions)
# ---------------------------------------------------------------------------


class TestOrientRule10:
    """Rule #10: SSRF-to-IMDS Cloud Pivot must be in system prompt."""

    def test_rule10_present_in_system_prompt(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "SSRF-to-IMDS" in prompt or "ssrf" in prompt.lower()

    def test_rule10_mentions_metadata_endpoint(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "169.254.169.254" in prompt

    def test_rule10_mentions_web_http_fetch(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "web_http_fetch" in prompt

    def test_rule10_mentions_web_vuln_ssrf_trigger(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "web.vuln.ssrf" in prompt

    def test_rule10_mentions_mcp_engine(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "web-scanner" in prompt or "web_http_fetch" in prompt


class TestOrientRule11:
    """Rule #11: Cloud Credential Lateral Movement must be in system prompt."""

    def test_rule11_present_in_system_prompt(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "Cloud Credential Lateral Movement" in prompt or "cloud.aws.iam_credential" in prompt

    def test_rule11_mentions_iam_credential_trigger(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "cloud.aws.iam_credential" in prompt

    def test_rule11_mentions_t1078_004(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "T1078.004" in prompt

    def test_rule11_mentions_t1530(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "T1530" in prompt

    def test_rule11_defers_cloud_cli_to_phase2(self) -> None:
        prompt = orient_module._ORIENT_SYSTEM_PROMPT
        assert "Phase 2" in prompt or "phase 2" in prompt.lower()


# ---------------------------------------------------------------------------
# 2b. engine_router Tests
# ---------------------------------------------------------------------------


class TestWebExploitTechniqueDetection:
    """_is_web_exploit_technique helper (ADR-048)."""

    def test_t1190_mcp_is_web_exploit(self) -> None:
        assert _is_web_exploit_technique("T1190", "mcp") is True

    def test_t1078_004_mcp_is_web_exploit(self) -> None:
        assert _is_web_exploit_technique("T1078.004", "mcp") is True

    def test_t1530_mcp_is_web_exploit(self) -> None:
        assert _is_web_exploit_technique("T1530", "mcp") is True

    def test_t1190_metasploit_is_not_web_exploit(self) -> None:
        assert _is_web_exploit_technique("T1190", "metasploit") is False

    def test_t1110_mcp_is_not_web_exploit(self) -> None:
        assert _is_web_exploit_technique("T1110", "mcp") is False


class TestEngineRouterWebExploit:
    """Web exploit via MCP web-scanner routing (ADR-048)."""

    @pytest.mark.asyncio
    async def test_route_web_exploit_to_mcp_web_scanner(self) -> None:
        """engine='mcp' + T1190 + web.vuln.ssrf fact -> web exploit route."""
        from app.clients import ExecutionResult
        from app.services.engine_router import EngineRouter

        mock_mcp = MagicMock()
        mock_mcp.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                execution_id="e1",
                output='{"facts": [{"trait": "cloud.aws.iam_role", "value": "my-role"}]}',
                facts=[{"trait": "cloud.aws.iam_role", "value": "my-role"}],
            )
        )
        mock_fc = MagicMock()
        mock_fc.collect_from_result = AsyncMock(return_value=[])
        mock_ws = MagicMock()
        mock_ws.broadcast = AsyncMock()

        db = MagicMock()
        db.execute = AsyncMock()
        db.fetchrow = AsyncMock(return_value={"mitre_id": "T1190", "c2_ability_id": None})
        # Return a web.vuln.ssrf fact when querying facts
        db.fetch = AsyncMock(return_value=[
            {"trait": "web.vuln.ssrf", "value": "http://target/proxy?url="},
        ])

        with patch("app.services.engine_router.settings") as s:
            s.MCP_ENABLED = True
            s.MOCK_C2_ENGINE = True
            s.EXECUTION_ENGINE = "mcp_ssh"
            s.PERSISTENCE_ENABLED = False
            router = EngineRouter(MagicMock(), mock_fc, mock_ws, mcp_engine=mock_mcp)
            result = await router._execute_web_exploit_via_mcp(
                db, "T1190", "test-target-1", "test-op-1", "ooda-1",
            )

        assert result["status"] == "success"
        assert result["engine"] == "mcp"
        mock_mcp.execute.assert_awaited_once()
        call_args = mock_mcp.execute.call_args
        # The tool should be web-scanner:web_http_fetch
        assert "web-scanner" in str(call_args) or "web_http_fetch" in str(call_args)

    @pytest.mark.asyncio
    async def test_route_t1190_metasploit_unchanged(self, seeded_db) -> None:
        """engine='metasploit' + T1190 + MCP_ENABLED=False -> MetasploitRPCEngine."""
        from app.services.engine_router import EngineRouter

        mock_fc = MagicMock()
        mock_fc.collect_from_result = AsyncMock(return_value=[])
        mock_ws = MagicMock()
        mock_ws.broadcast = AsyncMock()

        # No MCP engine → metasploit fallback
        router = EngineRouter(MagicMock(), mock_fc, mock_ws, mcp_engine=None)

        # Seed an exploitable service fact so metasploit route is taken
        await seeded_db.execute(
            "INSERT INTO facts (id, operation_id, source_target_id, trait, value, category, score) "
            "VALUES ($1, 'test-op-1', 'test-target-1', 'service.open_port', "
            "'21/tcp vsftpd 2.3.4', 'service', 1)",
            str(uuid.uuid4()),
        )

        with patch("app.services.engine_router.settings") as s, \
             patch("app.clients.metasploit_client.MetasploitRPCEngine") as mock_msf_cls:
            s.MCP_ENABLED = False
            s.MOCK_C2_ENGINE = True
            s.EXECUTION_ENGINE = "mcp_ssh"
            s.PERSISTENCE_ENABLED = False
            s.RELAY_IP = ""

            mock_msf = mock_msf_cls.return_value
            async def fake_exploit(target_ip, **kwargs):
                return {"status": "success", "output": "uid=0(root)", "engine": "metasploit"}
            mock_msf.get_exploit_for_service.return_value = fake_exploit

            result = await router._execute_single(
                seeded_db,
                technique_id="T1190",
                target_id="test-target-1",
                engine="metasploit",
                operation_id="test-op-1",
            )

        # Should route to metasploit, not MCP web exploit
        assert result.get("engine") == "metasploit" or "metasploit" in str(result)


# ---------------------------------------------------------------------------
# 2c. fact_collector Tests
# ---------------------------------------------------------------------------


class TestFactCollectorCloudTrait:
    """Cloud trait -> CREDENTIAL category (ADR-048)."""

    def test_cloud_trait_category(self) -> None:
        category = FactCollector._category_from_trait("cloud.aws.iam_credential")
        assert category == FactCategory.CREDENTIAL

    def test_cloud_aws_iam_role_category(self) -> None:
        category = FactCollector._category_from_trait("cloud.aws.iam_role")
        assert category == FactCategory.CREDENTIAL

    def test_cloud_azure_trait_category(self) -> None:
        category = FactCollector._category_from_trait("cloud.azure.managed_identity")
        assert category == FactCategory.CREDENTIAL

    def test_existing_traits_unchanged(self) -> None:
        """Existing trait categories must not change."""
        assert FactCollector._category_from_trait("credential.ssh") == FactCategory.CREDENTIAL
        assert FactCollector._category_from_trait("service.open_port") == FactCategory.SERVICE
        assert FactCollector._category_from_trait("network.host.ip") == FactCategory.NETWORK
        assert FactCollector._category_from_trait("host.os") == FactCategory.HOST

    def test_web_trait_category(self) -> None:
        category = FactCollector._category_from_trait("web.vuln.ssrf")
        assert category == FactCategory.WEB

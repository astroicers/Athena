# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for the api-fuzzer MCP tool server.

Tests cover:
- api_schema_detect: OpenAPI found, GraphQL found, nothing found,
                     introspection disabled, unreachable target
- api_endpoint_enum: schema-based, wordlist-only, auth_required,
                     wildcard filter, max endpoint truncation
- api_auth_test: BOLA detected, IDOR detected, method tampering,
                 no ID in URL, token expired, all secure
- api_param_fuzz: SQLi, CMDi, XSS, overflow detected, no vulns,
                  WAF blocking, empty params, JSON content type
- Dependency: missing ffuf fallback

All external HTTP calls are mocked via httpx mocking (no real network).
"""

import importlib
import importlib.util
import json
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

# ---------------------------------------------------------------------------
# Import api-fuzzer modules using importlib to avoid module-name collisions
# with other tool servers that also have server.py, schema_detector.py, etc.
# ---------------------------------------------------------------------------
_API_FUZZER_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "api-fuzzer"


def _import_tool_module(name: str, alias: str) -> "types.ModuleType":
    """Import a module from the api-fuzzer tool directory with a unique alias."""
    spec = importlib.util.spec_from_file_location(alias, str(_API_FUZZER_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


# Submodules must be loaded first (server.py imports them)
schema_detector = _import_tool_module("schema_detector", "api_fuzzer_schema_detector")
auth_tester = _import_tool_module("auth_tester", "api_fuzzer_auth_tester")
param_fuzzer = _import_tool_module("param_fuzzer", "api_fuzzer_param_fuzzer")

# Now map the names that server.py will import
sys.modules["schema_detector"] = schema_detector
sys.modules["auth_tester"] = auth_tester
sys.modules["param_fuzzer"] = param_fuzzer

api_fuzzer_server = _import_tool_module("server", "api_fuzzer_server")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_result(result: str) -> dict:
    """Parse the JSON string returned by an MCP tool."""
    return json.loads(result)


def _mock_httpx_response(status_code: int = 200, text: str = "", json_data: dict | None = None):
    """Create a mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = text or (json.dumps(json_data) if json_data else "")
    mock_resp.json.return_value = json_data or {}
    mock_resp.headers = {"content-type": "application/json"}
    return mock_resp


def _mock_subprocess(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock for asyncio.create_subprocess_exec."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(
        return_value=(stdout.encode(), stderr.encode())
    )
    mock_proc.returncode = returncode
    mock_proc.kill = MagicMock()
    return mock_proc


# ===========================================================================
# Tool 1: api_schema_detect
# ===========================================================================

class TestApiSchemaDetect:
    """Tests for the api_schema_detect MCP tool."""

    async def test_api_schema_detect_openapi_found(self):
        """OpenAPI spec discovered at a well-known path."""
        mock_resp_200 = _mock_httpx_response(status_code=200, text='{"openapi": "3.0.0"}')
        mock_resp_404 = _mock_httpx_response(status_code=404, text="Not Found")
        mock_resp_gql_404 = _mock_httpx_response(status_code=404, text="Not Found")

        call_count = {"n": 0}
        openapi_path_count = len(schema_detector.OPENAPI_PATHS)

        async def mock_get(url, **kwargs):
            call_count["n"] += 1
            # First OpenAPI path returns 200, rest return 404
            if call_count["n"] == 1:
                return mock_resp_200
            return mock_resp_404

        async def mock_post(url, **kwargs):
            return mock_resp_gql_404

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_schema_detector.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_schema_detect("http://target.com")

        data = _parse_result(result)
        openapi_facts = [f for f in data["facts"] if f["trait"] == "api.schema.openapi"]
        assert len(openapi_facts) >= 1
        assert "200" in openapi_facts[0]["value"]
        assert "error" not in data

    async def test_api_schema_detect_graphql_found(self):
        """GraphQL introspection endpoint discovered and enabled."""
        mock_resp_404 = _mock_httpx_response(status_code=404, text="Not Found")
        mock_resp_gql = _mock_httpx_response(
            status_code=200,
            text='{"data": {"__schema": {"types": [{"name": "Query"}]}}}',
        )

        async def mock_get(url, **kwargs):
            return mock_resp_404

        call_count = {"n": 0}

        async def mock_post(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_resp_gql
            return mock_resp_404

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_schema_detector.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_schema_detect("http://target.com")

        data = _parse_result(result)
        gql_facts = [f for f in data["facts"] if f["trait"] == "api.schema.graphql"]
        assert len(gql_facts) >= 1
        assert "introspection=enabled" in gql_facts[0]["value"]

    async def test_api_schema_detect_nothing_found(self):
        """All probed paths return 404 - empty facts."""
        mock_resp_404 = _mock_httpx_response(status_code=404, text="Not Found")

        async def mock_get(url, **kwargs):
            return mock_resp_404

        async def mock_post(url, **kwargs):
            return mock_resp_404

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_schema_detector.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_schema_detect("http://target.com")

        data = _parse_result(result)
        assert data["facts"] == []
        assert "error" not in data

    async def test_api_schema_detect_graphql_introspection_disabled(self):
        """GraphQL endpoint exists but introspection is disabled."""
        mock_resp_404 = _mock_httpx_response(status_code=404, text="Not Found")
        # GraphQL returns 200 but without __schema in body
        mock_resp_gql_disabled = _mock_httpx_response(
            status_code=200,
            text='{"errors": [{"message": "Introspection is disabled"}]}',
        )

        async def mock_get(url, **kwargs):
            return mock_resp_404

        call_count = {"n": 0}

        async def mock_post(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_resp_gql_disabled
            return mock_resp_404

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_schema_detector.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_schema_detect("http://target.com")

        data = _parse_result(result)
        gql_facts = [f for f in data["facts"] if f["trait"] == "api.schema.graphql"]
        assert len(gql_facts) >= 1
        assert "introspection=disabled" in gql_facts[0]["value"]

    async def test_api_schema_detect_unreachable(self):
        """Target unreachable results in CONNECTION_ERROR."""
        import httpx as real_httpx

        async def mock_get(url, **kwargs):
            raise real_httpx.ConnectError("Connection refused")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_schema_detector.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_schema_detect("http://unreachable.test")

        data = _parse_result(result)
        assert data["error"]["type"] == "CONNECTION_ERROR"


# ===========================================================================
# Tool 2: api_endpoint_enum
# ===========================================================================

class TestApiEndpointEnum:
    """Tests for the api_endpoint_enum MCP tool."""

    async def test_api_endpoint_enum_schema_based(self):
        """Parse OpenAPI spec and extract endpoints."""
        openapi_spec = json.dumps({
            "openapi": "3.0.0",
            "paths": {
                "/users": {"get": {}, "post": {}},
                "/users/{id}": {"get": {}, "put": {}, "delete": {}},
                "/orders": {"get": {}},
            },
        })

        mock_resp = _mock_httpx_response(status_code=200, text=openapi_spec)

        async def mock_get(url, **kwargs):
            return mock_resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # ffuf not installed, wordlist file doesn't exist either -> fallback path
        # but that path also needs the wordlist file. Use a real temp wordlist.
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="test_wl_"
        ) as tf:
            tf.write("# empty\n")
            wordlist_path = tf.name

        with patch("api_fuzzer_server.httpx.AsyncClient", return_value=mock_client), \
             patch("api_fuzzer_server.shutil.which", return_value=None), \
             patch.dict(api_fuzzer_server._WORDLIST_MAP, {"api-common": wordlist_path}):
            result = await api_fuzzer_server.api_endpoint_enum(
                "http://target.com/api",
                schema_url="http://target.com/openapi.json",
            )

        os.unlink(wordlist_path)

        data = _parse_result(result)
        found_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.found"]
        assert len(found_facts) == 6  # 2 + 3 + 1 methods
        assert "error" not in data

    async def test_api_endpoint_enum_wordlist_only(self):
        """ffuf wordlist fuzzing returns discovered endpoints."""
        ffuf_output = json.dumps({
            "results": [
                {"input": {"FUZZ": "users"}, "status": 200, "length": 500},
                {"input": {"FUZZ": "admin"}, "status": 200, "length": 300},
                {"input": {"FUZZ": "health"}, "status": 200, "length": 100},
            ],
        })

        mock_proc = _mock_subprocess(stdout=ffuf_output)

        with patch("api_fuzzer_server.shutil.which", return_value="/usr/local/bin/ffuf"), \
             patch("api_fuzzer_server.Path.exists", return_value=True), \
             patch("api_fuzzer_server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await api_fuzzer_server.api_endpoint_enum("http://target.com/api")

        data = _parse_result(result)
        found_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.found"]
        assert len(found_facts) == 3
        assert "error" not in data

    async def test_api_endpoint_enum_auth_required(self):
        """401/403 responses produce api.endpoint.auth_required facts."""
        ffuf_output = json.dumps({
            "results": [
                {"input": {"FUZZ": "admin"}, "status": 401, "length": 50},
                {"input": {"FUZZ": "settings"}, "status": 403, "length": 60},
                {"input": {"FUZZ": "public"}, "status": 200, "length": 300},
            ],
        })

        mock_proc = _mock_subprocess(stdout=ffuf_output)

        with patch("api_fuzzer_server.shutil.which", return_value="/usr/local/bin/ffuf"), \
             patch("api_fuzzer_server.Path.exists", return_value=True), \
             patch("api_fuzzer_server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await api_fuzzer_server.api_endpoint_enum("http://target.com/api")

        data = _parse_result(result)
        auth_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.auth_required"]
        found_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.found"]
        assert len(auth_facts) == 2
        assert len(found_facts) == 1

    async def test_api_endpoint_enum_wildcard_filter(self):
        """Wildcard responses (>80% same length) are filtered out."""
        # 9 results with same length (90%) and 1 different -> wildcard filter
        results = []
        for i in range(9):
            results.append({"input": {"FUZZ": f"path{i}"}, "status": 200, "length": 500})
        results.append({"input": {"FUZZ": "real"}, "status": 200, "length": 300})

        ffuf_output = json.dumps({"results": results})
        mock_proc = _mock_subprocess(stdout=ffuf_output)

        with patch("api_fuzzer_server.shutil.which", return_value="/usr/local/bin/ffuf"), \
             patch("api_fuzzer_server.Path.exists", return_value=True), \
             patch("api_fuzzer_server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await api_fuzzer_server.api_endpoint_enum("http://target.com/api")

        data = _parse_result(result)
        found_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.found"]
        # Only the one with different length should survive
        assert len(found_facts) == 1
        assert "Wildcard detected" in data["raw_output"]

    async def test_api_endpoint_enum_max_endpoints_truncation(self):
        """Results beyond MAX_ENDPOINTS are truncated."""
        results = []
        for i in range(600):
            results.append({"input": {"FUZZ": f"path{i}"}, "status": 200, "length": i})

        ffuf_output = json.dumps({"results": results})
        mock_proc = _mock_subprocess(stdout=ffuf_output)

        with patch("api_fuzzer_server.shutil.which", return_value="/usr/local/bin/ffuf"), \
             patch("api_fuzzer_server.Path.exists", return_value=True), \
             patch("api_fuzzer_server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(api_fuzzer_server, "MAX_ENDPOINTS", 500):
            result = await api_fuzzer_server.api_endpoint_enum("http://target.com/api")

        data = _parse_result(result)
        assert len(data["facts"]) <= 500
        assert "Truncated" in data["raw_output"]


# ===========================================================================
# Tool 3: api_auth_test
# ===========================================================================

class TestApiAuthTest:
    """Tests for the api_auth_test MCP tool."""

    async def test_api_auth_test_bola_detected(self):
        """Adjacent ID access succeeds, indicating BOLA vulnerability."""
        call_count = {"n": 0}

        async def mock_request(method, url, **kwargs):
            call_count["n"] += 1
            # All requests succeed (simulating BOLA)
            return _mock_httpx_response(status_code=200, text='{"data": "sensitive"}')

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users/42",
                auth_token="valid-token",
            )

        data = _parse_result(result)
        bola_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.bola"]
        assert len(bola_facts) >= 1
        assert "adjacent_id" in bola_facts[0]["value"]

    async def test_api_auth_test_idor_detected(self):
        """Unauthenticated ID access succeeds, indicating IDOR."""
        async def mock_request(method, url, **kwargs):
            return _mock_httpx_response(status_code=200, text='{"data": "sensitive"}')

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users/42",
            )

        data = _parse_result(result)
        idor_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.idor"]
        assert len(idor_facts) >= 1
        assert "no_auth" in idor_facts[0]["value"]

    async def test_api_auth_test_method_tampering(self):
        """Non-standard method returns 200, indicating method tampering."""
        async def mock_request(method, url, **kwargs):
            # Original GET returns 403, but DELETE returns 200
            if method == "DELETE":
                return _mock_httpx_response(status_code=200, text='{"deleted": true}')
            if method == "GET":
                return _mock_httpx_response(status_code=200, text='{"data": "ok"}')
            return _mock_httpx_response(status_code=403, text="Forbidden")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users/42",
                method="GET",
            )

        data = _parse_result(result)
        tamper_facts = [
            f for f in data["facts"]
            if f["trait"] == "api.vuln.auth_bypass" and "method_tamper" in f["value"]
        ]
        assert len(tamper_facts) >= 1
        assert "DELETE" in tamper_facts[0]["value"]

    async def test_api_auth_test_no_id_in_url(self):
        """No numeric ID in URL means BOLA/IDOR tests produce no findings."""
        async def mock_request(method, url, **kwargs):
            return _mock_httpx_response(status_code=200, text='{"data": "ok"}')

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users",
                method="GET",
            )

        data = _parse_result(result)
        bola_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.bola"]
        idor_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.idor"]
        assert len(bola_facts) == 0
        assert len(idor_facts) == 0

    async def test_api_auth_test_token_expired(self):
        """All requests return 401 (expired token), no vulns."""
        async def mock_request(method, url, **kwargs):
            return _mock_httpx_response(status_code=401, text="Unauthorized")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users/42",
                auth_token="expired-token",
            )

        data = _parse_result(result)
        # No vulns should be reported since everything returns 401
        assert len(data["facts"]) == 0
        assert "error" not in data

    async def test_api_auth_test_all_secure(self):
        """All tests return 403/401 — no vulnerabilities, empty facts."""
        async def mock_request(method, url, **kwargs):
            return _mock_httpx_response(status_code=403, text="Forbidden")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_auth_tester.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_auth_test(
                "http://target.com/api/users/42",
                auth_token="valid-token",
            )

        data = _parse_result(result)
        assert len(data["facts"]) == 0
        assert "error" not in data


# ===========================================================================
# Tool 4: api_param_fuzz
# ===========================================================================

class TestApiParamFuzz:
    """Tests for the api_param_fuzz MCP tool."""

    async def test_api_param_fuzz_sqli_detected(self):
        """SQL error string in response body detected as SQLi."""
        async def mock_request(method, url, **kwargs):
            # Check if request contains a SQLi payload
            req_params = kwargs.get("params", {}) or kwargs.get("json", {})
            if req_params:
                for val in req_params.values():
                    if "'" in str(val) or '"' in str(val) or "UNION" in str(val):
                        return _mock_httpx_response(
                            status_code=500,
                            text="You have an error in your SQL syntax near ''",
                        )
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/search",
                method="GET",
                params={"q": "test"},
            )

        data = _parse_result(result)
        injection_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.injection"]
        assert len(injection_facts) >= 1
        assert "sqli" in injection_facts[0]["value"]

    async def test_api_param_fuzz_cmdi_detected(self):
        """Command output in response detected as CMDi."""
        async def mock_request(method, url, **kwargs):
            req_params = kwargs.get("params", {}) or kwargs.get("json", {})
            if req_params:
                for val in req_params.values():
                    if "|" in str(val) or ";" in str(val) or "`" in str(val) or "$(" in str(val):
                        return _mock_httpx_response(
                            status_code=200,
                            text="uid=0(root) gid=0(root) groups=0(root)",
                        )
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/exec",
                method="GET",
                params={"cmd": "test"},
            )

        data = _parse_result(result)
        injection_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.injection"]
        assert len(injection_facts) >= 1
        assert "cmdi" in injection_facts[0]["value"]

    async def test_api_param_fuzz_xss_detected(self):
        """Reflected XSS payload in response body."""
        async def mock_request(method, url, **kwargs):
            req_params = kwargs.get("params", {}) or kwargs.get("json", {})
            if req_params:
                for val in req_params.values():
                    if "<script>" in str(val):
                        return _mock_httpx_response(
                            status_code=200,
                            text=f'<html>Search: {val}</html>',
                        )
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/search",
                method="GET",
                params={"q": "test"},
            )

        data = _parse_result(result)
        injection_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.injection"]
        assert len(injection_facts) >= 1
        assert "xss" in injection_facts[0]["value"]

    async def test_api_param_fuzz_overflow_detected(self):
        """Server 500 error on integer overflow payload."""
        async def mock_request(method, url, **kwargs):
            req_params = kwargs.get("params", {}) or kwargs.get("json", {})
            if req_params:
                for val in req_params.values():
                    if str(val) in ("999999999999999999999", "2147483648", "-2147483649"):
                        return _mock_httpx_response(
                            status_code=500,
                            text="Internal Server Error: integer overflow",
                        )
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/page",
                method="GET",
                params={"page": "1"},
            )

        data = _parse_result(result)
        overflow_facts = [f for f in data["facts"] if f["trait"] == "api.vuln.overflow"]
        assert len(overflow_facts) >= 1
        assert "overflow" in overflow_facts[0]["value"]

    async def test_api_param_fuzz_no_vulns(self):
        """Clean responses - no vulnerabilities found."""
        async def mock_request(method, url, **kwargs):
            return _mock_httpx_response(status_code=200, text='{"result": "OK"}')

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/search",
                method="GET",
                params={"q": "test"},
            )

        data = _parse_result(result)
        assert len(data["facts"]) == 0
        assert "error" not in data

    async def test_api_param_fuzz_waf_blocking(self):
        """All payloads blocked by WAF (403 responses)."""
        async def mock_request(method, url, **kwargs):
            req_params = kwargs.get("params", {}) or kwargs.get("json", {})
            # WAF blocks anything with attack payloads
            if req_params:
                for val in req_params.values():
                    if str(val) != "test":
                        return _mock_httpx_response(status_code=403, text="Forbidden by WAF")
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/search",
                method="GET",
                params={"q": "test"},
            )

        data = _parse_result(result)
        # WAF blocking note should appear
        waf_facts = [f for f in data["facts"] if "waf_blocking" in f.get("value", "")]
        assert len(waf_facts) == 1

    async def test_api_param_fuzz_empty_params(self):
        """Empty params dict results in VALIDATION_ERROR."""
        result = await api_fuzzer_server.api_param_fuzz(
            "http://target.com/api/search",
            method="GET",
            params=None,
        )

        data = _parse_result(result)
        assert data["error"]["type"] == "VALIDATION_ERROR"
        assert "params" in data["error"]["message"]

    async def test_api_param_fuzz_json_content_type(self):
        """POST method sends params as JSON body."""
        captured_kwargs: list[dict] = []

        async def mock_request(method, url, **kwargs):
            captured_kwargs.append(kwargs)
            return _mock_httpx_response(status_code=200, text="OK")

        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_param_fuzzer.httpx.AsyncClient", return_value=mock_client):
            result = await api_fuzzer_server.api_param_fuzz(
                "http://target.com/api/data",
                method="POST",
                params={"name": "test"},
            )

        data = _parse_result(result)
        # Verify POST sends JSON body (json kwarg) not query params
        post_calls = [kw for kw in captured_kwargs if "json" in kw]
        assert len(post_calls) > 0


# ===========================================================================
# Dependency: ffuf missing
# ===========================================================================

class TestDependencyMissing:
    """Tests for graceful handling when ffuf is not installed."""

    async def test_dependency_missing_ffuf(self):
        """When ffuf is missing, falls back to httpx-based enumeration."""
        import tempfile

        # Create a temp wordlist
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="test_wordlist_"
        ) as tf:
            tf.write("users\nadmin\nhealth\n")
            wordlist_path = tf.name

        # Mock httpx responses for fallback
        async def mock_get(url, **kwargs):
            if "users" in url:
                return _mock_httpx_response(status_code=200, text="OK")
            if "admin" in url:
                return _mock_httpx_response(status_code=401, text="Unauthorized")
            return _mock_httpx_response(status_code=404, text="Not Found")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("api_fuzzer_server.shutil.which", return_value=None), \
             patch("api_fuzzer_server.httpx.AsyncClient", return_value=mock_client), \
             patch.dict(api_fuzzer_server._WORDLIST_MAP, {"api-common": wordlist_path}):
            result = await api_fuzzer_server.api_endpoint_enum("http://target.com/api")

        os.unlink(wordlist_path)

        data = _parse_result(result)
        found_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.found"]
        auth_facts = [f for f in data["facts"] if f["trait"] == "api.endpoint.auth_required"]
        assert len(found_facts) >= 1
        assert len(auth_facts) >= 1
        assert "httpx fallback" in data["raw_output"]
        assert "error" not in data


# ===========================================================================
# Module-level tests for schema_detector
# ===========================================================================

class TestSchemaDetectorModule:
    """Tests for schema_detector module functions."""

    def test_parse_openapi_spec_json(self):
        """parse_openapi_spec handles JSON OpenAPI specs."""
        spec = json.dumps({
            "openapi": "3.0.0",
            "paths": {
                "/pets": {"get": {}, "post": {}},
                "/pets/{id}": {"get": {}, "delete": {}},
            },
        })
        endpoints = schema_detector.parse_openapi_spec(spec)
        assert len(endpoints) == 4
        assert "GET /pets" in endpoints
        assert "POST /pets" in endpoints

    def test_parse_openapi_spec_yaml(self):
        """parse_openapi_spec handles YAML OpenAPI specs."""
        import yaml

        spec_dict = {
            "openapi": "3.0.0",
            "paths": {
                "/items": {"get": {}, "post": {}},
            },
        }
        spec = yaml.dump(spec_dict)
        endpoints = schema_detector.parse_openapi_spec(spec)
        assert len(endpoints) == 2
        assert "GET /items" in endpoints
        assert "POST /items" in endpoints

    def test_parse_openapi_spec_invalid(self):
        """parse_openapi_spec returns empty list for invalid input."""
        assert schema_detector.parse_openapi_spec("not valid json or yaml {{{}}}") == []

    def test_parse_openapi_spec_no_paths(self):
        """parse_openapi_spec returns empty list when no paths key."""
        spec = json.dumps({"openapi": "3.0.0", "info": {"title": "Test"}})
        assert schema_detector.parse_openapi_spec(spec) == []


# ===========================================================================
# Module-level tests for auth_tester
# ===========================================================================

class TestAuthTesterModule:
    """Tests for auth_tester module helper functions."""

    def test_extract_id_from_url(self):
        """_extract_id correctly extracts numeric IDs from URLs."""
        assert auth_tester._extract_id("http://api.com/users/42") == 42
        assert auth_tester._extract_id("http://api.com/users/42/orders/99") == 99
        assert auth_tester._extract_id("http://api.com/users") is None
        assert auth_tester._extract_id("http://api.com/users/abc") is None

    def test_replace_id_in_url(self):
        """_replace_id correctly replaces numeric IDs in URLs."""
        assert auth_tester._replace_id(
            "http://api.com/users/42", 42, 43,
        ) == "http://api.com/users/43"
        assert auth_tester._replace_id(
            "http://api.com/users/42/orders/99", 99, 100,
        ) == "http://api.com/users/42/orders/100"


# ===========================================================================
# Module-level tests for param_fuzzer
# ===========================================================================

class TestParamFuzzerModule:
    """Tests for param_fuzzer module functions."""

    def test_load_payloads_sqli(self):
        """load_payloads loads SQLi payloads from file."""
        payloads = param_fuzzer.load_payloads("sqli")
        assert len(payloads) == 10
        assert any("OR" in p for p in payloads)

    def test_load_payloads_cmdi(self):
        """load_payloads loads CMDi payloads from file."""
        payloads = param_fuzzer.load_payloads("cmdi")
        assert len(payloads) == 8

    def test_load_payloads_xss(self):
        """load_payloads loads XSS payloads from file."""
        payloads = param_fuzzer.load_payloads("xss")
        assert len(payloads) == 7

    def test_load_payloads_traversal(self):
        """load_payloads loads path traversal payloads from file."""
        payloads = param_fuzzer.load_payloads("traversal")
        assert len(payloads) == 6

    def test_load_payloads_overflow(self):
        """load_payloads loads overflow payloads from file."""
        payloads = param_fuzzer.load_payloads("overflow")
        assert len(payloads) == 12

    def test_load_payloads_nonexistent(self):
        """load_payloads returns empty list for missing file."""
        payloads = param_fuzzer.load_payloads("nonexistent_category")
        assert payloads == []

    def test_detect_sqli(self):
        """_detect_sqli identifies SQL error patterns."""
        assert param_fuzzer._detect_sqli("You have an error in your SQL syntax")
        assert param_fuzzer._detect_sqli("ORA-12345: invalid identifier")
        assert param_fuzzer._detect_sqli("SQLSTATE[42000]")
        assert not param_fuzzer._detect_sqli("OK")

    def test_detect_cmdi(self):
        """_detect_cmdi identifies command execution output."""
        assert param_fuzzer._detect_cmdi("uid=0(root) gid=0(root)")
        assert param_fuzzer._detect_cmdi("root:x:0:0:root:/root:/bin/bash")
        assert not param_fuzzer._detect_cmdi("OK")

    def test_detect_xss(self):
        """_detect_xss identifies reflected payloads."""
        assert param_fuzzer._detect_xss(
            "<html><script>alert(1)</script></html>",
            "<script>alert(1)</script>",
        )
        assert not param_fuzzer._detect_xss(
            "<html>Safe content</html>",
            "<script>alert(1)</script>",
        )

    def test_detect_traversal(self):
        """_detect_traversal identifies path traversal indicators."""
        assert param_fuzzer._detect_traversal("root:x:0:0:root:/root:/bin/bash")
        assert not param_fuzzer._detect_traversal("OK")

    def test_detect_overflow(self):
        """_detect_overflow identifies overflow indicators."""
        assert param_fuzzer._detect_overflow(500, "Internal Server Error")
        assert param_fuzzer._detect_overflow(200, "integer overflow detected")
        assert not param_fuzzer._detect_overflow(200, "OK")


# ===========================================================================
# Error handling
# ===========================================================================

class TestErrorHandling:
    """Tests for structured error responses."""

    def test_make_error_structure(self):
        """_make_error returns valid JSON with correct structure."""
        result = api_fuzzer_server._make_error("TEST_ERROR", "test message")
        data = json.loads(result)
        assert data["facts"] == []
        assert data["raw_output"] == ""
        assert data["error"]["type"] == "TEST_ERROR"
        assert data["error"]["message"] == "test message"

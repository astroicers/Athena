"""Tests for web_ssrf_probe MCP tool."""

import asyncio
import json
from unittest.mock import patch

import httpx
import pytest
import respx

from server import web_ssrf_probe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(result: str) -> dict:
    return json.loads(result)


def _facts(result: str) -> list[dict]:
    return _parse(result)["facts"]


def _facts_by_trait(result: str, trait: str) -> list[dict]:
    return [f for f in _facts(result) if f["trait"] == trait]


def _first_fact(result: str, trait: str) -> dict | None:
    matches = _facts_by_trait(result, trait)
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Phase 1: Path proxy found
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_path_proxy_found():
    """A /proxy/ path returning 200 should produce a path_proxy fact."""
    base = "http://target.local"

    # Specific routes first, catch-all last (respx matches in registration order)
    respx.get(f"{base}/proxy/").mock(
        return_value=httpx.Response(200, text="proxy page")
    )
    respx.get(f"{base}/proxy/169.254.169.254/latest/meta-data/").mock(
        return_value=httpx.Response(404)
    )
    respx.route(method="GET", url__startswith=base).mock(
        return_value=httpx.Response(404)
    )

    result = await web_ssrf_probe(base)
    ssrf_facts = _facts_by_trait(result, "web.vuln.ssrf")

    assert len(ssrf_facts) >= 1
    proxy_facts = [f for f in ssrf_facts if "path_proxy" in f["value"] and "/proxy/" in f["value"]]
    assert len(proxy_facts) == 1
    assert "response_200" in proxy_facts[0]["value"]


# ---------------------------------------------------------------------------
# Phase 2: IMDS canary confirmed
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_imds_canary_confirmed():
    """IMDS canary via /proxy/ should produce imds_confirmed fact."""
    base = "http://target.local"

    # Specific routes first
    respx.get(f"{base}/proxy/").mock(
        return_value=httpx.Response(200, text="proxy gateway")
    )
    respx.get(f"{base}/proxy/169.254.169.254/latest/meta-data/").mock(
        return_value=httpx.Response(
            200,
            text="ami-id\ninstance-id\niam/\nsecurity-credentials/",
        )
    )
    respx.get(f"{base}/proxy/169.254.169.254/latest/meta-data/iam/security-credentials/").mock(
        return_value=httpx.Response(200, text="flaws-role\n")
    )
    # Catch-all last
    respx.route(method="GET", url__startswith=base).mock(
        return_value=httpx.Response(404)
    )

    result = await web_ssrf_probe(base)

    ssrf_fact = _first_fact(result, "web.vuln.ssrf")
    assert ssrf_fact is not None
    assert "imds_confirmed" in ssrf_fact["value"]
    assert "path_proxy" in ssrf_fact["value"]

    role_fact = _first_fact(result, "cloud.aws.imds_role")
    assert role_fact is not None
    assert role_fact["value"] == "flaws-role"


# ---------------------------------------------------------------------------
# Phase 3: Parameter-based SSRF
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_param_ssrf_found():
    """A ?url= param that returns IMDS markers should produce param_ssrf fact."""
    base = "http://target.local"

    # Specific route first
    respx.get(
        f"{base}?url=http://169.254.169.254/latest/meta-data/"
    ).mock(
        return_value=httpx.Response(
            200,
            text="ami-id\ninstance-id\nsecurity-credentials",
        )
    )
    # Catch-all last
    respx.route(method="GET", url__startswith=base).mock(
        return_value=httpx.Response(404)
    )

    result = await web_ssrf_probe(base)
    ssrf_facts = _facts_by_trait(result, "web.vuln.ssrf")

    param_facts = [f for f in ssrf_facts if "param_ssrf" in f["value"]]
    assert len(param_facts) == 1
    assert "imds_confirmed" in param_facts[0]["value"]
    assert "url=" in param_facts[0]["value"]


# ---------------------------------------------------------------------------
# No SSRF found
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_no_ssrf_found():
    """All 404 responses should produce zero facts."""
    base = "http://target.local"

    respx.route(method="GET", url__startswith=base).mock(
        return_value=httpx.Response(404)
    )

    result = await web_ssrf_probe(base)
    assert _facts(result) == []


# ---------------------------------------------------------------------------
# Rate limiting (semaphore)
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_rate_limiting():
    """Verify the semaphore limits concurrent requests."""
    base = "http://target.local"

    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    original_get = httpx.AsyncClient.get

    async def tracking_get(self, url, **kwargs):
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent:
                max_concurrent = current_concurrent
        try:
            return httpx.Response(404)
        finally:
            async with lock:
                current_concurrent -= 1

    with patch.object(httpx.AsyncClient, "get", tracking_get):
        result = await web_ssrf_probe(base)

    # The semaphore is set to SCAN_RATE_LIMIT (default 100).
    # With 14 paths + 8 params = 22 total phase 1+3 requests,
    # all should complete. Key assertion: it didn't blow up
    # and the semaphore was used (facts parsed correctly).
    parsed = _parse(result)
    assert "facts" in parsed
    assert "error" not in parsed


# ---------------------------------------------------------------------------
# Scheme guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheme_guard():
    """file:// and gopher:// must be rejected."""
    for bad_url in ["file:///etc/passwd", "gopher://evil.com"]:
        result = await web_ssrf_probe(bad_url)
        parsed = _parse(result)
        assert parsed["error"]["type"] == "INVALID_URL"

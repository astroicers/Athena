"""Tests for web_http_fetch MCP tool."""

import json

import httpx
import pytest
import respx

from server import web_http_fetch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(result: str) -> dict:
    return json.loads(result)


def _facts(result: str) -> list[dict]:
    return _parse(result)["facts"]


def _first_fact(result: str, trait: str) -> dict | None:
    for f in _facts(result):
        if f["trait"] == trait:
            return f
    return None


# ---------------------------------------------------------------------------
# Basic fetch
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_basic_url():
    respx.get("http://target.local/test").mock(
        return_value=httpx.Response(200, text="hello world", headers={"content-type": "text/plain"})
    )
    result = await web_http_fetch("http://target.local/test")
    parsed = _parse(result)
    fact = _first_fact(result, "web.http.response")

    assert fact is not None
    assert "200" in fact["value"]
    assert "http://target.local/test" in fact["value"]
    assert parsed["raw_output"] == "hello world"


# ---------------------------------------------------------------------------
# Custom headers
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_with_headers():
    route = respx.get("http://target.local/api")
    route.mock(return_value=httpx.Response(200, text="ok"))

    await web_http_fetch("http://target.local/api", headers={"Authorization": "Bearer xyz"})

    assert route.called
    sent_request = route.calls[0].request
    assert sent_request.headers["Authorization"] == "Bearer xyz"


# ---------------------------------------------------------------------------
# POST with body
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_post_with_body():
    route = respx.post("http://target.local/submit")
    route.mock(return_value=httpx.Response(201, text="created"))

    result = await web_http_fetch(
        "http://target.local/submit",
        method="POST",
        body='{"key": "value"}',
    )
    fact = _first_fact(result, "web.http.response")
    assert "201" in fact["value"]

    sent_request = route.calls[0].request
    assert sent_request.content == b'{"key": "value"}'


# ---------------------------------------------------------------------------
# Redirect following
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_follows_redirect():
    respx.get("http://target.local/old").mock(
        return_value=httpx.Response(
            302,
            headers={"location": "http://target.local/new"},
        )
    )
    respx.get("http://target.local/new").mock(
        return_value=httpx.Response(200, text="final destination")
    )

    result = await web_http_fetch("http://target.local/old", follow_redirects=True)
    parsed = _parse(result)
    assert parsed["raw_output"] == "final destination"


# ---------------------------------------------------------------------------
# Body truncation at 4KB
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_body_truncation():
    big_body = "A" * 8192
    respx.get("http://target.local/big").mock(
        return_value=httpx.Response(200, text=big_body)
    )

    result = await web_http_fetch("http://target.local/big")
    parsed = _parse(result)
    assert len(parsed["raw_output"]) == 4096


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_fetch_timeout():
    respx.get("http://target.local/slow").mock(side_effect=httpx.ReadTimeout("timed out"))

    result = await web_http_fetch("http://target.local/slow")
    parsed = _parse(result)
    assert parsed["error"]["type"] == "TIMEOUT"


# ---------------------------------------------------------------------------
# Scheme guard (file://, gopher://)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_scheme_guard():
    for bad_url in ["file:///etc/passwd", "gopher://evil.com", "ftp://internal"]:
        result = await web_http_fetch(bad_url)
        parsed = _parse(result)
        assert parsed["error"]["type"] == "INVALID_URL"
        assert "scheme" in parsed["error"]["message"].lower()


# ---------------------------------------------------------------------------
# IMDS credential detection
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_imds_credential_detection():
    imds_body = json.dumps({
        "Code": "Success",
        "AccessKeyId": "ASIAXXXXXXXXXEXAMPLE",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "Token": "FwoGZXIvYXdzEBYaDH...",
        "Expiration": "2026-04-17T00:00:00Z",
    })
    respx.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/role").mock(
        return_value=httpx.Response(200, text=imds_body, headers={"content-type": "application/json"})
    )

    result = await web_http_fetch(
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/role"
    )
    facts = _facts(result)

    response_fact = _first_fact(result, "web.http.response")
    cred_fact = _first_fact(result, "cloud.aws.iam_credential")

    assert response_fact is not None
    assert cred_fact is not None
    assert "ASIAXXXXXXXXXEXAMPLE" in cred_fact["value"]
    assert "2026-04-17" in cred_fact["value"]


# ---------------------------------------------------------------------------
# Partial IMDS (no Token) => no detection
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_imds_partial_no_detection():
    partial_body = json.dumps({
        "AccessKeyId": "ASIAXXXXXXXXXEXAMPLE",
    })
    respx.get("http://target.local/partial").mock(
        return_value=httpx.Response(200, text=partial_body)
    )

    result = await web_http_fetch("http://target.local/partial")
    cred_fact = _first_fact(result, "cloud.aws.iam_credential")
    assert cred_fact is None


# ---------------------------------------------------------------------------
# Non-JSON response body
# ---------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_non_json_response():
    respx.get("http://target.local/page").mock(
        return_value=httpx.Response(200, text="<html>hello</html>", headers={"content-type": "text/html"})
    )

    result = await web_http_fetch("http://target.local/page")
    parsed = _parse(result)
    assert parsed["raw_output"] == "<html>hello</html>"
    assert _first_fact(result, "cloud.aws.iam_credential") is None

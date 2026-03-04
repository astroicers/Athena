"""Tests for osint-recon MCP server."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_crtsh_query_returns_subdomains():
    """crtsh_query should return osint.subdomain facts."""
    from server import crtsh_query

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name_value": "www.example.com"},
        {"name_value": "mail.example.com\napi.example.com"},
        {"name_value": "*.example.com"},  # should be filtered
    ]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result_str = await crtsh_query("example.com")

    data = json.loads(result_str)
    assert "facts" in data
    subs = [f["value"] for f in data["facts"] if f["trait"] == "osint.subdomain"]
    assert "www.example.com" in subs
    assert "mail.example.com" in subs
    assert "api.example.com" in subs


async def test_crtsh_query_handles_error():
    """crtsh_query should handle HTTP errors gracefully."""
    from server import crtsh_query

    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result_str = await crtsh_query("example.com")

    data = json.loads(result_str)
    assert data["facts"] == []


async def test_subfinder_query_not_installed():
    """subfinder_query should handle FileNotFoundError gracefully."""
    from server import subfinder_query

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result_str = await subfinder_query("example.com")

    data = json.loads(result_str)
    assert data["facts"] == []
    assert "not available" in data["raw_output"]


async def test_dns_resolve_returns_ips():
    """dns_resolve should return osint.resolved_ip facts."""
    from server import dns_resolve

    mock_answer_a = [MagicMock(__str__=lambda s: "93.184.216.34")]
    mock_answer_aaaa = []

    mock_resolver = MagicMock()

    async def mock_resolve(sub, rdtype):
        if rdtype == "A":
            return mock_answer_a
        raise Exception("no AAAA")

    mock_resolver.resolve = mock_resolve

    with patch("dns.asyncresolver.Resolver", return_value=mock_resolver):
        result_str = await dns_resolve("www.example.com,api.example.com")

    data = json.loads(result_str)
    assert "facts" in data
    ip_facts = [f for f in data["facts"] if f["trait"] == "osint.resolved_ip"]
    assert len(ip_facts) >= 1


async def test_dns_resolve_no_dnspython():
    """dns_resolve should handle missing dnspython."""
    from server import dns_resolve

    import sys
    # Temporarily hide dns module
    with patch.dict(sys.modules, {"dns": None, "dns.asyncresolver": None, "dns.exception": None}):
        # Force reimport
        pass
    # The actual import error handling is inside the function,
    # so we test by patching the import
    with patch("builtins.__import__", side_effect=ImportError("no dns")):
        result_str = await dns_resolve("www.example.com")

    data = json.loads(result_str)
    assert data["facts"] == []

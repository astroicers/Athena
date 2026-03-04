"""Tests for vuln-lookup MCP server."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_banner_to_cpe_known_service():
    """banner_to_cpe should map known services to CPE strings."""
    from server import banner_to_cpe

    result_str = await banner_to_cpe("ssh", "OpenSSH 7.4")
    data = json.loads(result_str)
    assert len(data["facts"]) == 1
    assert data["facts"][0]["trait"] == "vuln.cpe"
    assert data["facts"][0]["value"] == "cpe:/a:openbsd:openssh:7.4"


async def test_banner_to_cpe_unknown_service():
    """banner_to_cpe should return empty facts for unknown services."""
    from server import banner_to_cpe

    result_str = await banner_to_cpe("custom-service", "1.0.0")
    data = json.loads(result_str)
    assert data["facts"] == []


async def test_banner_to_cpe_version_from_banner():
    """banner_to_cpe should extract version from product name in banner."""
    from server import banner_to_cpe

    result_str = await banner_to_cpe("http", "Apache 2.4.6")
    data = json.loads(result_str)
    assert data["facts"][0]["value"] == "cpe:/a:apache:http_server:2.4.6"


async def test_nvd_cve_lookup_returns_facts():
    """nvd_cve_lookup should return vuln.cve facts."""
    from server import nvd_cve_lookup

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2023-1234",
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseScore": 7.5}}
                        ]
                    },
                    "descriptions": [
                        {"lang": "en", "value": "A vulnerability in OpenSSH"}
                    ],
                    "references": [
                        {"url": "https://exploit-db.com/123", "tags": ["Exploit"]}
                    ],
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result_str = await nvd_cve_lookup("cpe:/a:openbsd:openssh:7.4")

    data = json.loads(result_str)
    assert len(data["facts"]) == 1
    fact = data["facts"][0]
    assert fact["trait"] == "vuln.cve"
    assert "CVE-2023-1234" in fact["value"]
    assert "cvss=7.5" in fact["value"]
    assert "exploit=true" in fact["value"]


async def test_nvd_cve_lookup_no_results():
    """nvd_cve_lookup should handle 404 (no CVEs)."""
    from server import nvd_cve_lookup

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result_str = await nvd_cve_lookup("cpe:/a:unknown:unknown:1.0")

    data = json.loads(result_str)
    assert data["facts"] == []


async def test_nvd_cve_lookup_api_error():
    """nvd_cve_lookup should handle API errors gracefully."""
    from server import nvd_cve_lookup

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result_str = await nvd_cve_lookup("cpe:/a:openbsd:openssh:7.4")

    data = json.loads(result_str)
    assert data["facts"] == []
    assert "failed" in data["raw_output"].lower()


async def test_nvd_rate_limiter_exists():
    """Rate limiter function should be importable and callable."""
    from server import _nvd_rate_limit

    assert callable(_nvd_rate_limit)

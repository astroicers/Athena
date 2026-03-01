# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0

"""Unit tests for VulnLookupService — A.3 acceptance criteria."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.vuln_lookup import VulnLookupService, _cvss_to_severity
from app.models.recon import ServiceInfo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_cvss_to_severity():
    assert _cvss_to_severity(9.8) == "critical"
    assert _cvss_to_severity(7.5) == "high"
    assert _cvss_to_severity(5.0) == "medium"
    assert _cvss_to_severity(2.0) == "low"
    assert _cvss_to_severity(0.0) == "info"


def test_banner_to_cpe_openssh():
    svc = VulnLookupService()
    cpe = svc._banner_to_cpe("ssh", "OpenSSH 7.4")
    assert cpe == "cpe:/a:openbsd:openssh:7.4"


def test_banner_to_cpe_apache():
    svc = VulnLookupService()
    cpe = svc._banner_to_cpe("http", "Apache 2.4.6")
    assert cpe == "cpe:/a:apache:http_server:2.4.6"


def test_banner_to_cpe_unknown_returns_none():
    svc = VulnLookupService()
    cpe = svc._banner_to_cpe("unknown_service", "SomeApp 1.0")
    assert cpe is None


def test_banner_to_cpe_version_from_version_string():
    """Service name might not match but version string first token does."""
    svc = VulnLookupService()
    cpe = svc._banner_to_cpe("ftp", "vsftpd 2.3.4")
    assert cpe is not None
    assert "vsftpd" in cpe
    assert "2.3.4" in cpe


async def test_enrich_services_graceful_on_api_failure():
    """NVD API failure → empty findings list (recon scan continues)."""
    db = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchone = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=cursor)
    db.commit = AsyncMock()
    db.row_factory = None

    services = [ServiceInfo(port=22, protocol="tcp", service="ssh", version="OpenSSH 7.4", state="open")]

    with patch("app.services.vuln_lookup.settings") as mock_settings, \
         patch("app.services.vuln_lookup.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.NVD_API_KEY = ""
        mock_settings.NVD_CACHE_TTL_HOURS = 24
        mock_settings.VULN_LOOKUP_ENABLED = True

        # Make _query_nvd raise an exception
        with patch.object(VulnLookupService, "_query_nvd", side_effect=Exception("API timeout")):
            findings = await VulnLookupService().enrich_services(
                db, services, "op-001", "tgt-001"
            )

    # Should return empty list (graceful degradation)
    assert findings == []

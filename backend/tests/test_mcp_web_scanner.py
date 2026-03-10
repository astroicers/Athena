# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for the web-scanner MCP tool server and recon_engine Step 8b integration.

Tests cover:
- web_http_probe: success, failure, WAF detection, default ports
- web_vuln_scan: success, no results, template error, timeout, severity filter
- web_dir_enum: success, sensitive detection, truncation, invalid wordlist
- web_screenshot: success, unreachable target
- Dependency missing (nuclei/httpx not found)
- recon_engine auto-trigger (Step 8b)

All external commands (httpx, nuclei) are mocked via asyncio.create_subprocess_exec.
"""

import json
import sys
import os
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Add the web-scanner tool directory to sys.path so we can import server.py
# ---------------------------------------------------------------------------
_WEB_SCANNER_DIR = str(Path(__file__).resolve().parent.parent.parent / "tools" / "web-scanner")
if _WEB_SCANNER_DIR not in sys.path:
    sys.path.insert(0, _WEB_SCANNER_DIR)

import server as web_scanner_server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_subprocess(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock for asyncio.create_subprocess_exec."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(
        return_value=(stdout.encode(), stderr.encode())
    )
    mock_proc.returncode = returncode
    mock_proc.kill = MagicMock()
    return mock_proc


def _parse_result(result: str) -> dict:
    """Parse the JSON string returned by an MCP tool."""
    return json.loads(result)


def make_mock_db():
    """Return a fully-mocked asyncpg connection."""
    db = AsyncMock()
    db.fetchrow = AsyncMock(return_value=None)
    db.fetch = AsyncMock(return_value=[])
    db.fetchval = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value="INSERT 0 1")
    return db


def make_ip_row(ip: str = "192.168.1.100"):
    """Return a MagicMock that behaves like an asyncpg.Record for ip_address."""
    row = MagicMock()
    row.__getitem__ = lambda self, k: ip if k == "ip_address" else None
    return row


# ===========================================================================
# Tool 1: web_http_probe
# ===========================================================================

class TestWebHttpProbe:
    """Tests for the web_http_probe MCP tool."""

    async def test_probe_success(self):
        """httpx returns JSON lines with service info, technologies, and WAF."""
        httpx_output = "\n".join([
            json.dumps({
                "url": "http://192.168.1.100:80",
                "status_code": 200,
                "title": "Apache Default",
                "webserver": "Apache/2.4.6",
                "tech": ["Apache", "PHP/7.4", "jQuery"],
                "waf": "Cloudflare",
            }),
            json.dumps({
                "url": "https://192.168.1.100:443",
                "status_code": 200,
                "title": "Secure Site",
                "webserver": "nginx/1.18",
                "tech": ["nginx"],
            }),
        ])

        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await web_scanner_server.web_http_probe("192.168.1.100")

        data = _parse_result(result)
        facts = data["facts"]

        # Should have 2 service facts + 3 tech facts (from first) + 1 tech fact (from second) + 1 WAF fact
        service_facts = [f for f in facts if f["trait"] == "web.http.service"]
        tech_facts = [f for f in facts if f["trait"] == "web.http.technology"]
        waf_facts = [f for f in facts if f["trait"] == "web.http.waf"]

        assert len(service_facts) == 2
        assert len(tech_facts) == 4  # Apache, PHP/7.4, jQuery, nginx
        assert len(waf_facts) == 1
        assert "Cloudflare" in waf_facts[0]["value"]
        assert "error" not in data

    async def test_probe_default_ports(self):
        """When no ports specified, defaults to [80, 443, 8080, 8443]."""
        mock_proc = _mock_subprocess(stdout="")

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await web_scanner_server.web_http_probe("192.168.1.100")

        # Verify the command includes default ports
        call_args = mock_exec.call_args[0]
        ports_idx = list(call_args).index("-ports")
        assert call_args[ports_idx + 1] == "80,443,8080,8443"

    async def test_probe_custom_ports(self):
        """Custom ports are passed to httpx correctly."""
        mock_proc = _mock_subprocess(stdout="")

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await web_scanner_server.web_http_probe("192.168.1.100", ports=[8000, 9000])

        call_args = mock_exec.call_args[0]
        ports_idx = list(call_args).index("-ports")
        assert call_args[ports_idx + 1] == "8000,9000"

    async def test_probe_connection_error(self):
        """httpx fails to run → CONNECTION_ERROR."""
        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", side_effect=OSError("No such file")):
            result = await web_scanner_server.web_http_probe("192.168.1.100")

        data = _parse_result(result)
        assert data["error"]["type"] == "CONNECTION_ERROR"

    async def test_probe_timeout(self):
        """httpx times out → TIMEOUT error."""
        import asyncio

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_proc.kill = MagicMock()
            mock_exec.return_value = mock_proc

            result = await web_scanner_server.web_http_probe("192.168.1.100")

        data = _parse_result(result)
        assert data["error"]["type"] == "TIMEOUT"

    async def test_probe_waf_detection(self):
        """WAF field produces web.http.waf fact."""
        httpx_output = json.dumps({
            "url": "http://target.com",
            "status_code": 403,
            "title": "Forbidden",
            "webserver": "",
            "waf": "ModSecurity",
        })
        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await web_scanner_server.web_http_probe("target.com")

        data = _parse_result(result)
        waf_facts = [f for f in data["facts"] if f["trait"] == "web.http.waf"]
        assert len(waf_facts) == 1
        assert "ModSecurity" in waf_facts[0]["value"]

    async def test_probe_httpx_missing(self):
        """httpx binary not found → DEPENDENCY_ERROR."""
        with patch("server.shutil.which", return_value=None):
            result = await web_scanner_server.web_http_probe("192.168.1.100")

        data = _parse_result(result)
        assert data["error"]["type"] == "DEPENDENCY_ERROR"
        assert "httpx" in data["error"]["message"]


# ===========================================================================
# Tool 2: web_vuln_scan
# ===========================================================================

class TestWebVulnScan:
    """Tests for the web_vuln_scan MCP tool."""

    async def test_vuln_scan_success(self):
        """Nuclei finds vulnerabilities → mapped to correct traits."""
        nuclei_output = "\n".join([
            json.dumps({
                "template-id": "sqli-error-based",
                "info": {
                    "name": "SQL Injection Error Based",
                    "severity": "high",
                    "description": "Error-based SQL injection found",
                    "tags": ["sqli", "owasp-top-10"],
                },
                "matched-at": "http://target.com/search?q=test",
            }),
            json.dumps({
                "template-id": "xss-reflected",
                "info": {
                    "name": "Reflected XSS",
                    "severity": "medium",
                    "description": "Reflected cross-site scripting",
                    "tags": ["xss", "owasp-top-10"],
                },
                "matched-at": "http://target.com/page?input=test",
            }),
        ])

        mock_proc = _mock_subprocess(stdout=nuclei_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("server.Path.is_dir", return_value=True):
            result = await web_scanner_server.web_vuln_scan("http://target.com")

        data = _parse_result(result)
        facts = data["facts"]

        assert len(facts) == 2
        assert facts[0]["trait"] == "web.vuln.sqli"
        assert facts[1]["trait"] == "web.vuln.xss"
        assert "sqli-error-based" in facts[0]["value"]
        assert "error" not in data

    async def test_vuln_scan_no_results(self):
        """Nuclei finds nothing → empty facts list."""
        mock_proc = _mock_subprocess(stdout="")

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("server.Path.is_dir", return_value=True):
            result = await web_scanner_server.web_vuln_scan("http://target.com")

        data = _parse_result(result)
        assert data["facts"] == []
        assert "error" not in data

    async def test_vuln_scan_template_error(self):
        """Nuclei reports template error → TEMPLATE_ERROR."""
        mock_proc = _mock_subprocess(
            stdout="",
            stderr="could not find template 'nonexistent'",
        )

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("server.Path.is_dir", return_value=True):
            result = await web_scanner_server.web_vuln_scan(
                "http://target.com", templates=["nonexistent"]
            )

        data = _parse_result(result)
        assert data["error"]["type"] == "TEMPLATE_ERROR"

    async def test_vuln_scan_timeout(self):
        """Nuclei times out → TIMEOUT error."""
        import asyncio

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec") as mock_exec, \
             patch("server.Path.is_dir", return_value=True):
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_proc.kill = MagicMock()
            mock_exec.return_value = mock_proc

            result = await web_scanner_server.web_vuln_scan("http://target.com")

        data = _parse_result(result)
        assert data["error"]["type"] == "TIMEOUT"

    async def test_vuln_scan_severity_filter(self):
        """Severity parameter is passed to nuclei correctly."""
        mock_proc = _mock_subprocess(stdout="")

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec, \
             patch("server.Path.is_dir", return_value=True):
            await web_scanner_server.web_vuln_scan(
                "http://target.com", severity="medium"
            )

        call_args = mock_exec.call_args[0]
        sev_idx = list(call_args).index("-severity")
        assert call_args[sev_idx + 1] == "medium,critical"

    async def test_vuln_scan_nuclei_missing(self):
        """nuclei binary not found → DEPENDENCY_ERROR."""
        with patch("server.shutil.which", return_value=None):
            result = await web_scanner_server.web_vuln_scan("http://target.com")

        data = _parse_result(result)
        assert data["error"]["type"] == "DEPENDENCY_ERROR"
        assert "nuclei" in data["error"]["message"]

    async def test_vuln_scan_tag_mapping(self):
        """All known Nuclei tags map to the correct Athena traits."""
        tag_expectations = {
            "sqli": "web.vuln.sqli",
            "sql-injection": "web.vuln.sqli",
            "xss": "web.vuln.xss",
            "cross-site-scripting": "web.vuln.xss",
            "ssrf": "web.vuln.ssrf",
            "lfi": "web.vuln.path_traversal",
            "rfi": "web.vuln.path_traversal",
            "path-traversal": "web.vuln.path_traversal",
            "rce": "web.vuln.rce",
            "command-injection": "web.vuln.rce",
            "auth-bypass": "web.vuln.auth_bypass",
            "misconfig": "web.vuln.misconfig",
            "exposure": "web.vuln.exposure",
            "deserialization": "web.vuln.deserialization",
        }

        for tag, expected_trait in tag_expectations.items():
            nuclei_output = json.dumps({
                "template-id": f"test-{tag}",
                "info": {
                    "name": f"Test {tag}",
                    "severity": "high",
                    "description": "test",
                    "tags": [tag],
                },
                "matched-at": "http://target.com",
            })
            mock_proc = _mock_subprocess(stdout=nuclei_output)

            with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
                 patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
                 patch("server.Path.is_dir", return_value=True):
                result = await web_scanner_server.web_vuln_scan("http://target.com")

            data = _parse_result(result)
            assert len(data["facts"]) == 1, f"Expected 1 fact for tag '{tag}'"
            assert data["facts"][0]["trait"] == expected_trait, (
                f"Tag '{tag}' should map to '{expected_trait}', "
                f"got '{data['facts'][0]['trait']}'"
            )

    async def test_vuln_scan_unknown_tag_maps_to_generic(self):
        """Unknown Nuclei tags map to web.vuln.generic."""
        nuclei_output = json.dumps({
            "template-id": "test-unknown",
            "info": {
                "name": "Unknown Vuln",
                "severity": "high",
                "description": "test",
                "tags": ["some-unknown-tag"],
            },
            "matched-at": "http://target.com",
        })
        mock_proc = _mock_subprocess(stdout=nuclei_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/nuclei"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("server.Path.is_dir", return_value=True):
            result = await web_scanner_server.web_vuln_scan("http://target.com")

        data = _parse_result(result)
        assert data["facts"][0]["trait"] == "web.vuln.generic"


# ===========================================================================
# Tool 3: web_dir_enum
# ===========================================================================

class TestWebDirEnum:
    """Tests for the web_dir_enum MCP tool."""

    async def test_dir_enum_success(self):
        """httpx discovers directories → web.dir.found facts."""
        httpx_output = "\n".join([
            json.dumps({"url": "http://target.com/admin", "status_code": 200}),
            json.dumps({"url": "http://target.com/login", "status_code": 302}),
            json.dumps({"url": "http://target.com/api", "status_code": 200}),
        ])

        # Create a temp wordlist
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("admin\nlogin\napi\n")
            wordlist_path = tf.name

        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.dict(web_scanner_server._WORDLIST_MAP, {"common": wordlist_path}):
            result = await web_scanner_server.web_dir_enum("http://target.com")

        os.unlink(wordlist_path)

        data = _parse_result(result)
        # admin is sensitive (matches "admin" pattern), others are regular
        sensitive = [f for f in data["facts"] if f["trait"] == "web.dir.sensitive"]
        found = [f for f in data["facts"] if f["trait"] == "web.dir.found"]

        assert len(sensitive) >= 1  # admin is sensitive
        assert len(found) >= 1
        assert "error" not in data

    async def test_dir_enum_sensitive_detection(self):
        """Sensitive paths (.git/, .env, .bak) are flagged as web.dir.sensitive."""
        httpx_output = "\n".join([
            json.dumps({"url": "http://target.com/.git/config", "status_code": 200}),
            json.dumps({"url": "http://target.com/.env", "status_code": 200}),
            json.dumps({"url": "http://target.com/backup.bak", "status_code": 200}),
            json.dumps({"url": "http://target.com/index.html", "status_code": 200}),
        ])

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("test\n")
            wordlist_path = tf.name

        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.dict(web_scanner_server._WORDLIST_MAP, {"common": wordlist_path}):
            result = await web_scanner_server.web_dir_enum("http://target.com")

        os.unlink(wordlist_path)

        data = _parse_result(result)
        sensitive = [f for f in data["facts"] if f["trait"] == "web.dir.sensitive"]
        found = [f for f in data["facts"] if f["trait"] == "web.dir.found"]

        assert len(sensitive) == 3  # .git/config, .env, .bak
        assert len(found) == 1  # index.html

    async def test_dir_enum_truncation(self):
        """Results are capped at 500 total, with sensitive paths prioritized."""
        # Generate 600 results
        lines = []
        for i in range(600):
            lines.append(json.dumps({
                "url": f"http://target.com/page{i}",
                "status_code": 200,
            }))
        httpx_output = "\n".join(lines)

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("test\n")
            wordlist_path = tf.name

        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.dict(web_scanner_server._WORDLIST_MAP, {"common": wordlist_path}):
            result = await web_scanner_server.web_dir_enum("http://target.com")

        os.unlink(wordlist_path)

        data = _parse_result(result)
        assert len(data["facts"]) <= 500

    async def test_dir_enum_invalid_wordlist(self):
        """Unknown wordlist name → INVALID_WORDLIST error."""
        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"):
            result = await web_scanner_server.web_dir_enum(
                "http://target.com", wordlist="nonexistent"
            )

        data = _parse_result(result)
        assert data["error"]["type"] == "INVALID_WORDLIST"

    async def test_dir_enum_wordlist_file_missing(self):
        """Wordlist file does not exist → INVALID_WORDLIST error."""
        with patch("server.shutil.which", return_value="/usr/local/bin/httpx"), \
             patch.dict(web_scanner_server._WORDLIST_MAP, {"common": "/nonexistent/path.txt"}):
            result = await web_scanner_server.web_dir_enum("http://target.com")

        data = _parse_result(result)
        assert data["error"]["type"] == "INVALID_WORDLIST"

    async def test_dir_enum_httpx_missing(self):
        """httpx binary not found → DEPENDENCY_ERROR."""
        with patch("server.shutil.which", return_value=None):
            result = await web_scanner_server.web_dir_enum("http://target.com")

        data = _parse_result(result)
        assert data["error"]["type"] == "DEPENDENCY_ERROR"


# ===========================================================================
# Tool 4: web_screenshot
# ===========================================================================

class TestWebScreenshot:
    """Tests for the web_screenshot MCP tool."""

    async def test_screenshot_with_chrome(self):
        """Chrome available → screenshot mode used, web.screenshot fact produced."""
        httpx_output = json.dumps({
            "url": "http://target.com",
            "status_code": 200,
        })
        mock_proc = _mock_subprocess(stdout=httpx_output)

        # Create a fake screenshot file
        import tempfile as _tempfile
        screenshot_dir = _tempfile.mkdtemp()
        fake_png = Path(screenshot_dir) / "screenshot.png"
        fake_png.write_bytes(b"fake png data")

        with patch("server.shutil.which", side_effect=lambda x: {
                 "httpx": "/usr/local/bin/httpx",
                 "chromium": "/usr/bin/chromium",
             }.get(x)), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("tempfile.mkdtemp", return_value=screenshot_dir):
            result = await web_scanner_server.web_screenshot("http://target.com")

        data = _parse_result(result)
        assert len(data["facts"]) == 1
        assert data["facts"][0]["trait"] == "web.screenshot"
        assert "http://target.com" in data["facts"][0]["value"]
        assert "error" not in data

        # Cleanup
        fake_png.unlink()
        Path(screenshot_dir).rmdir()

    async def test_screenshot_fallback_title(self):
        """No Chrome → falls back to title-only mode."""
        httpx_output = json.dumps({
            "url": "http://target.com",
            "status_code": 200,
            "title": "Example Web App",
        })
        mock_proc = _mock_subprocess(stdout=httpx_output)

        with patch("server.shutil.which", side_effect=lambda x: {
                 "httpx": "/usr/local/bin/httpx",
             }.get(x)), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await web_scanner_server.web_screenshot("http://target.com")

        data = _parse_result(result)
        assert len(data["facts"]) == 1
        assert data["facts"][0]["trait"] == "web.screenshot"
        assert "title:Example Web App" in data["facts"][0]["value"]

    async def test_screenshot_unreachable(self):
        """httpx returns no output for unreachable target → CONNECTION_ERROR."""
        mock_proc = _mock_subprocess(stdout="")

        with patch("server.shutil.which", side_effect=lambda x: {
                 "httpx": "/usr/local/bin/httpx",
             }.get(x)), \
             patch("server.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await web_scanner_server.web_screenshot("http://unreachable.invalid")

        data = _parse_result(result)
        assert data["error"]["type"] == "CONNECTION_ERROR"

    async def test_screenshot_httpx_missing(self):
        """httpx binary not found → DEPENDENCY_ERROR."""
        with patch("server.shutil.which", return_value=None):
            result = await web_scanner_server.web_screenshot("http://target.com")

        data = _parse_result(result)
        assert data["error"]["type"] == "DEPENDENCY_ERROR"


# ===========================================================================
# Helper function tests
# ===========================================================================

class TestHelpers:
    """Tests for internal helper functions."""

    def test_make_error_structure(self):
        """_make_error returns valid JSON with correct structure."""
        result = web_scanner_server._make_error("TEST_ERROR", "test message")
        data = json.loads(result)
        assert data["facts"] == []
        assert data["raw_output"] == ""
        assert data["error"]["type"] == "TEST_ERROR"
        assert data["error"]["message"] == "test message"

    def test_is_sensitive_path(self):
        """_is_sensitive_path correctly identifies sensitive files."""
        assert web_scanner_server._is_sensitive_path("/.git/config") is True
        assert web_scanner_server._is_sensitive_path("/.env") is True
        assert web_scanner_server._is_sensitive_path("/backup.bak") is True
        assert web_scanner_server._is_sensitive_path("/.htpasswd") is True
        assert web_scanner_server._is_sensitive_path("/wp-config.php") is True
        assert web_scanner_server._is_sensitive_path("/index.html") is False
        assert web_scanner_server._is_sensitive_path("/api/users") is False

    def test_map_nuclei_tags_to_trait(self):
        """_map_nuclei_tags_to_trait returns correct traits."""
        assert web_scanner_server._map_nuclei_tags_to_trait(["sqli"]) == "web.vuln.sqli"
        assert web_scanner_server._map_nuclei_tags_to_trait(["xss"]) == "web.vuln.xss"
        assert web_scanner_server._map_nuclei_tags_to_trait(["unknown"]) == "web.vuln.generic"
        assert web_scanner_server._map_nuclei_tags_to_trait([]) == "web.vuln.generic"
        # First matching tag wins
        assert web_scanner_server._map_nuclei_tags_to_trait(["sqli", "xss"]) == "web.vuln.sqli"


# ===========================================================================
# recon_engine Step 8b integration
# ===========================================================================

class TestReconEngineStep8b:
    """Tests for the recon_engine Step 8b web reconnaissance integration."""

    async def test_step_8b_triggers_for_http_services(self):
        """When MCP web-scanner is connected and http services found, Step 8b triggers."""
        from app.services.recon_engine import ReconEngine
        from app.models.recon import ServiceInfo

        row = make_ip_row("192.168.1.100")
        db = make_mock_db()
        # First fetchrow → ip_row (target lookup), subsequent → None (no engagement)
        db.fetchrow = AsyncMock(side_effect=[row, None])

        mock_mcp_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "service.open_port", "value": "80/tcp/http/Apache_2.4.6"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
            "is_error": False,
        }

        web_probe_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "web.http.service", "value": "http://192.168.1.100:80|200|Apache|Apache/2.4.6"},
                            {"trait": "web.http.technology", "value": "http://192.168.1.100:80|Apache"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
            "is_error": False,
        }

        mock_manager = MagicMock()
        mock_manager.is_connected = MagicMock(side_effect=lambda name: {
            "nmap-scanner": True,
            "web-scanner": True,
        }.get(name, False))

        # call_tool returns nmap result first, then web probe result
        mock_manager.call_tool = AsyncMock(
            side_effect=[mock_mcp_result, web_probe_result]
        )

        with patch("app.services.recon_engine.settings") as mock_settings, \
             patch("app.services.recon_engine.ws_manager") as mock_ws, \
             patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_manager):

            mock_settings.MOCK_C2_ENGINE = False
            mock_settings.MCP_ENABLED = True
            mock_settings.NMAP_SCAN_TIMEOUT_SEC = 60
            mock_settings.VULN_LOOKUP_ENABLED = False
            mock_ws.broadcast = AsyncMock()

            result = await ReconEngine().scan(db, "op-001", "tgt-001")

        # Verify web probe was called
        assert mock_manager.call_tool.call_count == 2
        web_call = mock_manager.call_tool.call_args_list[1]
        assert web_call[0][0] == "web-scanner"
        assert web_call[0][1] == "web_http_probe"

    async def test_step_8b_skips_when_no_http_services(self):
        """Step 8b skips when no HTTP services found by nmap."""
        from app.services.recon_engine import ReconEngine

        row = make_ip_row("192.168.1.100")
        db = make_mock_db()
        db.fetchrow = AsyncMock(side_effect=[row, None])

        # nmap result with only SSH (no http)
        mock_mcp_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "service.open_port", "value": "22/tcp/ssh/OpenSSH_7.4"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
            "is_error": False,
        }

        mock_manager = MagicMock()
        mock_manager.is_connected = MagicMock(return_value=True)
        mock_manager.call_tool = AsyncMock(return_value=mock_mcp_result)

        with patch("app.services.recon_engine.settings") as mock_settings, \
             patch("app.services.recon_engine.ws_manager") as mock_ws, \
             patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_manager):

            mock_settings.MOCK_C2_ENGINE = False
            mock_settings.MCP_ENABLED = True
            mock_settings.NMAP_SCAN_TIMEOUT_SEC = 60
            mock_settings.VULN_LOOKUP_ENABLED = False
            mock_ws.broadcast = AsyncMock()

            result = await ReconEngine().scan(db, "op-001", "tgt-001")

        # Only nmap call, no web-scanner call
        assert mock_manager.call_tool.call_count == 1
        assert mock_manager.call_tool.call_args[0][0] == "nmap-scanner"

    async def test_step_8b_graceful_failure(self):
        """Step 8b failure does not break the overall scan."""
        from app.services.recon_engine import ReconEngine

        row = make_ip_row("192.168.1.100")
        db = make_mock_db()
        db.fetchrow = AsyncMock(side_effect=[row, None])

        # nmap result with http service
        mock_mcp_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "service.open_port", "value": "80/tcp/http/Apache_2.4.6"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
            "is_error": False,
        }

        mock_manager = MagicMock()
        mock_manager.is_connected = MagicMock(side_effect=lambda name: {
            "nmap-scanner": True,
            "web-scanner": True,
        }.get(name, False))

        # First call (nmap) succeeds, second call (web probe) fails
        mock_manager.call_tool = AsyncMock(
            side_effect=[mock_mcp_result, ConnectionError("web-scanner down")]
        )

        with patch("app.services.recon_engine.settings") as mock_settings, \
             patch("app.services.recon_engine.ws_manager") as mock_ws, \
             patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_manager):

            mock_settings.MOCK_C2_ENGINE = False
            mock_settings.MCP_ENABLED = True
            mock_settings.NMAP_SCAN_TIMEOUT_SEC = 60
            mock_settings.VULN_LOOKUP_ENABLED = False
            mock_ws.broadcast = AsyncMock()

            # Should NOT raise, even though web-scanner call failed
            result = await ReconEngine().scan(db, "op-001", "tgt-001")

        assert result is not None
        assert result.ip_address == "192.168.1.100"

    async def test_step_8b_skips_when_web_scanner_not_connected(self):
        """Step 8b skips when web-scanner is not connected."""
        from app.services.recon_engine import ReconEngine

        row = make_ip_row("192.168.1.100")
        db = make_mock_db()
        db.fetchrow = AsyncMock(side_effect=[row, None])

        mock_mcp_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "service.open_port", "value": "80/tcp/http/Apache_2.4.6"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
            "is_error": False,
        }

        mock_manager = MagicMock()
        # nmap connected but web-scanner not connected
        mock_manager.is_connected = MagicMock(side_effect=lambda name: {
            "nmap-scanner": True,
            "web-scanner": False,
        }.get(name, False))
        mock_manager.call_tool = AsyncMock(return_value=mock_mcp_result)

        with patch("app.services.recon_engine.settings") as mock_settings, \
             patch("app.services.recon_engine.ws_manager") as mock_ws, \
             patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_manager):

            mock_settings.MOCK_C2_ENGINE = False
            mock_settings.MCP_ENABLED = True
            mock_settings.NMAP_SCAN_TIMEOUT_SEC = 60
            mock_settings.VULN_LOOKUP_ENABLED = False
            mock_ws.broadcast = AsyncMock()

            result = await ReconEngine().scan(db, "op-001", "tgt-001")

        # Only nmap call, no web-scanner call
        assert mock_manager.call_tool.call_count == 1

    async def test_write_web_facts_parses_probe_result(self):
        """_write_web_facts correctly parses MCP probe result and inserts facts."""
        from app.services.recon_engine import ReconEngine

        db = make_mock_db()

        probe_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "web.http.service", "value": "http://target:80|200|Title|Apache"},
                            {"trait": "web.http.technology", "value": "http://target:80|PHP"},
                            {"trait": "web.http.waf", "value": "http://target:80|Cloudflare"},
                        ],
                        "raw_output": "raw",
                    }),
                }
            ],
        }

        with patch("app.services.recon_engine.ws_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()

            count = await ReconEngine()._write_web_facts(
                db=db,
                operation_id="op-001",
                target_id="tgt-001",
                probe_result=probe_result,
            )

        assert count == 3
        # Verify db.execute was called for each fact INSERT
        insert_calls = [
            call for call in db.execute.call_args_list
            if call[0] and "INSERT" in str(call[0][0])
        ]
        assert len(insert_calls) == 3

    async def test_write_web_facts_waf_category(self):
        """WAF facts get category 'defense', vuln facts get 'vulnerability'."""
        from app.services.recon_engine import ReconEngine

        db = make_mock_db()
        captured_params: list = []

        async def capture_execute(sql, *args):
            if args:
                captured_params.append(args)
            return "INSERT 0 1"

        db.execute = AsyncMock(side_effect=capture_execute)

        probe_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "facts": [
                            {"trait": "web.http.waf", "value": "http://target|Cloudflare"},
                            {"trait": "web.vuln.sqli", "value": "http://target|sqli-test|high|SQLi|desc"},
                            {"trait": "web.http.service", "value": "http://target|200|Title|Server"},
                        ],
                        "raw_output": "",
                    }),
                }
            ],
        }

        with patch("app.services.recon_engine.ws_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()

            await ReconEngine()._write_web_facts(
                db=db,
                operation_id="op-001",
                target_id="tgt-001",
                probe_result=probe_result,
            )

        # Check categories in INSERT params
        # params format: (fact_id, trait, value, category, target_id, operation_id, now)
        categories = [p[3] for p in captured_params if len(p) >= 4]
        assert "defense" in categories  # WAF
        assert "vulnerability" in categories  # vuln
        assert "web" in categories  # service

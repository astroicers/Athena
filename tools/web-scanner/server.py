"""web-scanner MCP Server for Athena.

Exposes HTTP probing, vulnerability scanning, directory enumeration,
and screenshotting as MCP tools. Wraps httpx-toolkit and Nuclei.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

# Allow Docker internal network hostnames (mcp-web-scanner, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-web-scanner", transport_security=_security)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
SCAN_RATE_LIMIT = int(os.environ.get("SCAN_RATE_LIMIT", "100"))
SCAN_TIMEOUT_SEC = int(os.environ.get("SCAN_TIMEOUT_SEC", "300"))
NUCLEI_TEMPLATES_DIR = os.environ.get("NUCLEI_TEMPLATES_DIR", "/opt/nuclei-templates")

_DEFAULT_HTTP_PORTS = [80, 443, 8080, 8443]
_DEFAULT_VULN_TEMPLATES = ["owasp-top-10"]
_DEFAULT_EXTENSIONS = ["php", "html", "js", "txt", "bak"]

_WORDLIST_MAP = {
    "common": "/opt/wordlists/common.txt",
    "small": "/opt/wordlists/small.txt",
    "large": "/opt/wordlists/large.txt",
}

_SENSITIVE_PATTERNS = [
    ".git/", ".git/config", ".env", ".bak", ".old", ".orig",
    ".sql", ".dump", ".tar", ".gz", ".zip",
    "wp-config.php", "config.php", "config.inc.php",
    ".htpasswd", ".htaccess", "web.config",
    "backup", "admin", "phpmyadmin",
    ".DS_Store", "Thumbs.db",
    ".svn/", ".hg/",
]

# Nuclei tag → Athena fact trait mapping
_VULN_TAG_MAP: dict[str, str] = {
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


def _make_error(error_type: str, message: str) -> str:
    """Return a structured JSON error response."""
    return json.dumps({
        "facts": [],
        "raw_output": "",
        "error": {"type": error_type, "message": message},
    })


def _map_nuclei_tags_to_trait(tags: list[str]) -> str:
    """Map Nuclei template tags to an Athena fact trait."""
    for tag in tags:
        tag_lower = tag.lower().strip()
        if tag_lower in _VULN_TAG_MAP:
            return _VULN_TAG_MAP[tag_lower]
    return "web.vuln.generic"


def _is_sensitive_path(path: str) -> bool:
    """Check if a discovered path matches sensitive patterns."""
    path_lower = path.lower()
    return any(pattern in path_lower for pattern in _SENSITIVE_PATTERNS)


async def _run_command(
    cmd: list[str], timeout: int | None = None
) -> tuple[str, str, int]:
    """Run a command via asyncio subprocess. Returns (stdout, stderr, returncode)."""
    effective_timeout = timeout or SCAN_TIMEOUT_SEC
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=effective_timeout
        )
        return (
            stdout.decode(errors="replace"),
            stderr.decode(errors="replace"),
            proc.returncode or 0,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Tool 1: HTTP Probe
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_http_probe(target: str, ports: list[int] | None = None) -> str:
    """HTTP probe + tech fingerprinting + WAF detection for a target.

    Args:
        target: IP address, hostname, or URL to probe.
        ports: List of ports to probe. Defaults to [80, 443, 8080, 8443].

    Returns:
        JSON string with Athena-compatible facts:
        - web.http.service: "{url}|{status}|{title}|{server}"
        - web.http.technology: "{url}|{tech}"
        - web.http.waf: "{url}|{waf_name}"
    """
    if not shutil.which("httpx"):
        return _make_error("DEPENDENCY_ERROR", "httpx binary not found in PATH")

    effective_ports = ports or _DEFAULT_HTTP_PORTS
    ports_str = ",".join(str(p) for p in effective_ports)

    cmd = [
        "httpx",
        "-target", target,
        "-ports", ports_str,
        "-json",
        "-tech-detect",
        "-status-code",
        "-title",
        "-web-server",
        "-follow-redirects",
        "-silent",
    ]

    try:
        stdout, stderr, returncode = await _run_command(cmd)
    except asyncio.TimeoutError:
        return _make_error("TIMEOUT", f"httpx probe timed out after {SCAN_TIMEOUT_SEC}s")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Failed to run httpx: {exc}")

    facts: list[dict[str, str]] = []
    lines = [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        url = data.get("url", data.get("input", target))
        status = data.get("status_code", data.get("status-code", 0))
        title = data.get("title", "")
        server = data.get("webserver", data.get("web-server", ""))

        # HTTP service fact
        facts.append({
            "trait": "web.http.service",
            "value": f"{url}|{status}|{title}|{server}",
        })

        # Technology facts
        techs = data.get("tech", data.get("technologies", []))
        if isinstance(techs, list):
            for tech in techs:
                facts.append({
                    "trait": "web.http.technology",
                    "value": f"{url}|{tech}",
                })

        # WAF detection
        waf = data.get("waf", data.get("waf_name", ""))
        if waf:
            facts.append({
                "trait": "web.http.waf",
                "value": f"{url}|{waf}",
            })

    return json.dumps({
        "facts": facts,
        "raw_output": stdout[:2000],
    })


# ---------------------------------------------------------------------------
# Tool 2: Vulnerability Scan
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_vuln_scan(
    url: str,
    templates: list[str] | None = None,
    severity: str = "high",
) -> str:
    """OWASP Top 10 vulnerability scanning via Nuclei.

    Args:
        url: Target URL to scan (e.g. http://example.com).
        templates: Nuclei template tags to use. Defaults to ["owasp-top-10"].
        severity: Minimum severity filter. Defaults to "high".

    Returns:
        JSON string with Athena-compatible facts:
        - web.vuln.<category>: "{url}|{template_id}|{severity}|{name}|{description}"
    """
    if not shutil.which("nuclei"):
        return _make_error("DEPENDENCY_ERROR", "nuclei binary not found in PATH")

    effective_templates = templates or _DEFAULT_VULN_TEMPLATES
    tags_str = ",".join(effective_templates)
    severity_str = f"{severity},critical" if severity != "critical" else "critical"

    cmd = [
        "nuclei",
        "-u", url,
        "-tags", tags_str,
        "-severity", severity_str,
        "-json",
        "-silent",
        "-rate-limit", str(SCAN_RATE_LIMIT),
        "-timeout", str(SCAN_TIMEOUT_SEC),
    ]

    # Add templates directory if it exists
    templates_dir = Path(NUCLEI_TEMPLATES_DIR)
    if templates_dir.is_dir():
        cmd.extend(["-ud", str(templates_dir)])

    try:
        stdout, stderr, returncode = await _run_command(cmd)
    except asyncio.TimeoutError:
        return _make_error("TIMEOUT", f"nuclei scan timed out after {SCAN_TIMEOUT_SEC}s")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Failed to run nuclei: {exc}")

    # Check for template errors
    if "could not find template" in stderr.lower() or "no templates found" in stderr.lower():
        return _make_error("TEMPLATE_ERROR", f"Nuclei template error: {stderr[:500]}")

    facts: list[dict[str, str]] = []
    lines = [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        template_id = data.get("template-id", data.get("templateID", "unknown"))
        vuln_name = data.get("info", {}).get("name", data.get("name", ""))
        vuln_severity = data.get("info", {}).get("severity", data.get("severity", "unknown"))
        vuln_desc = data.get("info", {}).get("description", "")
        matched_url = data.get("matched-at", data.get("matched", url))
        tags = data.get("info", {}).get("tags", data.get("tags", []))

        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        trait = _map_nuclei_tags_to_trait(tags)

        facts.append({
            "trait": trait,
            "value": f"{matched_url}|{template_id}|{vuln_severity}|{vuln_name}|{vuln_desc[:200]}",
        })

    return json.dumps({
        "facts": facts,
        "raw_output": stdout[:2000],
    })


# ---------------------------------------------------------------------------
# Tool 3: Directory Enumeration
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_dir_enum(
    url: str,
    wordlist: str = "common",
    extensions: list[str] | None = None,
) -> str:
    """Directory and file enumeration via httpx.

    Args:
        url: Base URL to enumerate (e.g. http://example.com).
        wordlist: Wordlist size: "common", "small", or "large".
        extensions: File extensions to test. Defaults to ["php", "html", "js", "txt", "bak"].

    Returns:
        JSON string with Athena-compatible facts:
        - web.dir.found: "{full_url}|{status_code}"
        - web.dir.sensitive: "{full_url}|{status_code}|{pattern}"
    """
    if not shutil.which("httpx"):
        return _make_error("DEPENDENCY_ERROR", "httpx binary not found in PATH")

    wordlist_path = _WORDLIST_MAP.get(wordlist)
    if wordlist_path is None:
        return _make_error(
            "INVALID_WORDLIST",
            f"Unknown wordlist '{wordlist}'. Valid options: {', '.join(_WORDLIST_MAP.keys())}",
        )

    if not Path(wordlist_path).exists():
        return _make_error(
            "INVALID_WORDLIST",
            f"Wordlist file not found: {wordlist_path}",
        )

    effective_extensions = extensions or _DEFAULT_EXTENSIONS

    # Read wordlist and build URL list
    base_url = url.rstrip("/")
    try:
        with open(wordlist_path, "r") as f:
            words = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except Exception as exc:
        return _make_error("INVALID_WORDLIST", f"Failed to read wordlist: {exc}")

    # Build target URLs: base paths + extensions
    target_urls: list[str] = []
    for word in words:
        target_urls.append(f"{base_url}/{word}")
        for ext in effective_extensions:
            target_urls.append(f"{base_url}/{word}.{ext}")

    # Write targets to temp file for httpx
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="athena_dir_"
    ) as tf:
        tf.write("\n".join(target_urls))
        targets_file = tf.name

    try:
        cmd = [
            "httpx",
            "-l", targets_file,
            "-json",
            "-status-code",
            "-silent",
            "-follow-redirects",
            "-mc", "200,201,202,204,301,302,307,308,403",
        ]

        try:
            stdout, stderr, returncode = await _run_command(cmd)
        except asyncio.TimeoutError:
            return _make_error("TIMEOUT", f"Directory enumeration timed out after {SCAN_TIMEOUT_SEC}s")
        except Exception as exc:
            return _make_error("CONNECTION_ERROR", f"Failed to run httpx: {exc}")
    finally:
        try:
            os.unlink(targets_file)
        except OSError:
            pass

    facts: list[dict[str, str]] = []
    sensitive_facts: list[dict[str, str]] = []
    lines = [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        found_url = data.get("url", data.get("input", ""))
        status = data.get("status_code", data.get("status-code", 0))

        if not found_url:
            continue

        # Determine path relative to base URL for sensitivity check
        rel_path = found_url.replace(base_url, "", 1)

        if _is_sensitive_path(rel_path):
            # Identify which pattern matched
            matched_pattern = ""
            for pattern in _SENSITIVE_PATTERNS:
                if pattern in rel_path.lower():
                    matched_pattern = pattern
                    break
            sensitive_facts.append({
                "trait": "web.dir.sensitive",
                "value": f"{found_url}|{status}|{matched_pattern}",
            })
        else:
            facts.append({
                "trait": "web.dir.found",
                "value": f"{found_url}|{status}",
            })

    # Prioritize sensitive paths, then regular, truncate at 500
    max_results = 500
    combined = sensitive_facts[:max_results]
    remaining = max_results - len(combined)
    if remaining > 0:
        combined.extend(facts[:remaining])

    return json.dumps({
        "facts": combined,
        "raw_output": stdout[:2000],
    })


# ---------------------------------------------------------------------------
# Tool 4: Screenshot
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_screenshot(url: str) -> str:
    """Take a screenshot of a web page via httpx screenshot mode.

    Falls back to recording page title if no Chrome/Chromium binary is available.

    Args:
        url: URL to screenshot.

    Returns:
        JSON string with Athena-compatible facts:
        - web.screenshot: "{url}|{screenshot_path_or_title}"
    """
    if not shutil.which("httpx"):
        return _make_error("DEPENDENCY_ERROR", "httpx binary not found in PATH")

    # Check if Chrome/Chromium is available for screenshot mode
    has_chrome = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
    )

    if has_chrome:
        # Use httpx screenshot mode
        import tempfile
        screenshot_dir = tempfile.mkdtemp(prefix="athena_screenshot_")

        cmd = [
            "httpx",
            "-target", url,
            "-screenshot",
            "-screenshot-path", screenshot_dir,
            "-json",
            "-silent",
        ]

        try:
            stdout, stderr, returncode = await _run_command(cmd, timeout=60)
        except asyncio.TimeoutError:
            return _make_error("TIMEOUT", "Screenshot timed out after 60s")
        except Exception as exc:
            return _make_error("CONNECTION_ERROR", f"Screenshot failed: {exc}")

        # Find screenshot file
        screenshot_files = list(Path(screenshot_dir).glob("*.png"))
        screenshot_path = str(screenshot_files[0]) if screenshot_files else "no_screenshot"

        facts = [{
            "trait": "web.screenshot",
            "value": f"{url}|{screenshot_path}",
        }]

        return json.dumps({
            "facts": facts,
            "raw_output": stdout[:2000],
        })
    else:
        # Fallback: just get the page title
        cmd = [
            "httpx",
            "-target", url,
            "-json",
            "-title",
            "-status-code",
            "-silent",
        ]

        try:
            stdout, stderr, returncode = await _run_command(cmd, timeout=30)
        except asyncio.TimeoutError:
            return _make_error("TIMEOUT", "Title probe timed out after 30s")
        except Exception as exc:
            return _make_error("CONNECTION_ERROR", f"Title probe failed: {exc}")

        title = ""
        lines = [line.strip() for line in stdout.strip().split("\n") if line.strip()]
        for line in lines:
            try:
                data = json.loads(line)
                title = data.get("title", "")
                break
            except json.JSONDecodeError:
                continue

        if not title and not lines:
            return _make_error("CONNECTION_ERROR", f"Could not reach {url}")

        facts = [{
            "trait": "web.screenshot",
            "value": f"{url}|title:{title}",
        }]

        return json.dumps({
            "facts": facts,
            "raw_output": stdout[:2000],
        })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)

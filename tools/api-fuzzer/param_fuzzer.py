"""Parameter fuzzing module for api-fuzzer.

Injects attack payloads into API parameters and detects vulnerabilities
by analysing response bodies and status codes.

Supported categories:
- SQL Injection (SQLi)
- Command Injection (CMDi)
- Cross-Site Scripting (XSS)
- Path Traversal
- Integer Overflow / Type Confusion
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Directory containing payload files
_PAYLOADS_DIR = Path(__file__).parent / "payloads"

# ----- Detection patterns -----

_SQLI_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"sql syntax",
        r"mysql_fetch",
        r"ORA-\d{5}",
        r"pg_query",
        r"sqlite3?\.",
        r"unclosed quotation mark",
        r"SQLSTATE\[",
        r"syntax error.*sql",
        r"microsoft.*odbc",
        r"warning.*mysql",
        r"you have an error in your sql",
        r"quoted string not properly terminated",
    ]
]

_CMDI_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"uid=\d+\([\w-]+\)\s+gid=",    # id command output
        r"root:x:0:0:",                    # /etc/passwd
        r"Linux\s+\S+\s+\d+\.\d+",        # uname -a output
        r"Windows\s+NT",                   # Windows OS
        r"total\s+\d+\s+drwx",            # ls -la output
    ]
]

_XSS_INDICATORS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "javascript:alert(1)",
]

_TRAVERSAL_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"root:x:0:0:",
        r"\[boot loader\]",
        r"<Directory",
    ]
]


def load_payloads(category: str) -> list[str]:
    """Load payload strings from a payload file.

    Args:
        category: One of sqli, cmdi, xss, traversal, overflow.

    Returns:
        List of payload strings (empty list if file not found).
    """
    payload_file = _PAYLOADS_DIR / f"{category}.txt"
    if not payload_file.exists():
        logger.warning("Payload file not found: %s", payload_file)
        return []

    with open(payload_file, "r") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def _detect_sqli(response_body: str) -> bool:
    """Check if response body contains SQL error indicators."""
    return any(p.search(response_body) for p in _SQLI_PATTERNS)


def _detect_cmdi(response_body: str) -> bool:
    """Check if response body contains command execution output."""
    return any(p.search(response_body) for p in _CMDI_PATTERNS)


def _detect_xss(response_body: str, payload: str) -> bool:
    """Check if the XSS payload is reflected in the response body."""
    return payload in response_body


def _detect_traversal(response_body: str) -> bool:
    """Check if response body contains path traversal indicators."""
    return any(p.search(response_body) for p in _TRAVERSAL_PATTERNS)


def _detect_overflow(status_code: int, response_body: str) -> bool:
    """Check if integer overflow or type confusion caused a server error."""
    if status_code >= 500:
        return True
    overflow_indicators = [
        "overflow", "out of range", "too large", "too small",
        "maximum value", "minimum value", "integer",
        "NumberFormatException", "ValueError",
    ]
    body_lower = response_body.lower()
    return any(indicator in body_lower for indicator in overflow_indicators)


async def fuzz_parameter(
    endpoint: str,
    method: str = "GET",
    params: dict[str, str] | None = None,
    timeout: float = 10.0,
    categories: list[str] | None = None,
) -> list[dict[str, str]]:
    """Fuzz API parameters with attack payloads and detect vulnerabilities.

    Args:
        endpoint: Target URL.
        method: HTTP method.
        params: Dict of parameter names to their original values.
        timeout: Request timeout in seconds.
        categories: Payload categories to test. Defaults to all.

    Returns:
        List of fact dicts with detected vulnerabilities.
    """
    if not params:
        return []

    all_categories = categories or ["sqli", "cmdi", "xss", "traversal", "overflow"]
    facts: list[dict[str, str]] = []
    waf_block_count = 0
    total_requests = 0

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        for param_name, original_value in params.items():
            for category in all_categories:
                payloads = load_payloads(category)

                for payload in payloads:
                    total_requests += 1

                    # Build request with the fuzzed parameter
                    fuzzed_params = dict(params)
                    fuzzed_params[param_name] = payload

                    try:
                        if method.upper() in ("GET", "HEAD", "DELETE"):
                            resp = await client.request(
                                method, endpoint, params=fuzzed_params,
                            )
                        else:
                            # POST/PUT/PATCH → send as JSON body
                            resp = await client.request(
                                method, endpoint, json=fuzzed_params,
                            )
                    except httpx.HTTPError:
                        continue
                    except Exception:
                        continue

                    body = resp.text
                    status = resp.status_code

                    # WAF blocking detection
                    if status == 403:
                        waf_block_count += 1
                        continue

                    # Detect vulnerabilities based on category
                    detected = False
                    trait = ""

                    if category == "sqli" and _detect_sqli(body):
                        detected = True
                        trait = "api.vuln.injection"
                    elif category == "cmdi" and _detect_cmdi(body):
                        detected = True
                        trait = "api.vuln.injection"
                    elif category == "xss" and _detect_xss(body, payload):
                        detected = True
                        trait = "api.vuln.injection"
                    elif category == "traversal" and _detect_traversal(body):
                        detected = True
                        trait = "api.vuln.injection"
                    elif category == "overflow" and _detect_overflow(status, body):
                        detected = True
                        trait = "api.vuln.overflow"

                    if detected:
                        facts.append({
                            "trait": trait,
                            "value": (
                                f"{endpoint}|{param_name}|{category}|"
                                f"{status}|{payload[:80]}"
                            ),
                        })

    # If all non-error requests were blocked by WAF, note it
    if waf_block_count > 0 and waf_block_count == total_requests:
        facts.append({
            "trait": "api.vuln.injection",
            "value": f"{endpoint}|waf_blocking|all_payloads_blocked",
        })

    return facts

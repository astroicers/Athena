"""api-fuzzer MCP Server for Athena.

Exposes API security testing tools via the Model Context Protocol:
  1. api_schema_detect  — OpenAPI / GraphQL schema discovery
  2. api_endpoint_enum  — Endpoint enumeration (schema + ffuf wordlist)
  3. api_auth_test      — BOLA / IDOR / auth bypass testing
  4. api_param_fuzz     — Parameter injection fuzzing

Each tool returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

import httpx

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from schema_detector import detect_openapi, detect_graphql, parse_openapi_spec
from auth_tester import (
    test_unauthenticated,
    test_bola,
    test_idor,
    test_method_tampering,
    test_header_bypass,
)
from param_fuzzer import fuzz_parameter

logger = logging.getLogger(__name__)

# Allow Docker internal network hostnames (mcp-api-fuzzer, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-api-fuzzer", transport_security=_security)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
FUZZ_RATE_LIMIT = int(os.environ.get("FUZZ_RATE_LIMIT", "50"))
FUZZ_TIMEOUT_SEC = int(os.environ.get("FUZZ_TIMEOUT_SEC", "180"))
MAX_ENDPOINTS = int(os.environ.get("MAX_ENDPOINTS", "500"))

_WORDLIST_MAP = {
    "api-common": "/opt/wordlists/api-common.txt",
    "api-large": "/opt/wordlists/api-large.txt",
}


def _make_error(error_type: str, message: str) -> str:
    """Return a structured JSON error response."""
    return json.dumps({
        "facts": [],
        "raw_output": "",
        "error": {"type": error_type, "message": message},
    })


async def _run_command(
    cmd: list[str], timeout: int | None = None,
) -> tuple[str, str, int]:
    """Run a command via asyncio subprocess. Returns (stdout, stderr, returncode)."""
    effective_timeout = timeout or FUZZ_TIMEOUT_SEC
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=effective_timeout,
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
# Tool 1: API Schema Detection
# ---------------------------------------------------------------------------

@mcp.tool()
async def api_schema_detect(base_url: str) -> str:
    """Probe common OpenAPI/Swagger/GraphQL endpoint paths.

    Discovers API documentation and introspection endpoints for the target.

    Args:
        base_url: Base URL of the target API (e.g. http://example.com).

    Returns:
        JSON string with Athena-compatible facts:
        - api.schema.openapi: "{url}|{status}"
        - api.schema.graphql: "{url}|introspection={enabled|disabled}"
    """
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    try:
        openapi_facts = await detect_openapi(base_url, timeout=10.0)
        facts.extend(openapi_facts)
        if openapi_facts:
            raw_parts.append(f"OpenAPI endpoints found: {len(openapi_facts)}")
    except httpx.ConnectError as exc:
        return _make_error("CONNECTION_ERROR", f"Cannot reach {base_url}: {exc}")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Schema detection failed: {exc}")

    try:
        graphql_facts = await detect_graphql(base_url, timeout=10.0)
        facts.extend(graphql_facts)
        if graphql_facts:
            raw_parts.append(f"GraphQL endpoints found: {len(graphql_facts)}")
    except Exception as exc:
        raw_parts.append(f"GraphQL detection error: {exc}")

    raw_output = "; ".join(raw_parts) if raw_parts else "No API schemas detected"

    return json.dumps({
        "facts": facts,
        "raw_output": raw_output,
    })


# ---------------------------------------------------------------------------
# Tool 2: API Endpoint Enumeration
# ---------------------------------------------------------------------------

@mcp.tool()
async def api_endpoint_enum(
    base_url: str,
    schema_url: str | None = None,
    wordlist: str = "api-common",
) -> str:
    """Enumerate API endpoints via schema parsing and/or ffuf wordlist fuzzing.

    Phase 1 (if schema_url provided): Download and parse OpenAPI spec to
    extract documented endpoints.
    Phase 2: Run ffuf against the target with an API-specific wordlist,
    filtering wildcard responses (>80% identical = wildcard).

    Args:
        base_url: Base URL of the target API (e.g. http://example.com/api).
        schema_url: Optional URL of an OpenAPI spec to parse first.
        wordlist: Wordlist to use: "api-common" or "api-large".

    Returns:
        JSON string with Athena-compatible facts:
        - api.endpoint.found: "{method} {path}|{status_code}"
        - api.endpoint.auth_required: "{path}|{status_code}"
    """
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    # Phase 1: Schema-based discovery
    if schema_url:
        try:
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True, verify=False,
            ) as client:
                resp = await client.get(schema_url)
                if resp.status_code < 400:
                    endpoints = parse_openapi_spec(resp.text)
                    for ep in endpoints[:MAX_ENDPOINTS]:
                        facts.append({
                            "trait": "api.endpoint.found",
                            "value": f"{ep}|schema",
                        })
                    raw_parts.append(
                        f"Schema-based: {len(endpoints)} endpoints from {schema_url}"
                    )
                else:
                    raw_parts.append(
                        f"Schema fetch failed: {schema_url} returned {resp.status_code}"
                    )
        except httpx.ConnectError as exc:
            return _make_error("CONNECTION_ERROR", f"Cannot reach {schema_url}: {exc}")
        except Exception as exc:
            raw_parts.append(f"Schema parse error: {exc}")

    # Phase 2: ffuf wordlist fuzzing
    wordlist_path = _WORDLIST_MAP.get(wordlist)
    if wordlist_path is None:
        return _make_error(
            "VALIDATION_ERROR",
            f"Unknown wordlist '{wordlist}'. Valid: {', '.join(_WORDLIST_MAP.keys())}",
        )

    has_ffuf = shutil.which("ffuf")
    if has_ffuf and Path(wordlist_path).exists():
        fuzz_url = base_url.rstrip("/") + "/FUZZ"
        cmd = [
            "ffuf",
            "-u", fuzz_url,
            "-w", wordlist_path,
            "-o", "/dev/stdout",
            "-of", "json",
            "-mc", "200,201,202,204,301,302,307,308,401,403",
            "-rate", str(FUZZ_RATE_LIMIT),
            "-s",  # silent
        ]

        try:
            stdout, stderr, returncode = await _run_command(cmd)
        except asyncio.TimeoutError:
            return _make_error(
                "TIMEOUT", f"ffuf timed out after {FUZZ_TIMEOUT_SEC}s"
            )
        except Exception as exc:
            return _make_error("CONNECTION_ERROR", f"Failed to run ffuf: {exc}")

        # Parse ffuf JSON output
        ffuf_results: list[dict] = []
        try:
            ffuf_data = json.loads(stdout)
            ffuf_results = ffuf_data.get("results", [])
        except (json.JSONDecodeError, ValueError):
            # Try line-by-line if not valid JSON block
            for line in stdout.strip().split("\n"):
                if line.strip():
                    try:
                        ffuf_results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Wildcard filter: if >80% of responses have same length, it's a wildcard
        if ffuf_results:
            lengths = [r.get("length", r.get("content-length", 0)) for r in ffuf_results]
            if lengths:
                from collections import Counter
                most_common_len, count = Counter(lengths).most_common(1)[0]
                wildcard_ratio = count / len(lengths)
                if wildcard_ratio > 0.8:
                    raw_parts.append(
                        f"Wildcard detected (ratio={wildcard_ratio:.2f}), "
                        f"filtering {count} false positives"
                    )
                    ffuf_results = [
                        r for r in ffuf_results
                        if r.get("length", r.get("content-length", 0)) != most_common_len
                    ]

        for result in ffuf_results:
            status = result.get("status", 0)
            input_word = result.get("input", {})
            if isinstance(input_word, dict):
                word = input_word.get("FUZZ", "unknown")
            else:
                word = str(input_word)
            path = f"{base_url.rstrip('/')}/{word}"

            if status in (401, 403):
                facts.append({
                    "trait": "api.endpoint.auth_required",
                    "value": f"{path}|{status}",
                })
            elif 200 <= status < 400:
                facts.append({
                    "trait": "api.endpoint.found",
                    "value": f"GET {path}|{status}",
                })

        raw_parts.append(f"ffuf: {len(ffuf_results)} results after filtering")
    elif not has_ffuf:
        # Fallback: use httpx for basic enumeration when ffuf not available
        if Path(wordlist_path).exists():
            try:
                with open(wordlist_path, "r") as f:
                    words = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
            except Exception as exc:
                return _make_error("DEPENDENCY_ERROR", f"Cannot read wordlist: {exc}")

            base = base_url.rstrip("/")
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=False, verify=False,
            ) as client:
                for word in words[:MAX_ENDPOINTS]:
                    url = f"{base}/{word}"
                    try:
                        resp = await client.get(url)
                        if resp.status_code in (401, 403):
                            facts.append({
                                "trait": "api.endpoint.auth_required",
                                "value": f"{url}|{resp.status_code}",
                            })
                        elif 200 <= resp.status_code < 400:
                            facts.append({
                                "trait": "api.endpoint.found",
                                "value": f"GET {url}|{resp.status_code}",
                            })
                    except httpx.HTTPError:
                        continue

            raw_parts.append(f"httpx fallback: tested {min(len(words), MAX_ENDPOINTS)} paths")
        else:
            return _make_error(
                "DEPENDENCY_ERROR",
                f"ffuf not found and wordlist {wordlist_path} missing",
            )
    else:
        raw_parts.append(f"Wordlist not found: {wordlist_path}")

    # Truncate to MAX_ENDPOINTS
    if len(facts) > MAX_ENDPOINTS:
        raw_parts.append(f"Truncated from {len(facts)} to {MAX_ENDPOINTS} endpoints")
        facts = facts[:MAX_ENDPOINTS]

    return json.dumps({
        "facts": facts,
        "raw_output": "; ".join(raw_parts) if raw_parts else "No endpoints found",
    })


# ---------------------------------------------------------------------------
# Tool 3: API Auth Test
# ---------------------------------------------------------------------------

@mcp.tool()
async def api_auth_test(
    endpoint: str,
    method: str = "GET",
    auth_token: str | None = None,
) -> str:
    """Test an API endpoint for authentication and authorization vulnerabilities.

    Runs the following checks:
    (a) Unauthenticated access
    (b) BOLA/IDOR via adjacent numeric IDs
    (c) HTTP method tampering
    (d) Header manipulation (X-Original-URL, path traversal)

    Args:
        endpoint: Full URL of the API endpoint to test (e.g. http://api.example.com/users/42).
        method: HTTP method for the primary request. Defaults to GET.
        auth_token: Optional Bearer token for authenticated tests.

    Returns:
        JSON string with Athena-compatible facts:
        - api.vuln.bola: "{url}|adjacent_id={id}|{status}"
        - api.vuln.idor: "{url}|no_auth|id={id}|{status}"
        - api.vuln.auth_bypass: "{url}|{type}|{detail}|{status}"
    """
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    # (a) Unauthenticated access
    try:
        unauth_facts = await test_unauthenticated(endpoint, method)
        facts.extend(unauth_facts)
        raw_parts.append(f"Unauthenticated: {len(unauth_facts)} findings")
    except httpx.ConnectError as exc:
        return _make_error("CONNECTION_ERROR", f"Cannot reach {endpoint}: {exc}")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Auth test failed: {exc}")

    # (b) BOLA (with auth token if provided)
    try:
        bola_facts = await test_bola(endpoint, method, auth_token)
        facts.extend(bola_facts)
        raw_parts.append(f"BOLA: {len(bola_facts)} findings")
    except Exception as exc:
        raw_parts.append(f"BOLA test error: {exc}")

    # (b') IDOR (without auth)
    try:
        idor_facts = await test_idor(endpoint, method)
        facts.extend(idor_facts)
        raw_parts.append(f"IDOR: {len(idor_facts)} findings")
    except Exception as exc:
        raw_parts.append(f"IDOR test error: {exc}")

    # (c) Method tampering
    try:
        tamper_facts = await test_method_tampering(endpoint, method, auth_token)
        facts.extend(tamper_facts)
        raw_parts.append(f"Method tamper: {len(tamper_facts)} findings")
    except Exception as exc:
        raw_parts.append(f"Method tamper error: {exc}")

    # (d) Header bypass
    try:
        header_facts = await test_header_bypass(endpoint, method)
        facts.extend(header_facts)
        raw_parts.append(f"Header bypass: {len(header_facts)} findings")
    except Exception as exc:
        raw_parts.append(f"Header bypass error: {exc}")

    return json.dumps({
        "facts": facts,
        "raw_output": "; ".join(raw_parts),
    })


# ---------------------------------------------------------------------------
# Tool 4: API Parameter Fuzzing
# ---------------------------------------------------------------------------

@mcp.tool()
async def api_param_fuzz(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
) -> str:
    """Fuzz API parameters with injection payloads to detect vulnerabilities.

    Injects SQL injection, command injection, XSS, path traversal, and
    integer overflow payloads into each parameter and analyses responses
    for vulnerability indicators.

    Args:
        endpoint: Full URL of the API endpoint (e.g. http://api.example.com/search).
        method: HTTP method. Defaults to GET.
        params: Dict of parameter names to their original values.
                Example: {"q": "test", "page": "1"}

    Returns:
        JSON string with Athena-compatible facts:
        - api.vuln.injection: "{url}|{param}|{category}|{status}|{payload}"
        - api.vuln.overflow: "{url}|{param}|overflow|{status}|{payload}"
    """
    if not params:
        return _make_error(
            "VALIDATION_ERROR", "params dict is required (e.g. {\"q\": \"test\"})"
        )

    try:
        facts = await fuzz_parameter(
            endpoint=endpoint,
            method=method,
            params=params,
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        return _make_error("CONNECTION_ERROR", f"Cannot reach {endpoint}: {exc}")
    except Exception as exc:
        return _make_error("CONNECTION_ERROR", f"Param fuzzing failed: {exc}")

    return json.dumps({
        "facts": facts,
        "raw_output": f"Tested {len(params)} parameters, {len(facts)} findings",
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

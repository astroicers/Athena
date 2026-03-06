"""BOLA / IDOR / authentication bypass testing module for api-fuzzer.

Tests API endpoints for:
- Unauthenticated access
- Broken Object Level Authorization (BOLA) via adjacent IDs
- Insecure Direct Object Reference (IDOR) via predictable IDs
- HTTP method tampering
- Header-based authentication bypass
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Numeric ID pattern in URL paths (e.g. /users/42, /api/v1/orders/123)
_ID_PATTERN = re.compile(r"/(\d+)(?=/|$)")

# Headers used for auth bypass attempts
_BYPASS_HEADERS = [
    {"X-Original-URL": "/admin"},
    {"X-Rewrite-URL": "/admin"},
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
]

# Path traversal bypass payloads
_PATH_BYPASS_SUFFIXES = [
    "/.",
    "/%2e",
    "/%2e/",
    "/..;/",
]

# HTTP methods to test for method tampering
_TAMPER_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _extract_id(url: str) -> int | None:
    """Extract the last numeric ID from a URL path."""
    matches = _ID_PATTERN.findall(url)
    if matches:
        try:
            return int(matches[-1])
        except ValueError:
            return None
    return None


def _replace_id(url: str, original_id: int, new_id: int) -> str:
    """Replace the last occurrence of original_id with new_id in the URL path."""
    # Replace the last occurrence
    parts = url.rsplit(str(original_id), 1)
    if len(parts) == 2:
        return parts[0] + str(new_id) + parts[1]
    return url


async def test_unauthenticated(
    endpoint: str,
    method: str = "GET",
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Test endpoint access without authentication.

    Returns facts if the endpoint responds with 2xx without any auth.
    """
    facts: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        try:
            resp = await client.request(method, endpoint)
            if 200 <= resp.status_code < 300:
                facts.append({
                    "trait": "api.vuln.auth_bypass",
                    "value": f"{endpoint}|unauthenticated|{resp.status_code}",
                })
        except httpx.HTTPError as exc:
            logger.debug("Unauthenticated test error for %s: %s", endpoint, exc)
        except Exception as exc:
            logger.debug("Unauthenticated test unexpected error: %s", exc)

    return facts


async def test_bola(
    endpoint: str,
    method: str = "GET",
    auth_token: str | None = None,
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Test for Broken Object Level Authorization (BOLA).

    Extracts a numeric ID from the URL and tries adjacent IDs
    (ID-1, ID+1, ID+100, 0, 1) to see if they are accessible.
    """
    facts: list[dict[str, str]] = []
    original_id = _extract_id(endpoint)

    if original_id is None:
        return facts

    adjacent_ids = [
        original_id - 1,
        original_id + 1,
        original_id + 100,
        0,
        1,
    ]
    # Deduplicate and remove original
    adjacent_ids = [i for i in dict.fromkeys(adjacent_ids) if i != original_id]

    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        for test_id in adjacent_ids:
            test_url = _replace_id(endpoint, original_id, test_id)
            try:
                resp = await client.request(method, test_url, headers=headers)
                if 200 <= resp.status_code < 300:
                    facts.append({
                        "trait": "api.vuln.bola",
                        "value": f"{test_url}|adjacent_id={test_id}|{resp.status_code}",
                    })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts


async def test_idor(
    endpoint: str,
    method: str = "GET",
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Test for IDOR by accessing ID-based resources without auth.

    Similar to BOLA but specifically tests without any auth token.
    """
    facts: list[dict[str, str]] = []
    original_id = _extract_id(endpoint)

    if original_id is None:
        return facts

    adjacent_ids = [
        original_id - 1,
        original_id + 1,
        original_id + 100,
        0,
        1,
    ]
    adjacent_ids = [i for i in dict.fromkeys(adjacent_ids) if i != original_id]

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        for test_id in adjacent_ids:
            test_url = _replace_id(endpoint, original_id, test_id)
            try:
                resp = await client.request(method, test_url)
                if 200 <= resp.status_code < 300:
                    facts.append({
                        "trait": "api.vuln.idor",
                        "value": f"{test_url}|no_auth|id={test_id}|{resp.status_code}",
                    })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts


async def test_method_tampering(
    endpoint: str,
    original_method: str = "GET",
    auth_token: str | None = None,
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Test HTTP method tampering.

    Tries all standard HTTP methods to see if methods not expected
    by the endpoint return 2xx responses.
    """
    facts: list[dict[str, str]] = []
    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    methods_to_test = [m for m in _TAMPER_METHODS if m != original_method.upper()]

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        for test_method in methods_to_test:
            try:
                resp = await client.request(test_method, endpoint, headers=headers)
                if 200 <= resp.status_code < 300:
                    facts.append({
                        "trait": "api.vuln.auth_bypass",
                        "value": f"{endpoint}|method_tamper|{test_method}|{resp.status_code}",
                    })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts


async def test_header_bypass(
    endpoint: str,
    method: str = "GET",
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Test authentication bypass via header manipulation.

    Tries bypass headers (X-Original-URL, X-Forwarded-For, etc.)
    and path traversal suffixes.
    """
    facts: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, verify=False,
    ) as client:
        # Header-based bypass
        for bypass_headers in _BYPASS_HEADERS:
            try:
                resp = await client.request(method, endpoint, headers=bypass_headers)
                if 200 <= resp.status_code < 300:
                    header_name = list(bypass_headers.keys())[0]
                    facts.append({
                        "trait": "api.vuln.auth_bypass",
                        "value": f"{endpoint}|header_bypass|{header_name}|{resp.status_code}",
                    })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

        # Path traversal bypass
        for suffix in _PATH_BYPASS_SUFFIXES:
            test_url = endpoint.rstrip("/") + suffix
            try:
                resp = await client.request(method, test_url)
                if 200 <= resp.status_code < 300:
                    facts.append({
                        "trait": "api.vuln.auth_bypass",
                        "value": f"{test_url}|path_bypass|{suffix}|{resp.status_code}",
                    })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts

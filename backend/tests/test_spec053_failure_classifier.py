# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-053 Test Matrix — _classify_failure heuristic.

Covers test cases B1-B4 from SPEC-053 §Test Matrix:

    B1 (T05): auth_failure   — "All SSH credentials failed..."
    B2 (T06): exploit_failed — "no session within 60s"
    B3:       unknown        — error=None
    B4:       tool_error     — pydantic validation error text

The function under test is the module-level helper
``engine_router._classify_failure``. It is a pure string heuristic
with no I/O, so the tests have zero fixtures.

Gherkin scenario reference: Scenario Outline "failure classifier
heuristic" in SPEC-053 §驗收場景.
"""

import pytest

from app.services.engine_router import _classify_failure


# ---------------------------------------------------------------------------
# Explicit single-case tests (match Test Matrix B1-B4 one-for-one)
# ---------------------------------------------------------------------------


def test_b1_auth_failure_ssh_credentials_exhausted() -> None:
    """B1/T05: SSH brute exhaust message -> auth_failure."""
    got = _classify_failure(
        "All SSH credentials failed for 192.168.0.26:22",
        "initial_access",
    )
    assert got == "auth_failure"


def test_b2_exploit_failed_no_session() -> None:
    """B2/T06: metasploit no-session timeout -> exploit_failed."""
    got = _classify_failure("no session within 60s", "metasploit")
    assert got == "exploit_failed"


def test_b3_none_error_falls_to_unknown() -> None:
    """B3: None error -> unknown (safe fallback)."""
    assert _classify_failure(None, "mcp") == "unknown"


def test_b4_tool_error_pydantic_validation() -> None:
    """B4: dns_resolve pydantic validation -> tool_error."""
    got = _classify_failure(
        "1 validation error for dns_resolveArguments\n"
        "subdomains\n  Field required",
        "mcp",
    )
    assert got == "tool_error"


# ---------------------------------------------------------------------------
# Parametrised boundary outline (Gherkin Scenario Outline coverage)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error,engine,expected",
    [
        # Auth-style errors
        ("All SSH credentials failed for host", "initial_access", "auth_failure"),
        ("permission denied for user msfadmin", "initial_access", "auth_failure"),
        ("Login failed on winrm", "mcp", "auth_failure"),
        # Service reachability
        ("connection refused", "mcp", "service_unreachable"),
        ("no route to host", "metasploit", "service_unreachable"),
        ("unreachable network", "mcp", "service_unreachable"),
        ("No targetable services found", "initial_access", "service_unreachable"),
        # Exploit failed
        ("no session within 30s", "metasploit", "exploit_failed"),
        ("no session within 60s", "metasploit", "exploit_failed"),
        ("exploit aborted", "metasploit", "exploit_failed"),
        # Privilege
        ("privilege insufficient for DCSync", "c2", "privilege_insufficient"),
        ("not root, cannot dump", "c2", "privilege_insufficient"),
        # Prerequisite
        ("no credential available", "c2", "prerequisite_missing"),
        ("prerequisite missing: agent", "c2", "prerequisite_missing"),
        # Tool errors (MCP pydantic)
        (
            "1 validation error for dns_resolveArguments\nsubdomains\n  Field required",
            "mcp",
            "tool_error",
        ),
        ("tool not found: nonexistent_tool", "mcp", "tool_error"),
        # Timeout
        ("operation timed out", "metasploit", "timeout"),
        ("timeout waiting for result", "mcp", "timeout"),
        # Unknown fallback
        ("something totally unexpected", "mcp", "unknown"),
        (None, "mcp", "unknown"),
        ("", "mcp", "unknown"),
    ],
)
def test_classify_failure_outline(error, engine, expected) -> None:
    assert _classify_failure(error, engine) == expected


# ---------------------------------------------------------------------------
# Safety properties — heuristic must never raise
# ---------------------------------------------------------------------------


def test_classify_failure_accepts_mixed_case() -> None:
    """Heuristic must be case-insensitive (we lowercase the input)."""
    assert (
        _classify_failure("CONNECTION REFUSED", "metasploit")
        == "service_unreachable"
    )


def test_classify_failure_never_raises_on_unicode() -> None:
    """Non-ASCII input should degrade gracefully to 'unknown'."""
    # Chinese error text — not something the heuristic matches
    assert _classify_failure("認證失敗", "mcp") == "unknown"
    # Emoji in error message
    assert _classify_failure("💥 kaboom", "mcp") == "unknown"

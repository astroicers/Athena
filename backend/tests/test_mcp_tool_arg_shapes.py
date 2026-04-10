# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Tech-debt D2: Parametrized test for MCPEngineClient._TOOL_ARG_SHAPES.

Verifies the per-tool argument shape override mechanism introduced
in SPEC-054 (B3 fix for dns_resolve schema mismatch). The override
dict maps tool names to lambdas that transform the raw target string
into the correct argument dict for that tool's schema.
"""

import pytest

from app.clients.mcp_engine_client import _TOOL_ARG_SHAPES


@pytest.mark.parametrize(
    "tool_name,target,expected_key,expected_value",
    [
        # dns_resolve expects {subdomains: target} instead of {target: target}
        ("dns_resolve", "192.168.0.26", "subdomains", "192.168.0.26"),
        ("dns_resolve", "sub1.example.com,sub2.example.com", "subdomains",
         "sub1.example.com,sub2.example.com"),
        # Tools NOT in _TOOL_ARG_SHAPES use the default {target: target}
        ("nmap_scan", "192.168.0.26", "target", "192.168.0.26"),
        ("web_scan", "https://example.com", "target", "https://example.com"),
        ("nonexistent_tool", "x", "target", "x"),
    ],
)
def test_tool_arg_shape(
    tool_name: str,
    target: str,
    expected_key: str,
    expected_value: str,
) -> None:
    """_TOOL_ARG_SHAPES transforms the target string per tool schema."""
    shaper = _TOOL_ARG_SHAPES.get(tool_name)
    args = shaper(target) if shaper else {"target": target}
    assert expected_key in args, (
        f"Expected key '{expected_key}' in args for tool '{tool_name}', "
        f"got {args}"
    )
    assert args[expected_key] == expected_value


def test_dns_resolve_does_not_include_target_key() -> None:
    """dns_resolve must NOT have a 'target' key — only 'subdomains'."""
    shaper = _TOOL_ARG_SHAPES["dns_resolve"]
    args = shaper("192.168.0.26")
    assert "target" not in args, (
        "dns_resolve shape must NOT include 'target' key — "
        "it expects 'subdomains' only"
    )
    assert "subdomains" in args


def test_tool_arg_shapes_is_dict_of_callables() -> None:
    """Sanity: every entry in _TOOL_ARG_SHAPES is callable."""
    for name, shaper in _TOOL_ARG_SHAPES.items():
        assert callable(shaper), f"_TOOL_ARG_SHAPES[{name!r}] is not callable"
        # Must return a dict when called
        result = shaper("test")
        assert isinstance(result, dict), (
            f"_TOOL_ARG_SHAPES[{name!r}]('test') returned "
            f"{type(result).__name__}, expected dict"
        )

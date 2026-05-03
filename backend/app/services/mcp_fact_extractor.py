# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Extract Athena facts from MCP tool results.

MCP tools are expected to return JSON-structured output in one of these formats:

1. Structured facts (preferred):
   {"facts": [{"trait": "network.host.ip", "value": "10.0.1.5"}, ...]}

2. Flat dict (simple):
   {"trait_name": "value", ...}

3. Plain text (fallback):
   Any text -> wrapped as a single fact with default_trait.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_VALUE_MAX_LEN = 500
_HASH_TRAITS = frozenset({
    "credential.asrep_hash", "credential.kerberos_hash",
    "credential.service_hash", "credential.ntlm_hash",
    "credential.ntds_hash", "credential.krbtgt_hash",
})
_HASH_VALUE_MAX_LEN = 1000


class MCPFactExtractor:
    """Convert MCP tool results to Athena {trait, value} facts."""

    @staticmethod
    def extract(
        mcp_result: dict[str, Any],
        default_trait: str = "mcp.output",
        output_traits: list[str] | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        """Extract facts and output text from an MCP call_tool result.

        Args:
            mcp_result: Dict from MCPClientManager.call_tool().
                        Keys: "content" (list of content blocks), "is_error".
            default_trait: Trait name when structured facts are not found.
            output_traits: From tool_registry.output_traits, used as fallback.

        Returns:
            (output_text, facts_list) tuple.
        """
        if mcp_result.get("is_error"):
            text = MCPFactExtractor._extract_text(mcp_result)
            return text, []

        text = MCPFactExtractor._extract_text(mcp_result)
        if not text.strip():
            return "", []

        # Attempt 1: JSON with {"facts": [...]}
        facts = MCPFactExtractor._try_structured_facts(text)
        if facts:
            return text, facts

        # Attempt 2: JSON flat dict {key: value}
        facts = MCPFactExtractor._try_flat_dict(text)
        if facts:
            return text, facts

        # Attempt 3: fallback — wrap entire output as single fact
        trait = output_traits[0] if output_traits else default_trait
        return text, [{"trait": trait, "value": text[:_VALUE_MAX_LEN]}]

    @staticmethod
    def _extract_text(mcp_result: dict) -> str:
        """Concatenate all text content blocks from MCP result."""
        parts: list[str] = []
        for block in mcp_result.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)

    @staticmethod
    def _try_structured_facts(text: str) -> list[dict[str, str]] | None:
        """Try to parse {"facts": [{"trait": ..., "value": ...}, ...]}."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "facts" in data:
                raw_facts = data["facts"]
                if isinstance(raw_facts, list):
                    validated = []
                    for f in raw_facts:
                        if isinstance(f, dict) and "trait" in f and "value" in f:
                            t = str(f["trait"])
                            vlim = _HASH_VALUE_MAX_LEN if t in _HASH_TRAITS else _VALUE_MAX_LEN
                            validated.append({
                                "trait": t,
                                "value": str(f["value"])[:vlim],
                            })
                    if validated:
                        return validated
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return None

    @staticmethod
    def _try_flat_dict(text: str) -> list[dict[str, str]] | None:
        """Try to parse {"trait_name": "value", ...} flat dict."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "facts" not in data:
                facts = []
                for key, val in data.items():
                    if isinstance(val, (str, int, float, bool)):
                        facts.append({
                            "trait": str(key),
                            "value": str(val)[:_VALUE_MAX_LEN],
                        })
                if facts:
                    return facts
        except (json.JSONDecodeError, TypeError):
            pass
        return None

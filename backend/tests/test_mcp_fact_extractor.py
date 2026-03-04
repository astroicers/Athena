# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for MCPFactExtractor."""

from app.services.mcp_fact_extractor import MCPFactExtractor


def test_extract_structured_facts():
    """Structured JSON with 'facts' key is parsed correctly."""
    mcp_result = {
        "content": [
            {
                "type": "text",
                "text": '{"facts": [{"trait": "host.os", "value": "Linux"}, {"trait": "host.user", "value": "root"}]}',
            }
        ],
        "is_error": False,
    }
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert len(facts) == 2
    assert facts[0]["trait"] == "host.os"
    assert facts[1]["value"] == "root"


def test_extract_flat_dict():
    """Flat dict {key: value} parsed as facts."""
    mcp_result = {
        "content": [
            {
                "type": "text",
                "text": '{"network.host.ip": "10.0.1.5", "host.os": "Linux"}',
            }
        ],
        "is_error": False,
    }
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert len(facts) == 2
    traits = {f["trait"] for f in facts}
    assert "network.host.ip" in traits


def test_extract_plain_text_fallback():
    """Plain text falls back to single fact with default trait."""
    mcp_result = {
        "content": [{"type": "text", "text": "Some raw nmap output"}],
        "is_error": False,
    }
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert len(facts) == 1
    assert facts[0]["trait"] == "mcp.output"
    assert facts[0]["value"] == "Some raw nmap output"


def test_extract_with_output_traits():
    """output_traits from tool_registry used as fallback trait name."""
    mcp_result = {
        "content": [{"type": "text", "text": "scan result text"}],
        "is_error": False,
    }
    output, facts = MCPFactExtractor.extract(
        mcp_result,
        output_traits=["network.host.ip"],
    )
    assert facts[0]["trait"] == "network.host.ip"


def test_extract_error_returns_no_facts():
    """Error MCP result returns empty facts."""
    mcp_result = {
        "content": [{"type": "text", "text": "Error: connection refused"}],
        "is_error": True,
    }
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert facts == []
    assert "Error" in output


def test_extract_empty_content():
    """Empty content returns empty output and facts."""
    mcp_result = {"content": [], "is_error": False}
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert output == ""
    assert facts == []


def test_extract_value_truncation():
    """Values longer than 500 chars are truncated."""
    long_value = "A" * 1000
    mcp_result = {
        "content": [
            {
                "type": "text",
                "text": f'{{"facts": [{{"trait": "test", "value": "{long_value}"}}]}}',
            }
        ],
        "is_error": False,
    }
    output, facts = MCPFactExtractor.extract(mcp_result)
    assert len(facts[0]["value"]) == 500

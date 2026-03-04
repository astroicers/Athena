"""{{TOOL_NAME}} MCP Server for Athena.

Exposes tools via the Model Context Protocol.
Each tool SHOULD return JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("athena-{{TOOL_NAME}}")


@mcp.tool()
async def example_scan(target: str) -> str:
    """Example tool: scan a target and return facts.

    Args:
        target: IP address or hostname to scan.

    Returns:
        JSON string with Athena-compatible facts.
    """
    # TODO: Replace with real implementation
    facts = [
        {"trait": "network.host.ip", "value": target},
        {"trait": "host.os", "value": "Linux"},
    ]
    return json.dumps({"facts": facts, "raw_output": f"Scanned {target}"})


if __name__ == "__main__":
    mcp.run()

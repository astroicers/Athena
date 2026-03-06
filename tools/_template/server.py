"""{{TOOL_NAME}} MCP Server for Athena.

Exposes tools via the Model Context Protocol.
Each tool SHOULD return JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-xxx, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-{{TOOL_NAME}}", transport_security=_security)


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
    ]
    return json.dumps({"facts": facts, "raw_output": f"Scanned {target}"})


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

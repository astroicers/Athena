"""nmap-scanner MCP Server for Athena.

Exposes nmap port scanning as an MCP tool.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-nmap, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-nmap-scanner", transport_security=_security)

# Default port list matching Athena's ReconEngine
_DEFAULT_PORTS = (
    "21,22,23,25,53,80,110,135,139,143,443,445,"
    "1433,3000,3306,3389,3500,5432,5900,6379,"
    "8080,8443,8888,9090,27017"
)


@mcp.tool()
async def nmap_scan(target: str, ports: str = _DEFAULT_PORTS) -> str:
    """Run nmap service/version scan against a target IP.

    Args:
        target: IP address or hostname to scan.
        ports: Comma-separated list of ports to scan.

    Returns:
        JSON string with Athena-compatible facts:
        - service.open_port: "{port}/{proto}/{service}/{version}"
        - network.host.ip: target IP
        - host.os: OS guess (if detected)
    """
    import nmap as nmap_lib

    loop = asyncio.get_event_loop()
    nm = await loop.run_in_executor(None, _run_nmap, target, ports, nmap_lib)

    facts: list[dict[str, str]] = []
    os_guess: str | None = None

    if target in nm.all_hosts():
        host_data = nm[target]

        # OS detection
        if "osmatch" in host_data and host_data["osmatch"]:
            raw_os = host_data["osmatch"][0].get("name", "")
            os_guess = raw_os.replace(" ", "_") if raw_os else None

        # Open ports / services
        for proto in host_data.all_protocols():
            for port in host_data[proto].keys():
                port_data = host_data[proto][port]
                if port_data.get("state") != "open":
                    continue
                svc_name = port_data.get("name", "unknown")
                svc_version = (
                    " ".join(
                        filter(
                            None,
                            [
                                port_data.get("product", ""),
                                port_data.get("version", ""),
                                port_data.get("extrainfo", ""),
                            ],
                        )
                    ).strip()
                    or "unknown"
                )
                facts.append({
                    "trait": "service.open_port",
                    "value": f"{port}/{proto}/{svc_name}/{svc_version.replace(' ', '_')}",
                })

    # Always include target IP
    facts.append({"trait": "network.host.ip", "value": target})

    # OS fact
    if os_guess:
        facts.append({"trait": "host.os", "value": os_guess})

    raw_output = (nm.get_nmap_last_output() or b"").decode(errors="replace")
    return json.dumps({
        "facts": facts,
        "raw_output": raw_output[:2000],
    })


def _run_nmap(ip: str, ports: str, nmap_lib) -> "nmap_lib.PortScanner":
    """Synchronous nmap call — runs inside executor."""
    nm = nmap_lib.PortScanner()
    nm.scan(hosts=ip, arguments=f"-sV -Pn --script=banner -p {ports}")
    return nm


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)

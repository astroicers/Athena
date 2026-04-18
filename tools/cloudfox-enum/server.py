"""cloudfox-enum MCP Server for Athena.

CloudFox-based AWS/Azure/GCP environment enumeration + privilege escalation
path detection.
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

mcp = FastMCP("athena-cloudfox-enum", transport_security=_security)


async def _run_command(cmd: list[str], timeout: int = 300) -> tuple[str, str, int]:
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


def _build_cloudfox_cmd(provider: str, module: str, profile: str = "default") -> list[str]:
    """Build CloudFox command for the given provider and module."""
    cmd = ["cloudfox", provider, module]
    if provider == "aws":
        cmd.extend(["-p", profile])
    return cmd


@mcp.tool()
async def cloudfox_iam_enum(
    provider: str = "aws",
    profile: str = "default",
) -> str:
    """IAM permission enumeration + privilege escalation path analysis.

    Args:
        provider: Cloud provider (aws, azure, gcp)
        profile: AWS profile name or cloud credential identifier

    Returns:
        JSON with facts: cloud.iam_role, cloud.privesc_path, cloud.overprivileged_user
    """
    facts: list[dict[str, str]] = []

    try:
        if provider == "aws":
            cmd = _build_cloudfox_cmd("aws", "iam-simulator", profile)
        elif provider == "azure":
            cmd = ["cloudfox", "azure", "rbac"]
        else:
            cmd = ["cloudfox", provider, "iam"]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            if re.search(r"(Admin|PowerUser|FullAccess|\*:\*)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.overprivileged_user", "value": stripped[:200]})

            if re.search(r"(privesc|escalat|assume.?role|pass.?role)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.privesc_path", "value": stripped[:200]})

            role_match = re.search(r"(arn:aws:iam::\d+:role/\S+)", stripped)
            if role_match:
                facts.append({"trait": "cloud.iam_role", "value": role_match.group(1)})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def cloudfox_all_checks(
    provider: str = "aws",
    profile: str = "default",
) -> str:
    """Execute all CloudFox security checks.

    Args:
        provider: Cloud provider (aws, azure, gcp)
        profile: AWS profile name or cloud credential identifier

    Returns:
        JSON with facts: cloud.public_resource, cloud.secret_found, cloud.misconfiguration
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = _build_cloudfox_cmd(provider, "all-checks", profile)

        stdout, stderr, rc = await _run_command(cmd, timeout=600)
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            if re.search(r"(public|exposed|open)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.public_resource", "value": stripped[:200]})

            if re.search(r"(secret|password|key|token|credential)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.secret_found", "value": stripped[:200]})

            if re.search(r"(misconfigur|warning|critical|high)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.misconfiguration", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def cloudfox_find_secrets(
    provider: str = "aws",
    profile: str = "default",
) -> str:
    """Search cloud environment for sensitive information (env vars, SSM, Secrets Manager).

    Args:
        provider: Cloud provider (aws, azure, gcp)
        profile: AWS profile name or cloud credential identifier

    Returns:
        JSON with facts: cloud.secret_found, cloud.env_variable, cloud.ssm_parameter
    """
    facts: list[dict[str, str]] = []

    try:
        modules = ["env-vars", "secrets", "ssm"]
        combined_output = ""

        for module in modules:
            cmd = _build_cloudfox_cmd(provider, module, profile)
            stdout, stderr, rc = await _run_command(cmd)
            output = stdout + stderr
            combined_output += output + "\n"

            for line in output.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("["):
                    continue

                if module == "env-vars":
                    facts.append({"trait": "cloud.env_variable", "value": stripped[:200]})
                elif module == "ssm":
                    facts.append({"trait": "cloud.ssm_parameter", "value": stripped[:200]})
                else:
                    facts.append({"trait": "cloud.secret_found", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined_output[:4000]})

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

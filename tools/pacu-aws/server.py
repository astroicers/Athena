"""pacu-aws MCP Server for Athena.

Pacu AWS exploitation framework: IAM privilege escalation, S3 enumeration,
Lambda backdoor analysis, EC2 enumeration.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-pacu-aws", transport_security=_security)

PACU_SESSION = "athena"


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


async def _run_pacu_module(module: str, args: list[str] | None = None, timeout: int = 300) -> tuple[str, str, int]:
    """Run a Pacu module with the athena session."""
    cmd = ["pacu", "--session", PACU_SESSION, "--module", module]
    if args:
        cmd.extend(args)
    return await _run_command(cmd, timeout=timeout)


@mcp.tool()
async def pacu_iam_privesc_scan(
    profile: str = "default",
    region: str = "us-east-1",
) -> str:
    """Scan for IAM privilege escalation paths (iam__privesc_scan).

    Args:
        profile: AWS profile name
        region: AWS region

    Returns:
        JSON with facts: cloud.iam_privesc, cloud.exploitable_policy
    """
    facts: list[dict[str, str]] = []

    try:
        os.environ["AWS_PROFILE"] = profile
        os.environ["AWS_DEFAULT_REGION"] = region

        stdout, stderr, rc = await _run_pacu_module("iam__privesc_scan")
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            if re.search(r"(privesc|escalat|exploit)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.iam_privesc", "value": stripped[:200]})

            policy_match = re.search(r"(arn:aws:iam::\S+)", stripped)
            if policy_match and re.search(r"(policy|permission)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.exploitable_policy", "value": policy_match.group(1)})

            if re.search(r"(CreateAccessKey|PassRole|AssumeRole|AttachUserPolicy|PutUserPolicy)", stripped):
                facts.append({"trait": "cloud.iam_privesc", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def pacu_s3_enum(
    profile: str = "default",
    region: str = "us-east-1",
) -> str:
    """Enumerate S3 bucket access permissions + sensitive files.

    Args:
        profile: AWS profile name
        region: AWS region

    Returns:
        JSON with facts: cloud.s3_bucket, cloud.s3_public_bucket, cloud.s3_sensitive_file
    """
    facts: list[dict[str, str]] = []

    try:
        os.environ["AWS_PROFILE"] = profile
        os.environ["AWS_DEFAULT_REGION"] = region

        stdout, stderr, rc = await _run_pacu_module("s3__bucket_finder")
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            bucket_match = re.search(r"(s3://[\w.-]+|[\w.-]+\.s3\.amazonaws\.com)", stripped)
            if bucket_match:
                facts.append({"trait": "cloud.s3_bucket", "value": bucket_match.group(1)})

            if re.search(r"(public|open|world|everyone)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.s3_public_bucket", "value": stripped[:200]})

            if re.search(r"\.(pem|key|env|conf|bak|sql|csv)$", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.s3_sensitive_file", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def pacu_lambda_backdoor(
    profile: str = "default",
    region: str = "us-east-1",
    function_name: str = "",
) -> str:
    """Lambda function backdoor analysis (detection + simulation).

    Args:
        profile: AWS profile name
        region: AWS region
        function_name: Specific Lambda function to analyze (empty for all)

    Returns:
        JSON with facts: cloud.lambda_function, cloud.lambda_backdoor_opportunity
    """
    facts: list[dict[str, str]] = []

    try:
        os.environ["AWS_PROFILE"] = profile
        os.environ["AWS_DEFAULT_REGION"] = region

        stdout1, stderr1, _ = await _run_pacu_module("lambda__enum")
        combined = stdout1 + stderr1

        for line in combined.splitlines():
            lambda_match = re.search(r"(arn:aws:lambda:\S+:function:\S+)", line.strip())
            if lambda_match:
                facts.append({"trait": "cloud.lambda_function", "value": lambda_match.group(1)})

        stdout2, stderr2, _ = await _run_pacu_module("lambda__backdoor_new_roles")
        combined2 = stdout2 + stderr2

        for line in combined2.splitlines():
            if re.search(r"(backdoor|vulnerable|exploit|opportunity)", line.strip(), re.IGNORECASE):
                facts.append({"trait": "cloud.lambda_backdoor_opportunity", "value": line.strip()[:200]})

        return json.dumps({"facts": facts, "raw_output": (combined + "\n" + combined2)[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def pacu_ec2_enum(
    profile: str = "default",
    region: str = "us-east-1",
) -> str:
    """EC2 instance enumeration + security group analysis.

    Args:
        profile: AWS profile name
        region: AWS region

    Returns:
        JSON with facts: cloud.ec2_instance, cloud.security_group_open, cloud.ec2_public_ip
    """
    facts: list[dict[str, str]] = []

    try:
        os.environ["AWS_PROFILE"] = profile
        os.environ["AWS_DEFAULT_REGION"] = region

        stdout, stderr, rc = await _run_pacu_module("ec2__enum")
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            instance_match = re.search(r"(i-[a-fA-F0-9]+)", stripped)
            if instance_match:
                facts.append({"trait": "cloud.ec2_instance", "value": stripped[:200]})

            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
            if ip_match:
                ip = ip_match.group(1)
                if not (ip.startswith("10.") or ip.startswith("172.") or ip.startswith("192.168.")):
                    facts.append({"trait": "cloud.ec2_public_ip", "value": ip})

            if re.search(r"(0\.0\.0\.0/0|::/0|all traffic|open)", stripped, re.IGNORECASE):
                facts.append({"trait": "cloud.security_group_open", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

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

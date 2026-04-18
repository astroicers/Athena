"""scoutsuite-audit MCP Server for Athena.

ScoutSuite-based multi-cloud security compliance audit
(AWS/Azure/GCP/Alibaba/Oracle).
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

mcp = FastMCP("athena-scoutsuite-audit", transport_security=_security)

REPORT_DIR = "/tmp/scoutsuite-report"


async def _run_command(cmd: list[str], timeout: int = 600) -> tuple[str, str, int]:
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


def _parse_scoutsuite_results(report_dir: str) -> dict:
    """Parse ScoutSuite JSON results from report directory."""
    results: dict = {"critical": 0, "high": 0, "medium": 0, "low": 0, "findings": []}

    for fname in os.listdir(report_dir) if os.path.isdir(report_dir) else []:
        if fname.startswith("scoutsuite-results") and fname.endswith(".js"):
            fpath = os.path.join(report_dir, fname)
            try:
                with open(fpath) as fh:
                    content = fh.read()
                    json_start = content.find("{")
                    if json_start >= 0:
                        data = json.loads(content[json_start:])
                        services = data.get("services", {})
                        for svc_name, svc_data in services.items():
                            for finding_key, finding in svc_data.get("findings", {}).items():
                                level = finding.get("level", "info")
                                if level == "danger":
                                    results["critical"] += 1
                                elif level == "warning":
                                    results["high"] += 1
                                else:
                                    results["medium"] += 1
                                results["findings"].append({
                                    "service": svc_name,
                                    "rule": finding_key,
                                    "level": level,
                                    "count": len(finding.get("items", [])),
                                    "description": finding.get("rationale", "")[:200],
                                })
            except (json.JSONDecodeError, OSError, KeyError):
                continue

    return results


@mcp.tool()
async def scoutsuite_audit(
    provider: str = "aws",
    profile: str = "default",
    services: str = "",
) -> str:
    """Execute comprehensive security audit (HTML report + JSON structured data).

    Args:
        provider: Cloud provider (aws, azure, gcp, aliyun, oci)
        profile: AWS profile or cloud credential identifier
        services: Comma-separated list of services to audit (empty for all)

    Returns:
        JSON with facts: cloud.audit_finding, cloud.critical_count, cloud.high_count
    """
    facts: list[dict[str, str]] = []

    try:
        report_dir = f"{REPORT_DIR}/{provider}"
        os.makedirs(report_dir, exist_ok=True)

        cmd = ["scout", provider]
        if provider == "aws":
            cmd.extend(["-p", profile])
        cmd.extend(["--report-dir", report_dir, "--no-browser"])

        if services:
            cmd.extend(["--services", *services.split(",")])

        stdout, stderr, rc = await _run_command(cmd, timeout=600)
        combined = stdout + stderr

        results = _parse_scoutsuite_results(report_dir)

        facts.append({"trait": "cloud.critical_count", "value": str(results["critical"])})
        facts.append({"trait": "cloud.high_count", "value": str(results["high"])})

        for finding in results["findings"][:20]:
            facts.append({"trait": "cloud.audit_finding", "value": json.dumps(finding)})

        for line in combined.splitlines():
            stripped = line.strip()
            if re.search(r"(danger|warning|critical|high)", stripped, re.IGNORECASE):
                if "finding" in stripped.lower() or "rule" in stripped.lower():
                    facts.append({"trait": "cloud.audit_finding", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def scoutsuite_service_check(
    provider: str = "aws",
    profile: str = "default",
    service: str = "iam",
) -> str:
    """Single service deep security check.

    Args:
        provider: Cloud provider (aws, azure, gcp, aliyun, oci)
        profile: AWS profile or cloud credential identifier
        service: Service to audit (e.g. iam, s3, ec2, rds, lambda, cloudtrail)

    Returns:
        JSON with facts: cloud.service_finding, cloud.misconfiguration
    """
    facts: list[dict[str, str]] = []

    try:
        report_dir = f"{REPORT_DIR}/{provider}-{service}"
        os.makedirs(report_dir, exist_ok=True)

        cmd = ["scout", provider]
        if provider == "aws":
            cmd.extend(["-p", profile])
        cmd.extend(["--services", service, "--report-dir", report_dir, "--no-browser"])

        stdout, stderr, rc = await _run_command(cmd, timeout=300)
        combined = stdout + stderr

        results = _parse_scoutsuite_results(report_dir)

        for finding in results["findings"]:
            facts.append({"trait": "cloud.service_finding", "value": json.dumps(finding)})
            if finding.get("level") in ("danger", "warning"):
                facts.append({
                    "trait": "cloud.misconfiguration",
                    "value": f"{service}:{finding['rule']} ({finding['level']})",
                })

        for line in combined.splitlines():
            stripped = line.strip()
            if re.search(r"(finding|rule|check)", stripped, re.IGNORECASE):
                if re.search(r"(fail|danger|warning)", stripped, re.IGNORECASE):
                    facts.append({"trait": "cloud.misconfiguration", "value": stripped[:200]})

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

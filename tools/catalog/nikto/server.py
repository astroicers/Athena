"""athena-nikto-mcp — FastMCP MCP container. Returns {"facts": [...]} format.

Tool: nikto_scan — HTTP vulnerability scan via nikto -h
MITRE ATT&CK: T1190 (Exploit Public-Facing Application)

Trait naming:
  scan.target              target host scanned
  scan.port                port used for scanning
  nikto.finding            individual vulnerability finding from nikto
  nikto.server             web server banner detected
  nikto.osvdb              OSVDB reference found
  nikto.ip                 resolved IP of the target
  scan.duration            scan duration in seconds
  scan.error               error message if scan failed

Security:
  - target validated against strict IP/hostname regex (no shell metacharacters)
  - port validated as integer in range 1-65535
  - no eval(), no raw user input passed to shell without validation
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("athena-nikto-mcp")

# ── validation ────────────────────────────────────────────────────────────────

# IPv4 / IPv6 / strict RFC-1123 hostname — no shell metacharacters
_TARGET_RE = re.compile(
    r"^(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}"                                       # IPv4
    r"|(?:[0-9a-fA-F:]+)"                                            # IPv6
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)"          # single label
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*"    # more labels
    r")$"
)

# Nikto output line patterns
_SERVER_RE = re.compile(r"^\+ Server:\s*(.+)", re.MULTILINE)
_TARGET_IP_RE = re.compile(r"^\+ Target IP:\s*([\d.a-fA-F:]+)", re.MULTILINE)
_OSVDB_RE = re.compile(r"OSVDB-(\d+)")
_FINDING_RE = re.compile(r"^\+ (.+)", re.MULTILINE)
_DURATION_RE = re.compile(r"(\d+) second", re.IGNORECASE)

# Lines to skip when collecting generic findings
_SKIP_PREFIXES = (
    "Target IP:",
    "Target Hostname:",
    "Target Port:",
    "Start Time:",
    "Server:",
    "End Time:",
    "1 host(s) tested",
    "-----------",
    "Nikto v",
    "SSL Info:",
    "+ No web server found",
    "0 error(s) and",
)


def _validate_target(target: str) -> str | None:
    """Return None if valid, error string if invalid."""
    if not target or len(target) > 253:
        return "target must be a non-empty string of at most 253 characters"
    if not _TARGET_RE.match(target):
        return (
            f"target '{target}' contains invalid characters or is not a valid "
            "IP/hostname"
        )
    return None


def _validate_port(port: int) -> str | None:
    """Return None if valid, error string if invalid."""
    if not (1 <= port <= 65535):
        return f"port {port} is out of valid range 1-65535"
    return None


# ── async subprocess helper ───────────────────────────────────────────────────


async def _run(cmd: str, timeout: int = 300) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (stdout + stderr).decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return "timeout"


# ── fact builder ──────────────────────────────────────────────────────────────


def _parse_nikto_output(
    raw: str,
    target: str,
    port: int,
    elapsed: float,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []

    # Always include scan target and port
    facts.append({"trait": "scan.target", "value": target, "confidence": 100})
    facts.append({"trait": "scan.port", "value": str(port), "confidence": 100})
    facts.append(
        {"trait": "scan.duration", "value": f"{elapsed:.1f}s", "confidence": 100}
    )

    if raw == "timeout":
        facts.append(
            {
                "trait": "scan.error",
                "value": "nikto scan timed out",
                "confidence": 100,
            }
        )
        return facts

    # Resolved IP
    ip_match = _TARGET_IP_RE.search(raw)
    if ip_match:
        facts.append(
            {"trait": "nikto.ip", "value": ip_match.group(1).strip(), "confidence": 95}
        )

    # Web server banner
    server_match = _SERVER_RE.search(raw)
    if server_match:
        facts.append(
            {
                "trait": "nikto.server",
                "value": server_match.group(1).strip(),
                "confidence": 90,
            }
        )

    # OSVDB references
    for osvdb in _OSVDB_RE.findall(raw):
        facts.append(
            {
                "trait": "nikto.osvdb",
                "value": f"OSVDB-{osvdb}",
                "confidence": 85,
            }
        )

    # Generic finding lines (nikto prefixes each finding with "+ ")
    seen: set[str] = set()
    for match in _FINDING_RE.finditer(raw):
        text = match.group(1).strip()
        if not text or text in seen:
            continue
        # Skip header/metadata lines
        if any(text.startswith(skip) for skip in _SKIP_PREFIXES):
            continue
        seen.add(text)
        facts.append(
            {
                "trait": "nikto.finding",
                "value": text,
                "confidence": 80,
            }
        )

    # If no findings at all beyond metadata, note it
    finding_count = sum(1 for f in facts if f["trait"] == "nikto.finding")
    if finding_count == 0 and "No web server found" not in raw and raw != "timeout":
        facts.append(
            {
                "trait": "nikto.finding",
                "value": "no vulnerabilities found",
                "confidence": 70,
            }
        )

    return facts


# ── MCP tool ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def nikto_scan(
    target: str,
    port: int = 80,
) -> dict[str, Any]:
    """Perform an HTTP vulnerability scan against a web target using nikto.

    MITRE ATT&CK: T1190 — Exploit Public-Facing Application.

    Args:
        target: IP address or hostname of the web server to scan.
        port:   TCP port to scan (default: 80). Use 443 for HTTPS.

    Returns:
        {"facts": [...]} with nikto findings as individual fact entries.
    """
    # Input validation
    err = _validate_target(target)
    if err:
        return {
            "facts": [
                {"trait": "scan.target", "value": target, "confidence": 0},
                {"trait": "scan.error", "value": err, "confidence": 100},
            ]
        }

    err = _validate_port(port)
    if err:
        return {
            "facts": [
                {"trait": "scan.target", "value": target, "confidence": 100},
                {"trait": "scan.error", "value": err, "confidence": 100},
            ]
        }

    # Determine SSL flag
    ssl_flag = "-ssl" if port == 443 else ""

    # Build nikto command — safe because target and port are validated
    # -nointeractive: no prompts; -ask no: disable interactive questions
    # -Format txt: plain text output for easy parsing
    cmd = (
        f"nikto -h {target} -p {port} {ssl_flag} "
        f"-nointeractive -ask no -Format txt -output /dev/stdout 2>&1"
    ).strip()

    start = time.monotonic()
    raw = await _run(cmd, timeout=300)
    elapsed = time.monotonic() - start

    facts = _parse_nikto_output(raw, target, port, elapsed)
    return {"facts": facts}


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Allow CLI override of transport/host/port (matches CMD in Dockerfile)
    # but FastMCP.run() handles those kwargs directly when called programmatically.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9106)

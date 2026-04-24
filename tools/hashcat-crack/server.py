"""hashcat-crack MCP Server for Athena.

Hash cracking with Hashcat: AS-REP Roasting (-m 18200),
Kerberoasting (-m 13100), NTLM (-m 1000), and session status.
Uses start/status model for long-running crack sessions.
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

mcp = FastMCP("athena-hashcat-crack", transport_security=_security)

DEFAULT_WORDLIST = "/usr/share/wordlists/rockyou.txt"
HASHCAT_OUTPUT_DIR = "/tmp/hashcat-output"

_active_sessions: dict[str, dict] = {}


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


async def _run_hashcat(
    hash_mode: int,
    hash_file: str,
    wordlist: str,
    rules: str,
    session_name: str,
    timeout: int = 600,
) -> tuple[list[dict[str, str]], str]:
    """Common hashcat execution logic."""
    facts: list[dict[str, str]] = []
    os.makedirs(HASHCAT_OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(HASHCAT_OUTPUT_DIR, f"{session_name}.pot")

    cmd = [
        "hashcat",
        "-m", str(hash_mode),
        hash_file,
        wordlist,
        "-o", output_file,
        "--session", session_name,
        "--potfile-disable",
        "--force",
    ]
    if rules:
        cmd.extend(["-r", rules])

    stdout, stderr, rc = await _run_command(cmd, timeout=timeout)
    combined = stdout + stderr

    # Parse cracked results from output file
    if os.path.exists(output_file):
        with open(output_file) as f:
            for line in f:
                stripped = line.strip()
                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    facts.append({
                        "trait": "credential.cracked_password",
                        "value": json.dumps({
                            "hash": parts[0][:80] + "..." if len(parts[0]) > 80 else parts[0],
                            "password": parts[1] if len(parts) > 1 else "",
                            "mode": hash_mode,
                        }),
                    })

    # Also parse inline "Cracked" results from stdout
    cracked_re = re.compile(r"^(.+?):(.+)$", re.MULTILINE)
    if "Cracked" in combined or "Recovered" in combined:
        for line in combined.splitlines():
            if ":" in line and not line.startswith("[") and not line.startswith("Session"):
                match = cracked_re.match(line.strip())
                if match:
                    hash_val = match.group(1)
                    pw_val = match.group(2)
                    # Avoid duplicate if already in file
                    if not any(
                        pw_val in f.get("value", "")
                        for f in facts
                    ):
                        facts.append({
                            "trait": "credential.cracked_password",
                            "value": json.dumps({
                                "hash": hash_val[:80],
                                "password": pw_val,
                                "mode": hash_mode,
                            }),
                        })

    return facts, combined


@mcp.tool()
async def hashcat_crack_asrep(
    hash_file: str,
    wordlist: str = DEFAULT_WORDLIST,
    rules: str = "",
    timeout: int = 600,
) -> str:
    """Crack AS-REP Roasting hashes (hashcat mode 18200).

    Args:
        hash_file: Path to file containing AS-REP hashes ($krb5asrep$...)
        wordlist: Path to wordlist file (default: rockyou.txt)
        rules: Optional hashcat rules file path
        timeout: Maximum runtime in seconds (default: 600)

    Returns:
        JSON with facts: credential.cracked_password
    """
    try:
        facts, combined = await _run_hashcat(
            hash_mode=18200,
            hash_file=hash_file,
            wordlist=wordlist,
            rules=rules,
            session_name="asrep-crack",
            timeout=timeout,
        )

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
async def hashcat_crack_kerberoast(
    hash_file: str,
    wordlist: str = DEFAULT_WORDLIST,
    rules: str = "",
    timeout: int = 600,
) -> str:
    """Crack Kerberoasting hashes (hashcat mode 13100).

    Args:
        hash_file: Path to file containing Kerberos TGS hashes ($krb5tgs$...)
        wordlist: Path to wordlist file (default: rockyou.txt)
        rules: Optional hashcat rules file path
        timeout: Maximum runtime in seconds (default: 600)

    Returns:
        JSON with facts: credential.cracked_password
    """
    try:
        facts, combined = await _run_hashcat(
            hash_mode=13100,
            hash_file=hash_file,
            wordlist=wordlist,
            rules=rules,
            session_name="kerberoast-crack",
            timeout=timeout,
        )

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
async def hashcat_crack_ntlm(
    hash_file: str,
    wordlist: str = DEFAULT_WORDLIST,
    rules: str = "",
    timeout: int = 600,
) -> str:
    """Crack NTLM hashes (hashcat mode 1000).

    Args:
        hash_file: Path to file containing NTLM hashes
        wordlist: Path to wordlist file (default: rockyou.txt)
        rules: Optional hashcat rules file path
        timeout: Maximum runtime in seconds (default: 600)

    Returns:
        JSON with facts: credential.cracked_password
    """
    try:
        facts, combined = await _run_hashcat(
            hash_mode=1000,
            hash_file=hash_file,
            wordlist=wordlist,
            rules=rules,
            session_name="ntlm-crack",
            timeout=timeout,
        )

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
async def hashcat_status(
    session_id: str = "",
) -> str:
    """Check status of a running hashcat session or show potfile results.

    Args:
        session_id: Hashcat session name (e.g. asrep-crack, kerberoast-crack, ntlm-crack)

    Returns:
        JSON with facts: credential.crack_progress
    """
    facts: list[dict[str, str]] = []

    try:
        if session_id:
            cmd = ["hashcat", f"--session={session_id}", "--status", "--force"]
            stdout, stderr, rc = await _run_command(cmd, timeout=30)
            combined = stdout + stderr

            # Parse progress info
            progress_re = re.compile(r"Progress.*?:\s*(\d+)/(\d+)")
            speed_re = re.compile(r"Speed.*?:\s*(.+)")
            recovered_re = re.compile(r"Recovered.*?:\s*(\d+)/(\d+)")

            progress = ""
            speed = ""
            recovered = ""

            for line in combined.splitlines():
                pm = progress_re.search(line)
                if pm:
                    progress = f"{pm.group(1)}/{pm.group(2)}"
                sm = speed_re.search(line)
                if sm:
                    speed = sm.group(1).strip()
                rm = recovered_re.search(line)
                if rm:
                    recovered = f"{rm.group(1)}/{rm.group(2)}"

            facts.append({
                "trait": "credential.crack_progress",
                "value": json.dumps({
                    "session": session_id,
                    "progress": progress,
                    "speed": speed,
                    "recovered": recovered,
                }),
            })
        else:
            # List all output files
            combined = ""
            if os.path.isdir(HASHCAT_OUTPUT_DIR):
                for fname in os.listdir(HASHCAT_OUTPUT_DIR):
                    fpath = os.path.join(HASHCAT_OUTPUT_DIR, fname)
                    if os.path.isfile(fpath):
                        with open(fpath) as f:
                            content = f.read()
                        combined += f"=== {fname} ===\n{content}\n"
                        count = len([l for l in content.splitlines() if l.strip()])
                        facts.append({
                            "trait": "credential.crack_progress",
                            "value": json.dumps({
                                "session": fname.replace(".pot", ""),
                                "cracked_count": count,
                            }),
                        })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000] if "combined" in dir() else "",
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

"""privesc-scanner MCP Server for Athena.

Detects Linux/Windows privilege escalation vectors via SSH / WinRM.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import re

import asyncssh

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-xxx, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-privesc-scanner", transport_security=_security)

# Well-known SUID binaries that can be abused for privilege escalation
# Reference: GTFOBins (https://gtfobins.github.io/)
_SUID_ESCALATION_BINARIES = frozenset({
    "python", "python2", "python3",
    "perl", "ruby",
    "bash", "sh", "dash", "zsh", "csh",
    "vim", "vi", "nano",
    "find", "awk", "gawk", "mawk", "nawk",
    "less", "more", "man",
    "nmap",
    "gcc", "cc",
    "env", "strace", "ltrace",
    "cp", "mv", "tar", "zip", "unzip",
    "wget", "curl",
    "tee", "dd",
    "node", "php", "lua",
    "docker", "pkexec", "doas",
    "base64", "openssl",
    "systemctl", "journalctl",
})

# Kernel versions with known public exploits (major examples)
_KNOWN_VULNERABLE_KERNELS: list[tuple[str, str]] = [
    (r"2\.6\.(1[7-9]|2\d|3[0-9])", "CVE-2009-2692 (sock_sendpage)"),
    (r"2\.6\.3[2-9]", "CVE-2010-3904 (RDS)"),
    (r"3\.(0|1|2)\.", "CVE-2012-0056 (memfd)"),
    (r"3\.1[0-3]\.", "CVE-2014-0196 (pty race)"),
    (r"3\.1[3-9]\.|4\.[0-3]\.", "CVE-2015-1328 (overlayfs)"),
    (r"4\.[0-9]\.|4\.1[0-3]\.", "CVE-2016-5195 (DirtyCow)"),
    (r"4\.4\.", "CVE-2017-6074 (DCCP double-free)"),
    (r"4\.14\.|4\.15\.|4\.16\.", "CVE-2018-14634 (integer overflow)"),
    (r"5\.[0-7]\.", "CVE-2019-13272 (ptrace_link)"),
    (r"5\.[8-9]\.|5\.1[0-6]\.", "CVE-2021-3156 (sudoedit Baron Samedit)"),
    (r"5\.[8-9]\.|5\.1[0-3]\.", "CVE-2022-0847 (DirtyPipe)"),
    (r"5\.1[5-9]\.|6\.0\.", "CVE-2023-0386 (OverlayFS fuse)"),
]

# Dangerous sudo rules (commands that can spawn a shell)
_SUDO_DANGEROUS_CMDS = frozenset({
    "ALL", "/bin/bash", "/bin/sh", "/usr/bin/python",
    "/usr/bin/python3", "/usr/bin/perl", "/usr/bin/ruby",
    "/usr/bin/vim", "/usr/bin/vi", "/usr/bin/less",
    "/usr/bin/more", "/usr/bin/man", "/usr/bin/find",
    "/usr/bin/awk", "/usr/bin/env", "/usr/bin/nmap",
    "/usr/bin/docker", "/usr/bin/pkexec",
})


async def _ssh_run(target: str, port: int, username: str, password: str,
                   command: str, timeout: int = 30) -> str:
    """Connect via SSH and run a command, returning stdout."""
    async with asyncssh.connect(
        target, port=port,
        username=username, password=password,
        known_hosts=None,
    ) as conn:
        result = await asyncio.wait_for(
            conn.run(command, check=False), timeout=timeout,
        )
        return result.stdout or ""


@mcp.tool()
async def linux_privesc_scan(
    target: str,
    username: str,
    password: str,
    port: int = 22,
) -> str:
    """SSH into target and detect privilege escalation vectors.

    Checks: SUID binaries, sudo rules, kernel version vs exploit DB.

    Args:
        target: IP address or hostname
        username: SSH username
        password: SSH password
        port: SSH port (default 22)

    Returns:
        JSON with facts: privesc.suid_binary, privesc.sudo_rule, privesc.kernel_vuln
    """
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    try:
        # ------- 1. SUID binary check -------
        suid_cmd = "find / -perm -4000 -type f 2>/dev/null | head -30"
        suid_output = await _ssh_run(target, port, username, password, suid_cmd)
        raw_parts.append(f"=== SUID binaries ===\n{suid_output}")

        for line in suid_output.strip().splitlines():
            path = line.strip()
            if not path:
                continue
            binary_name = path.rsplit("/", 1)[-1]
            if binary_name in _SUID_ESCALATION_BINARIES:
                facts.append({
                    "trait": "privesc.suid_binary",
                    "value": path,
                })

        # ------- 2. sudo rules -------
        sudo_cmd = "sudo -l 2>/dev/null"
        sudo_output = await _ssh_run(target, port, username, password, sudo_cmd)
        raw_parts.append(f"=== sudo -l ===\n{sudo_output}")

        for line in sudo_output.strip().splitlines():
            stripped = line.strip()
            # Lines like "(root) NOPASSWD: /usr/bin/vim"
            if "NOPASSWD" in stripped or "ALL" in stripped:
                # Extract the command portion after the last colon
                cmd_part = stripped.split(":")[-1].strip() if ":" in stripped else stripped
                for dangerous in _SUDO_DANGEROUS_CMDS:
                    if dangerous in cmd_part:
                        facts.append({
                            "trait": "privesc.sudo_rule",
                            "value": stripped,
                        })
                        break

        # ------- 3. Kernel version check -------
        kernel_cmd = "uname -r"
        kernel_output = await _ssh_run(target, port, username, password, kernel_cmd)
        raw_parts.append(f"=== kernel ===\n{kernel_output}")
        kernel_version = kernel_output.strip()

        for pattern, cve_name in _KNOWN_VULNERABLE_KERNELS:
            if re.search(pattern, kernel_version):
                facts.append({
                    "trait": "privesc.kernel_vuln",
                    "value": f"{kernel_version} -> {cve_name}",
                })

        return json.dumps({
            "facts": facts,
            "raw_output": "\n".join(raw_parts)[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def windows_privesc_scan(
    target: str,
    username: str,
    password: str,
    port: int = 5985,
) -> str:
    """WinRM into target and detect Windows privilege escalation vectors.

    Checks: token privileges, UAC level, scheduled tasks, unquoted service paths.

    Args:
        target: IP or hostname
        username: Windows username
        password: Windows password
        port: WinRM port (default 5985)

    Returns:
        JSON with facts: privesc.token_privilege, privesc.uac_level, privesc.scheduled_task
    """
    import winrm  # type: ignore[import-untyped]

    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    try:
        session = winrm.Session(
            f"http://{target}:{port}/wsman",
            auth=(username, password),
            transport="ntlm",
        )

        # ------- 1. Token privileges -------
        priv_result = session.run_cmd("whoami", ["/priv"])
        priv_output = priv_result.std_out.decode(errors="replace")
        raw_parts.append(f"=== whoami /priv ===\n{priv_output}")

        dangerous_privs = {
            "SeImpersonatePrivilege", "SeAssignPrimaryTokenPrivilege",
            "SeBackupPrivilege", "SeRestorePrivilege", "SeDebugPrivilege",
            "SeTakeOwnershipPrivilege", "SeLoadDriverPrivilege",
        }
        for line in priv_output.splitlines():
            for priv in dangerous_privs:
                if priv in line and "Enabled" in line:
                    facts.append({
                        "trait": "privesc.token_privilege",
                        "value": priv,
                    })

        # ------- 2. UAC level -------
        uac_result = session.run_cmd(
            "reg", [
                "query",
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "/v", "EnableLUA",
            ],
        )
        uac_output = uac_result.std_out.decode(errors="replace")
        raw_parts.append(f"=== UAC ===\n{uac_output}")

        if "0x0" in uac_output:
            uac_level = "disabled"
        elif "0x1" in uac_output:
            uac_level = "enabled"
        else:
            uac_level = "unknown"
        facts.append({"trait": "privesc.uac_level", "value": uac_level})

        # ------- 3. Scheduled tasks running as SYSTEM -------
        task_result = session.run_cmd(
            "schtasks", ["/query", "/fo", "CSV", "/v"],
        )
        task_output = task_result.std_out.decode(errors="replace")
        raw_parts.append(f"=== schtasks (truncated) ===\n{task_output[:2000]}")

        for line in task_output.splitlines():
            upper = line.upper()
            if "SYSTEM" in upper and "DISABLED" not in upper:
                # CSV fields: HostName,TaskName,...,Run As User,...
                parts = line.split(",")
                if len(parts) >= 2:
                    task_name = parts[1].strip('"').strip()
                    if task_name and task_name != "TaskName":
                        facts.append({
                            "trait": "privesc.scheduled_task",
                            "value": task_name,
                        })

        # ------- 4. Unquoted service paths -------
        svc_result = session.run_cmd(
            "wmic", [
                "service", "get",
                "name,displayname,pathname,startmode",
                "/format:csv",
            ],
        )
        svc_output = svc_result.std_out.decode(errors="replace")

        for line in svc_output.splitlines():
            if "C:\\" in line and '"' not in line:
                parts_svc = line.split(",")
                for part in parts_svc:
                    if " " in part and "C:\\" in part:
                        facts.append({
                            "trait": "privesc.unquoted_service_path",
                            "value": part.strip(),
                        })

        return json.dumps({
            "facts": facts,
            "raw_output": "\n".join(raw_parts)[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def check_writable_paths(
    target: str,
    username: str,
    password: str,
    port: int = 22,
) -> str:
    """Check for writable system paths that enable privilege escalation.

    Checks: PATH hijacking opportunities, writable cron directories.

    Args:
        target: IP or hostname
        username: SSH username
        password: SSH password
        port: SSH port (default 22)

    Returns:
        JSON with facts: privesc.writable_path, privesc.writable_cron
    """
    facts: list[dict[str, str]] = []
    raw_parts: list[str] = []

    try:
        # ------- 1. Writable PATH directories -------
        path_cmd = (
            "echo $PATH | tr ':' '\\n' | "
            "while read p; do [ -w \"$p\" ] && echo \"WRITABLE: $p\"; done"
        )
        path_output = await _ssh_run(target, port, username, password, path_cmd)
        raw_parts.append(f"=== writable PATH dirs ===\n{path_output}")

        for line in path_output.strip().splitlines():
            if line.startswith("WRITABLE:"):
                writable_dir = line.split(":", 1)[1].strip()
                facts.append({
                    "trait": "privesc.writable_path",
                    "value": writable_dir,
                })

        # ------- 2. Writable cron directories / files -------
        cron_cmd = (
            "for d in /etc/cron.d /etc/cron.daily /etc/cron.hourly "
            "/etc/cron.weekly /etc/cron.monthly /var/spool/cron /var/spool/cron/crontabs; do "
            "[ -w \"$d\" ] 2>/dev/null && echo \"WRITABLE_DIR: $d\"; "
            "done; "
            "[ -w /etc/crontab ] 2>/dev/null && echo \"WRITABLE_FILE: /etc/crontab\"; "
            "ls -la /etc/cron.d/ /var/spool/cron/ /etc/crontab 2>/dev/null"
        )
        cron_output = await _ssh_run(target, port, username, password, cron_cmd)
        raw_parts.append(f"=== writable cron ===\n{cron_output}")

        for line in cron_output.strip().splitlines():
            if line.startswith("WRITABLE_DIR:") or line.startswith("WRITABLE_FILE:"):
                writable_path = line.split(":", 1)[1].strip()
                facts.append({
                    "trait": "privesc.writable_cron",
                    "value": writable_path,
                })

        # ------- 3. World-writable /etc files -------
        etc_cmd = "find /etc -writable -type f 2>/dev/null | head -15"
        etc_output = await _ssh_run(target, port, username, password, etc_cmd)
        raw_parts.append(f"=== writable /etc files ===\n{etc_output}")

        for line in etc_output.strip().splitlines():
            path = line.strip()
            if path:
                facts.append({
                    "trait": "privesc.writable_path",
                    "value": path,
                })

        return json.dumps({
            "facts": facts,
            "raw_output": "\n".join(raw_parts)[:4000],
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

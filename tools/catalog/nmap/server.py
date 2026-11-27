"""
athena-nmap-mcp — Nmap MCP container (FastMCP, streamable-http)

Capability-first design:
  nmap_scan         — full nmap capability with configurable scan_type/scripts/os_detect/timing
  nmap_vuln_scan    — semantic shortcut: NSE vuln scripts (preset-driven)
  nmap_udp_scan     — semantic shortcut: UDP service discovery (preset-driven)
  nmap_os_detect    — semantic shortcut: OS fingerprinting (preset-driven)
  nmap_stealth_scan — semantic shortcut: low-noise SYN scan (preset-driven)
  nmap_full_scan    — semantic shortcut: complete scan (preset-driven)

Semantic shortcut tools fetch their parameters from Athena's preset API
(GET /api/tools/nmap_scan/presets/{name}); they fall back to embedded defaults
if the API is unreachable. This lets operators tune scan behavior at runtime
without rebuilding the image.

Returns {"facts": [...]} format.

Trait naming:
  network.host.ip          IP address of the live host
  host.os.guess            OS guess string (with -O)
  host.os.cpe              CPE OS identifier (with -O)
  service.open_port        {port}/{proto}/{service_name}
  service.{port}.version   "{product} {version}"
  vuln.{port}.{script}     NSE script vuln finding
  service.{port}.script.{name}  generic NSE script output

Security:
  - target validated against strict IP/hostname/CIDR regex (no shell metacharacters)
  - scan_type restricted to known nmap scan flags
  - scripts restricted to NSE categories or allowlisted script names
  - extra_flags filtered against an allowlist of non-dangerous flags
"""

from __future__ import annotations

import os
import re
import time

import aiohttp
import nmap
from fastmcp import FastMCP

mcp = FastMCP("athena-nmap-mcp")

ATHENA_API = os.environ.get(
    "ATHENA_API_URL", "http://athena.athena-system.svc.cluster.local:58000"
)

# ── validation ────────────────────────────────────────────────────────────────

# IPv4 / IPv4-CIDR / IPv6 / strict RFC-1123 hostname — no shell metacharacters
_TARGET_RE = re.compile(
    r"^(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?"   # IPv4 with optional CIDR
    r"|(?:[0-9a-fA-F:]+)"                       # IPv6
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)"
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*"
    r")$"
)

# Port spec: "80", "22-1024", "80,443,8080", "1-65535", or "top200"/"top1000"
_PORTS_RE = re.compile(r"^(?:[\d,\-]+|top\d+)$")

_MAX_PORT = 65535

# Allowed scan types (the -sX flag). Only safe/standard scan modes.
_ALLOWED_SCAN_TYPES = frozenset({
    "sV",  # version detection (TCP connect + version)
    "sS",  # SYN stealth scan
    "sU",  # UDP scan
    "sA",  # ACK scan (firewall mapping)
    "sN",  # Null scan
    "sX",  # Xmas scan
    "sF",  # FIN scan
    "sT",  # TCP connect
    "sn",  # ping scan / host discovery (no port scan)
})

# Allowed NSE script categories and specific scripts.
_ALLOWED_SCRIPTS = frozenset({
    # categories
    "vuln", "auth", "discovery", "safe", "default", "version",
    # specific scripts
    "http-title", "http-headers", "http-methods", "http-enum",
    "ftp-vsftpd-backdoor", "ftp-bounce", "ftp-anon",
    "smb-vuln-ms17-010", "smb-vuln-ms08-067", "smb-security-mode",
    "smb-enum-shares", "smb-os-discovery",
    "ssh-hostkey", "ssh-auth-methods", "ssh2-enum-algos",
    "ssl-cert", "ssl-enum-ciphers", "ssl-heartbleed",
    "dns-zone-transfer", "dns-recursion",
    "mysql-info", "mysql-empty-password",
    "rdp-ntlm-info", "rdp-enum-encryption",
    "banner",
})

# Allowed additional flags (non-dangerous; no scripts/output redirection).
_ALLOWED_EXTRA_FLAGS = frozenset({
    "--open", "--traceroute", "-v", "-vv",
    "--version-intensity", "--version-light", "--version-all",
    "--reason", "--packet-trace",
    "--max-retries", "--host-timeout",
    "--min-rate", "--max-rate",
    "-f", "--mtu",
    "--data-length", "--ttl",
    "--spoof-mac",
    "--osscan-guess", "--osscan-limit",
})


def _validate_target(target: str) -> str | None:
    if not target or len(target) > 253:
        return "target must be a non-empty string of at most 253 characters"
    if not _TARGET_RE.match(target):
        return f"target '{target}' contains invalid characters or is not a valid IP/hostname/CIDR"
    # Cap CIDR size: reject prefixes wider than /16 (65k hosts) to avoid a single
    # call scanning an enormous range. Athena's scope validator is the real boundary,
    # but this caps blast radius per call.
    if "/" in target:
        try:
            prefix = int(target.rsplit("/", 1)[1])
            if prefix < 16:
                return f"CIDR prefix /{prefix} too wide; use /16 or narrower"
        except ValueError:
            return f"invalid CIDR prefix in '{target}'"
    return None


def _validate_ports(ports: str) -> str | None:
    if not ports:
        return None  # empty = let nmap default
    if not _PORTS_RE.match(ports):
        return f"ports '{ports}' must be digits/commas/hyphens or 'topN'"
    if ports.startswith("top"):
        return None
    for part in ports.split(","):
        for b in part.split("-"):
            if not b.isdigit():
                return f"port token '{b}' is not a number"
            if int(b) > _MAX_PORT:
                return f"port {b} exceeds maximum {_MAX_PORT}"
    return None


# Value-token shape: alphanumerics, dot, colon, percent (timeouts like "300s", MACs).
# Rejects shell metacharacters even though python-nmap does not invoke a shell.
_FLAG_VALUE_RE = re.compile(r"^[A-Za-z0-9.:%]+$")
_VALUE_FLAGS = frozenset({
    "--version-intensity", "--max-retries", "--host-timeout",
    "--min-rate", "--max-rate", "--mtu", "--data-length",
    "--ttl", "--spoof-mac",
})


def _filter_extra_flags(extra: str) -> str:
    """Keep only allowlisted flags from a free-form extra_flags string.
    Value-taking flags only keep their value if it matches a strict shape."""
    if not extra:
        return ""
    tokens = extra.split()
    kept: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _ALLOWED_EXTRA_FLAGS:
            if tok in _VALUE_FLAGS:
                # Require a well-formed value token; drop the flag entirely if absent/malformed.
                if i + 1 < len(tokens) and _FLAG_VALUE_RE.match(tokens[i + 1]):
                    kept.append(tok)
                    kept.append(tokens[i + 1])
                    i += 1
                # else: skip the value-flag (no valid argument)
            else:
                kept.append(tok)
        i += 1
    return " ".join(kept)


def _validate_scripts(scripts: str) -> str | None:
    """Validate NSE script names against the allowlist."""
    if not scripts:
        return None
    for s in scripts.split(","):
        s = s.strip()
        if s and s not in _ALLOWED_SCRIPTS:
            return f"NSE script '{s}' is not in the allowlist"
    return None


# ── fact builders ─────────────────────────────────────────────────────────────

def _error_fact(msg: str) -> dict:
    return {"facts": [{"trait": "error", "value": msg}]}


def _parse_nmap_result(nm: nmap.PortScanner) -> list[dict]:
    """Walk the nmap result tree and produce structured facts."""
    facts: list[dict] = []

    for host in nm.all_hosts():
        facts.append({"trait": "network.host.ip", "value": host, "confidence": 100})

        # OS detection (with -O)
        osmatch = nm[host].get("osmatch", [])
        if osmatch:
            best = osmatch[0]
            facts.append({
                "trait": "host.os.guess",
                "value": best.get("name", ""),
                "confidence": int(best.get("accuracy", 0)),
            })
            # CPE from osclass
            for oc in best.get("osclass", []):
                for cpe in oc.get("cpe", []):
                    facts.append({
                        "trait": "host.os.cpe",
                        "value": cpe,
                        "confidence": int(oc.get("accuracy", 0)),
                    })

        # Host-level NSE scripts (hostscript)
        for hs in nm[host].get("hostscript", []):
            name = hs.get("id", "script")
            out = (hs.get("output", "") or "").strip()
            if out:
                facts.append({
                    "trait": f"host.script.{name}",
                    "value": out[:512],
                    "confidence": 80,
                })

        # Port facts
        for proto in nm[host].all_protocols():
            for port in sorted(nm[host][proto].keys()):
                pd = nm[host][proto][port]
                state = pd.get("state", "")
                if state != "open" and state != "open|filtered":
                    continue

                service_name = pd.get("name", "unknown") or "unknown"
                facts.append({
                    "trait": "service.open_port",
                    "value": f"{port}/{proto}/{service_name}",
                    "confidence": 90,
                })

                product = pd.get("product", "").strip()
                version = pd.get("version", "").strip()
                extrainfo = pd.get("extrainfo", "").strip()
                banner_parts = [p for p in (product, version) if p]
                if banner_parts:
                    facts.append({
                        "trait": f"service.{port}.version",
                        "value": " ".join(banner_parts),
                        "confidence": 85,
                    })
                if extrainfo:
                    facts.append({
                        "trait": f"service.{port}.extrainfo",
                        "value": extrainfo,
                        "confidence": 75,
                    })

                # Port-level NSE scripts
                for sname, sout in pd.get("script", {}).items():
                    sout = (sout or "").strip()
                    if not sout:
                        continue
                    # vuln-category scripts → vuln.* trait at higher confidence
                    if "vuln" in sname or "VULNERABLE" in sout:
                        facts.append({
                            "trait": f"vuln.{port}.{sname}",
                            "value": sout[:512],
                            "confidence": 90,
                        })
                    else:
                        facts.append({
                            "trait": f"service.{port}.script.{sname}",
                            "value": sout[:512],
                            "confidence": 75,
                        })

    return facts


# ── core capability tool ──────────────────────────────────────────────────────

def _nmap_scan_impl(
    target: str,
    ports: str = "1-1024",
    scan_type: str = "sV",
    os_detect: bool = False,
    scripts: str = "",
    timing: int = 3,
    extra_flags: str = "",
) -> dict:
    """Core nmap execution shared by nmap_scan and the semantic shortcut tools."""
    err = _validate_target(target)
    if err:
        return _error_fact(err)

    if scan_type not in _ALLOWED_SCAN_TYPES:
        return _error_fact(f"scan_type '{scan_type}' not allowed; use one of {sorted(_ALLOWED_SCAN_TYPES)}")

    err = _validate_ports(ports)
    if err:
        return _error_fact(err)

    err = _validate_scripts(scripts)
    if err:
        return _error_fact(err)

    timing = max(0, min(5, int(timing)))

    # Build nmap argument string
    args = [f"-{scan_type}", f"-T{timing}"]
    if scan_type != "sn":  # sn (ping scan) takes no port/service flags
        if os_detect:
            args.append("-O")
        if scripts:
            args.append(f"--script {scripts}")
    extra = _filter_extra_flags(extra_flags)
    if extra:
        args.append(extra)
    # Always cap host runtime unless caller overrode it
    if "--host-timeout" not in extra:
        args.append("--host-timeout 600s")
    arg_str = " ".join(args)

    # Translate topN port spec
    scan_ports = None if (ports.startswith("top") or scan_type == "sn") else ports
    if ports.startswith("top"):
        n = ports[3:]
        arg_str += f" --top-ports {n}"

    try:
        nm = nmap.PortScanner()
        nm.scan(hosts=target, ports=scan_ports, arguments=arg_str, timeout=650)
    except nmap.PortScannerError as exc:
        return _error_fact(f"nmap execution error: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _error_fact(f"unexpected error during scan: {exc}")

    facts = _parse_nmap_result(nm)
    if not facts:
        facts.append({"trait": "scan.target", "value": target, "confidence": 100})
    return {"facts": facts}


@mcp.tool()
def nmap_scan(
    target: str,
    ports: str = "1-1024",
    scan_type: str = "sV",
    os_detect: bool = False,
    scripts: str = "",
    timing: int = 3,
    extra_flags: str = "",
) -> dict:
    """T1046/T1595: Full nmap scan with configurable flags.

    Combine scan_type, os_detect, and scripts for complete coverage.

    Args:
        target:     IP, CIDR, or hostname (no shell metacharacters).
        ports:      Port spec: "1-1024", "80,443", "1-65535", or "top200".
        scan_type:  sV (version)|sS (SYN)|sU (UDP)|sA (ACK)|sN (Null)|sX|sF|sT|sn (ping).
        os_detect:  Enable -O OS fingerprinting.
        scripts:    NSE scripts/categories: "vuln", "auth", "discovery", or specific names.
        timing:     -T0 (paranoid) to -T5 (insane); default 3.
        extra_flags: Additional allowlisted flags (e.g. "-f --version-all").

    Returns:
        {"facts": [{"trait": "service.open_port", "value": "22/tcp/ssh", "confidence": 90}, ...]}
    """
    return _nmap_scan_impl(target, ports, scan_type, os_detect, scripts, timing, extra_flags)


# ── preset helper for semantic shortcut tools ─────────────────────────────────

_preset_cache: dict[str, dict] = {}

_DEFAULT_PRESETS = {
    "vuln_scan":     {"scan_type": "sV", "ports": "80,443,22,21,8080,3389,139,445", "scripts": "vuln"},
    "udp_scan":      {"scan_type": "sU", "ports": "53,67,68,69,111,123,137,161,500,514"},
    "os_detect":     {"scan_type": "sV", "os_detect": True, "ports": "1-1024"},
    "stealth":       {"scan_type": "sS", "timing": 1, "ports": "1-1024"},
    "full":          {"scan_type": "sV", "os_detect": True, "ports": "1-65535"},
    "host_discover": {"scan_type": "sn"},
}


async def _get_preset(preset_name: str) -> dict:
    """Fetch nmap_scan preset params from Athena API (cached 60s; falls back to defaults)."""
    cached = _preset_cache.get(preset_name)
    if cached and time.time() - cached.get("_ts", 0) < 60:
        return cached
    try:
        async with aiohttp.ClientSession() as s:
            url = f"{ATHENA_API}/api/tools/nmap_scan/presets/{preset_name}"
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=3)) as r:
                if r.status == 200:
                    body = await r.json()
                    params = body.get("params", {})
                    if isinstance(params, dict):
                        params = dict(params)
                        params["_ts"] = time.time()
                        _preset_cache[preset_name] = params
                        return params
    except Exception:
        pass
    return dict(_DEFAULT_PRESETS.get(preset_name, {}))


# ── semantic shortcut tools (preset-driven) ───────────────────────────────────

@mcp.tool()
async def nmap_vuln_scan(target: str) -> dict:
    """T1190/T1203: NSE vulnerability scan. Use after a port scan to find CVEs on services.
    Behavior is configurable via the 'vuln_scan' preset (GET /api/tools/nmap_scan/presets/vuln_scan)."""
    p = await _get_preset("vuln_scan")
    return _nmap_scan_impl(
        target,
        ports=p.get("ports", "80,443,22,21,8080"),
        scan_type=p.get("scan_type", "sV"),
        scripts=p.get("scripts", "vuln"),
        timing=int(p.get("timing", 3)),
    )


@mcp.tool()
async def nmap_udp_scan(target: str) -> dict:
    """T1046: UDP service discovery. Run after TCP scan; finds DNS/SNMP/NFS/TFTP.
    Behavior is configurable via the 'udp_scan' preset."""
    p = await _get_preset("udp_scan")
    return _nmap_scan_impl(
        target,
        ports=p.get("ports", "53,111,123,161,500"),
        scan_type="sU",
        timing=int(p.get("timing", 3)),
    )


@mcp.tool()
async def nmap_os_detect(target: str) -> dict:
    """T1082: OS fingerprinting. Use to confirm OS before selecting OS-specific exploits.
    Behavior is configurable via the 'os_detect' preset."""
    p = await _get_preset("os_detect")
    return _nmap_scan_impl(
        target,
        ports=p.get("ports", "1-1024"),
        scan_type=p.get("scan_type", "sV"),
        os_detect=True,
        extra_flags="--osscan-guess",
        timing=int(p.get("timing", 3)),
    )


@mcp.tool()
async def nmap_stealth_scan(target: str, ports: str = "1-1024") -> dict:
    """T1595: Low-noise SYN scan with slow timing. Use in environments with IDS/firewall.
    Timing is configurable via the 'stealth' preset."""
    p = await _get_preset("stealth")
    return _nmap_scan_impl(
        target,
        ports=ports,
        scan_type="sS",
        timing=int(p.get("timing", 1)),
        extra_flags="-f",
    )


@mcp.tool()
async def nmap_full_scan(target: str) -> dict:
    """T1046: Complete scan (all ports, services, OS). Use for thorough enumeration.
    Behavior is configurable via the 'full' preset."""
    p = await _get_preset("full")
    return _nmap_scan_impl(
        target,
        ports=p.get("ports", "1-65535"),
        scan_type=p.get("scan_type", "sV"),
        os_detect=bool(p.get("os_detect", True)),
        timing=int(p.get("timing", 3)),
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)

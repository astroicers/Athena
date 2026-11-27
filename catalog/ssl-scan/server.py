"""
athena-ssl-scan-mcp — FastMCP MCP container

Tools: ssl_scan
Returns {"facts": [...]} format.

Trait naming:
  ssl.cert.subject        Certificate subject CN
  ssl.cert.issuer         Certificate issuer CN
  ssl.cert.not_before     Validity start (ISO-8601)
  ssl.cert.not_after      Validity end (ISO-8601)
  ssl.cert.expired        "true" / "false"
  ssl.cert.days_remaining Days until expiry (negative = expired)
  ssl.cert.san            Subject Alternative Name entry (one per SAN)
  ssl.cert.serial         Certificate serial number (hex)
  ssl.cert.fingerprint    SHA-256 fingerprint of the certificate
  ssl.protocol.supported  TLS/SSL protocol version accepted by the server
  ssl.cipher.accepted     Cipher suite accepted by the server (one per cipher)
  ssl.cipher.preferred    Cipher suite the server prefers
  ssl.vulnerability       Known weakness detected (e.g. "BEAST", "POODLE", "ROBOT")

Security:
  - target validated against strict IP/hostname regex (no shell metacharacters)
  - port validated to 1-65535 range
  - uses Python ssl/socket stdlib for cert inspection + openssl CLI for cipher enumeration
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import re
import socket
import ssl
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("athena-ssl-scan-mcp")

# ── validation ────────────────────────────────────────────────────────────────

_TARGET_RE = re.compile(
    r"^(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}"                                           # IPv4
    r"|(?:[0-9a-fA-F:]+)"                                                 # IPv6
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)"              # single label
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*"        # more labels
    r")$"
)


def _validate_target(target: str) -> str | None:
    if not target or len(target) > 253:
        return "target must be a non-empty string of at most 253 characters"
    if not _TARGET_RE.match(target):
        return f"target '{target}' contains invalid characters or is not a valid IP/hostname"
    return None


def _validate_port(port: int) -> str | None:
    if port < 1 or port > 65535:
        return f"port {port} is out of valid range 1-65535"
    return None


def _error_fact(msg: str) -> dict:
    return {"facts": [{"trait": "error", "value": msg}]}


# ── certificate inspection (stdlib ssl) ───────────────────────────────────────

_TLS_PROTOCOLS = [
    ("TLSv1.3", ssl.TLSVersion.TLSv1_3),
    ("TLSv1.2", ssl.TLSVersion.TLSv1_2),
]

# Older protocol constants may not exist on all Python builds
try:
    _TLS_PROTOCOLS.append(("TLSv1.1", ssl.TLSVersion.TLSv1_1))
    _TLS_PROTOCOLS.append(("TLSv1.0", ssl.TLSVersion.TLSv1))
except AttributeError:
    pass


def _fetch_cert_facts(target: str, port: int) -> list[dict]:
    """Connect with stdlib ssl and extract certificate facts."""
    facts: list[dict] = []

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((target, port), timeout=10) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=target) as tls_sock:
                cert_der = tls_sock.getpeercert(binary_form=True)
                cert_dict: dict[str, Any] = tls_sock.getpeercert() or {}
                cipher_info = tls_sock.cipher()          # (name, proto, bits)
                proto_used = tls_sock.version()          # e.g. "TLSv1.3"
    except (ssl.SSLError, OSError, socket.timeout) as exc:
        facts.append({"trait": "error", "value": f"TLS connect failed: {exc}"})
        return facts

    # ── protocol negotiated ───────────────────────────────────────────────────
    if proto_used:
        facts.append({
            "trait": "ssl.protocol.supported",
            "value": proto_used,
            "confidence": 100,
        })

    # ── cipher preferred by server ────────────────────────────────────────────
    if cipher_info:
        facts.append({
            "trait": "ssl.cipher.preferred",
            "value": cipher_info[0],
            "confidence": 95,
        })

    # ── certificate fingerprint ───────────────────────────────────────────────
    if cert_der:
        sha256 = hashlib.sha256(cert_der).hexdigest().upper()
        fp_str = ":".join(sha256[i:i+2] for i in range(0, len(sha256), 2))
        facts.append({
            "trait": "ssl.cert.fingerprint",
            "value": fp_str,
            "confidence": 100,
        })

    # ── subject ───────────────────────────────────────────────────────────────
    subject = dict(x[0] for x in cert_dict.get("subject", []))
    cn = subject.get("commonName", "")
    if cn:
        facts.append({"trait": "ssl.cert.subject", "value": cn, "confidence": 100})

    # ── issuer ────────────────────────────────────────────────────────────────
    issuer = dict(x[0] for x in cert_dict.get("issuer", []))
    issuer_cn = issuer.get("commonName", "")
    if issuer_cn:
        facts.append({"trait": "ssl.cert.issuer", "value": issuer_cn, "confidence": 100})

    # ── serial ────────────────────────────────────────────────────────────────
    serial = cert_dict.get("serialNumber", "")
    if serial:
        facts.append({"trait": "ssl.cert.serial", "value": serial, "confidence": 100})

    # ── validity window ───────────────────────────────────────────────────────
    fmt = "%b %d %H:%M:%S %Y %Z"
    not_before_raw = cert_dict.get("notBefore", "")
    not_after_raw = cert_dict.get("notAfter", "")

    not_after_dt: datetime.datetime | None = None

    if not_before_raw:
        try:
            dt = datetime.datetime.strptime(not_before_raw, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
            facts.append({
                "trait": "ssl.cert.not_before",
                "value": dt.isoformat(),
                "confidence": 100,
            })
        except ValueError:
            facts.append({"trait": "ssl.cert.not_before", "value": not_before_raw, "confidence": 90})

    if not_after_raw:
        try:
            not_after_dt = datetime.datetime.strptime(not_after_raw, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
            facts.append({
                "trait": "ssl.cert.not_after",
                "value": not_after_dt.isoformat(),
                "confidence": 100,
            })
        except ValueError:
            facts.append({"trait": "ssl.cert.not_after", "value": not_after_raw, "confidence": 90})

    # ── expiry status ─────────────────────────────────────────────────────────
    if not_after_dt is not None:
        now = datetime.datetime.now(datetime.timezone.utc)
        days_remaining = (not_after_dt - now).days
        expired = days_remaining < 0
        facts.append({
            "trait": "ssl.cert.expired",
            "value": str(expired).lower(),
            "confidence": 100,
        })
        facts.append({
            "trait": "ssl.cert.days_remaining",
            "value": str(days_remaining),
            "confidence": 100,
        })

    # ── Subject Alternative Names ─────────────────────────────────────────────
    for san_type, san_value in cert_dict.get("subjectAltName", []):
        facts.append({
            "trait": "ssl.cert.san",
            "value": f"{san_type}:{san_value}",
            "confidence": 100,
        })

    return facts


# ── protocol probing ──────────────────────────────────────────────────────────

def _probe_protocols(target: str, port: int) -> list[dict]:
    """Probe which TLS/SSL protocol versions the server accepts."""
    facts: list[dict] = []

    for proto_name, tls_ver in _TLS_PROTOCOLS:
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.minimum_version = tls_ver
            ctx.maximum_version = tls_ver
            with socket.create_connection((target, port), timeout=5) as raw_sock:
                with ctx.wrap_socket(raw_sock, server_hostname=target):
                    facts.append({
                        "trait": "ssl.protocol.supported",
                        "value": proto_name,
                        "confidence": 95,
                    })
        except (ssl.SSLError, OSError, socket.timeout, AttributeError):
            pass  # protocol not supported or not available in this build

    return facts


# ── cipher enumeration via openssl CLI ────────────────────────────────────────

async def _run(cmd: str, timeout: int = 30) -> str:
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


_CIPHER_ACCEPTED_RE = re.compile(r"Cipher\s+is\s+(\S+)")
_CIPHER_NO_RE = re.compile(r"alert handshake failure|no ciphers available|sslv3 alert", re.I)

# Representative cipher list covering common suites
_CIPHER_PROBES = [
    # TLS 1.3
    "TLS_AES_256_GCM_SHA384",
    "TLS_AES_128_GCM_SHA256",
    "TLS_CHACHA20_POLY1305_SHA256",
    # TLS 1.2 ECDHE
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES256-SHA384",
    "ECDHE-RSA-AES128-SHA256",
    # TLS 1.2 DHE
    "DHE-RSA-AES256-GCM-SHA384",
    "DHE-RSA-AES128-GCM-SHA256",
    # Legacy / weak
    "AES256-SHA",
    "AES128-SHA",
    "DES-CBC3-SHA",
    "RC4-SHA",
    "RC4-MD5",
    "EXP-RC4-MD5",
    "NULL-SHA",
]


async def _enumerate_ciphers(target: str, port: int) -> list[dict]:
    """Use openssl s_client to probe individual cipher acceptance."""
    facts: list[dict] = []
    accepted: list[str] = []

    for cipher in _CIPHER_PROBES:
        cmd = (
            f"echo Q | openssl s_client -connect {target}:{port} "
            f"-cipher '{cipher}' -no_ign_eof 2>&1"
        )
        out = await _run(cmd, timeout=10)
        m = _CIPHER_ACCEPTED_RE.search(out)
        if m and m.group(1) not in ("0000", "(NONE)"):
            suite = m.group(1)
            accepted.append(suite)
            facts.append({
                "trait": "ssl.cipher.accepted",
                "value": suite,
                "confidence": 90,
            })

    return facts


# ── vulnerability heuristics ──────────────────────────────────────────────────

def _detect_vulnerabilities(
    protocol_facts: list[dict],
    cipher_facts: list[dict],
) -> list[dict]:
    """Apply heuristics to flag known SSL/TLS weaknesses."""
    facts: list[dict] = []

    supported_protos = {
        f["value"] for f in protocol_facts if f["trait"] == "ssl.protocol.supported"
    }
    accepted_ciphers = {
        f["value"] for f in cipher_facts if f["trait"] == "ssl.cipher.accepted"
    }

    # POODLE — SSLv3 accepted
    if "SSLv3" in supported_protos:
        facts.append({
            "trait": "ssl.vulnerability",
            "value": "POODLE (SSLv3 accepted)",
            "confidence": 95,
        })

    # BEAST — TLSv1.0 with CBC cipher
    cbc_ciphers = {c for c in accepted_ciphers if "CBC" in c or c.endswith("-SHA")}
    if "TLSv1.0" in supported_protos and cbc_ciphers:
        facts.append({
            "trait": "ssl.vulnerability",
            "value": "BEAST (TLSv1.0 + CBC cipher accepted)",
            "confidence": 80,
        })

    # Weak/export ciphers
    weak = {c for c in accepted_ciphers if c.startswith("EXP-") or "RC4" in c or "NULL" in c or "DES-CBC-" in c}
    for w in sorted(weak):
        facts.append({
            "trait": "ssl.vulnerability",
            "value": f"WEAK_CIPHER ({w})",
            "confidence": 95,
        })

    # 3DES — SWEET32
    triple_des = {c for c in accepted_ciphers if "3DES" in c or "DES-CBC3" in c}
    if triple_des:
        facts.append({
            "trait": "ssl.vulnerability",
            "value": "SWEET32 (3DES cipher accepted)",
            "confidence": 85,
        })

    return facts


# ── tool ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def ssl_scan(target: str, port: int = 443) -> dict:
    """T1040, T1596.003: TLS/SSL certificate and cipher suite analysis.

    Performs a comprehensive SSL/TLS inspection of the target:
      - Certificate metadata (subject, issuer, SANs, validity, fingerprint)
      - Expiry status and days remaining
      - Supported protocol versions (TLS 1.0–1.3)
      - Accepted cipher suites (via openssl s_client probing)
      - Vulnerability heuristics (POODLE, BEAST, SWEET32, weak/export ciphers)

    Args:
        target: IP address or hostname to scan.
        port:   TCP port to connect to (default 443).

    Returns:
        {"facts": [{"trait": "ssl.cert.subject", "value": "...", "confidence": 100}, ...]}
    """
    err = _validate_target(target)
    if err:
        return _error_fact(err)

    err = _validate_port(port)
    if err:
        return _error_fact(err)

    facts: list[dict] = [
        {"trait": "scan.target", "value": f"{target}:{port}", "confidence": 100}
    ]

    # 1. Certificate + negotiated protocol/cipher (stdlib, synchronous but fast)
    loop = asyncio.get_event_loop()
    cert_facts = await loop.run_in_executor(None, _fetch_cert_facts, target, port)
    facts.extend(cert_facts)

    # If the connection itself failed, stop here
    if any(f["trait"] == "error" for f in cert_facts):
        return {"facts": facts}

    # 2. Protocol probing (synchronous, in executor to avoid blocking event loop)
    proto_facts = await loop.run_in_executor(None, _probe_protocols, target, port)
    # Deduplicate against what _fetch_cert_facts already found
    existing_protos = {f["value"] for f in facts if f["trait"] == "ssl.protocol.supported"}
    for pf in proto_facts:
        if pf["value"] not in existing_protos:
            facts.append(pf)
            existing_protos.add(pf["value"])

    # 3. Cipher enumeration (async, openssl CLI subprocess per cipher)
    cipher_facts = await _enumerate_ciphers(target, port)
    # Deduplicate preferred cipher that already appears in cipher_facts
    preferred = {f["value"] for f in facts if f["trait"] == "ssl.cipher.preferred"}
    seen_ciphers: set[str] = set()
    for cf in cipher_facts:
        if cf["value"] not in seen_ciphers:
            seen_ciphers.add(cf["value"])
            facts.append(cf)

    # 4. Vulnerability heuristics
    all_proto_facts = [f for f in facts if f["trait"] == "ssl.protocol.supported"]
    vuln_facts = _detect_vulnerabilities(all_proto_facts, cipher_facts)
    facts.extend(vuln_facts)

    return {"facts": facts}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9103)

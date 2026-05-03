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

DEFAULT_WORDLIST = "/wordlists/hashcat-custom.txt"
_FALLBACK_WORDLIST = "/usr/share/wordlists/rockyou.txt"
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


def _md4(data: bytes) -> bytes:
    """Pure-Python MD4 (needed because OpenSSL 3 disabled MD4 in hashlib)."""
    import struct

    def _lrot(x: int, n: int) -> int:
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    F = lambda x, y, z: (x & y) | (~x & z)
    G = lambda x, y, z: (x & y) | (x & z) | (y & z)
    H = lambda x, y, z: x ^ y ^ z

    msg = bytearray(data)
    orig_bit_len = len(data) * 8
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", orig_bit_len)

    A, B, C, D = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476

    for i in range(0, len(msg), 64):
        X = list(struct.unpack("<16I", msg[i:i + 64]))
        a, b, c, d = A, B, C, D

        # Round 1 — s values: 3,7,11,19
        for k, s in zip(range(16), [3,7,11,19,3,7,11,19,3,7,11,19,3,7,11,19]):
            A = _lrot((A + F(B, C, D) + X[k]) & 0xFFFFFFFF, s)
            A, B, C, D = D, A, B, C

        # Round 2 — s values: 3,5,9,13; index order 0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15
        for idx, k in enumerate([0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15]):
            s = [3,5,9,13][idx % 4]
            A = _lrot((A + G(B, C, D) + X[k] + 0x5A827999) & 0xFFFFFFFF, s)
            A, B, C, D = D, A, B, C

        # Round 3 — s values: 3,9,11,15; index order 0,8,4,12,2,10,6,14,1,9,5,13,3,11,7,15
        for idx, k in enumerate([0,8,4,12,2,10,6,14,1,9,5,13,3,11,7,15]):
            s = [3,9,11,15][idx % 4]
            A = _lrot((A + H(B, C, D) + X[k] + 0x6ED9EBA1) & 0xFFFFFFFF, s)
            A, B, C, D = D, A, B, C

        A = (A + a) & 0xFFFFFFFF
        B = (B + b) & 0xFFFFFFFF
        C = (C + c) & 0xFFFFFFFF
        D = (D + d) & 0xFFFFFFFF

    return struct.pack("<4I", A, B, C, D)


def _python_crack_asrep(hash_line: str, wordlist_path: str) -> str | None:
    """Pure-Python AS-REP hash cracker (fallback when hashcat has no GPU/OpenCL).
    Supports $krb5asrep$23$ format only — sufficient for lab use with small wordlists.
    """
    import hmac, hashlib, struct
    # Parse: $krb5asrep$23$user@DOMAIN:checksum$enc_part
    m = re.match(r"\$krb5asrep\$23\$[^:]+:([0-9a-fA-F]+)\$([0-9a-fA-F]+)", hash_line)
    if not m:
        return None
    checksum = bytes.fromhex(m.group(1))
    enc_part = bytes.fromhex(m.group(2))

    def _rc4_hmac_decrypt(key: bytes, data: bytes) -> bytes:
        k1 = hmac.new(key, struct.pack("<I", 8), hashlib.md5).digest()
        k3 = hmac.new(k1, data[:16], hashlib.md5).digest()
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + k3[i % 16]) % 256
            S[i], S[j] = S[j], S[i]
        i = j = 0
        out = []
        for byte in data[16:]:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            out.append(byte ^ S[(S[i] + S[j]) % 256])
        return bytes(out)

    data = checksum + enc_part
    try:
        with open(wordlist_path, errors="replace") as fh:
            for candidate in fh:
                candidate = candidate.rstrip("\n\r")
                nt_hash = _md4(candidate.encode("utf-16-le"))
                decrypted = _rc4_hmac_decrypt(nt_hash, data)
                k1 = hmac.new(nt_hash, struct.pack("<I", 8), hashlib.md5).digest()
                verify = hmac.new(k1, decrypted, hashlib.md5).digest()
                if verify == checksum:
                    return candidate
    except Exception:
        pass
    return None


async def _run_hashcat(
    hash_mode: int,
    hash_file: str,
    wordlist: str,
    rules: str,
    session_name: str,
    timeout: int = 600,
) -> tuple[list[dict[str, str]], str]:
    """Common hashcat execution logic."""
    # Prefer custom wordlist; fall back to rockyou if custom not mounted
    if wordlist == DEFAULT_WORDLIST and not os.path.exists(DEFAULT_WORDLIST):
        wordlist = _FALLBACK_WORDLIST
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

    # Python fallback: if hashcat produced nothing (no GPU/OpenCL), use pure-Python RC4-HMAC
    if not facts and hash_mode == 18200 and ("ATTENTION" in combined or "No devices found" in combined or rc != 0):
        try:
            with open(hash_file) as fhash:
                hash_lines = [l.strip() for l in fhash if l.strip().startswith("$krb5asrep$")]

            for hash_line in hash_lines:
                principal_m = re.search(r"\$krb5asrep\$\d+\$([^:]+):", hash_line)
                principal = principal_m.group(1) if principal_m else "unknown"
                cracked_pw = _python_crack_asrep(hash_line, wordlist)
                if cracked_pw:
                    facts.append({
                        "trait": "credential.cracked_password",
                        "value": json.dumps({
                            "hash": hash_line[:80] + "...",
                            "password": cracked_pw,
                            "mode": hash_mode,
                        }),
                    })
                    combined += f"\n[python-fallback] Cracked {principal}: {cracked_pw}"
        except Exception as py_exc:
            combined += f"\n[python-fallback] Error: {py_exc}"

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
    hash_file: str = "",
    hash_value: str = "",
    wordlist: str = DEFAULT_WORDLIST,
    rules: str = "",
    timeout: int = 600,
) -> str:
    """Crack Kerberoasting hashes (hashcat mode 13100).

    Args:
        hash_file: Path to file containing Kerberos TGS hashes ($krb5tgs$...).
                   Either hash_file or hash_value must be provided.
        hash_value: Inline hash string (written to a temp file automatically).
                    Use this when passing a hash directly instead of a file path.
        wordlist: Path to wordlist file (default: rockyou.txt)
        rules: Optional hashcat rules file path
        timeout: Maximum runtime in seconds (default: 600)

    Returns:
        JSON with facts: credential.cracked_password
    """
    try:
        tmp_path = None
        if not hash_file and hash_value:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(hash_value.strip() + "\n")
                tmp_path = f.name
            hash_file = tmp_path

        if not hash_file:
            return json.dumps({"facts": [], "raw_output": "", "error": {"type": "ValueError", "message": "Either hash_file or hash_value must be provided"}})

        # Auto-detect hash mode: AS-REP ($krb5asrep$) = 18200, Kerberoast ($krb5tgs$) = 13100
        detected_mode = 13100
        detected_hash = hash_value or ""
        if not detected_hash and os.path.exists(hash_file):
            with open(hash_file) as fh:
                detected_hash = fh.read(100)
        if "$krb5asrep$" in detected_hash:
            detected_mode = 18200

        facts, combined = await _run_hashcat(
            hash_mode=detected_mode,
            hash_file=hash_file,
            wordlist=wordlist,
            rules=rules,
            session_name="kerberoast-crack",
            timeout=timeout,
        )
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

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

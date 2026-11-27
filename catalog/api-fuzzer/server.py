"""
athena-api-fuzzer-mcp — REST/GraphQL API endpoint fuzzing MCP container (FastMCP, streamable-http)

3 tools covering T1190, T1595.002 (container=api-fuzzer):
  - api_fuzz: content/endpoint discovery against a target URL via ffuf, parsed into facts.
  - api_fuzz_params: POST-body/query-parameter value fuzzing against a fixed endpoint via ffuf.
  - graphql_introspect: GraphQL `__schema` introspection against a target endpoint.

All tools return {"facts": [...]} format.

Security boundaries:
  - target validated as an http(s) URL; control chars / shell metacharacters rejected
  - method restricted to an allowlist; match_codes restricted to digits+commas
  - wordlist path must resolve to an existing regular file
  - ffuf invoked via create_subprocess_exec (argv list, never shell=True) — no injection surface
  - GraphQL introspection uses a single fixed query body over stdlib urllib (no argv/shell
    surface at all); the request runs in a worker thread (asyncio.to_thread) since urllib is
    blocking, and the response body is read bounded (64KiB) to avoid unbounded memory use
  - any credentials embedded in a target URL (user:pass@host) are redacted before being
    echoed into a fact or log line
  - bounded timeout; on timeout/error a status fact is returned, never an exception
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("athena-api-fuzzer-mcp")

# ── constants ─────────────────────────────────────────────────────────────────

FFUF_BIN = os.environ.get("FFUF_BIN", "ffuf")
DEFAULT_WORDLIST = os.environ.get("API_FUZZ_WORDLIST", "/app/wordlist.txt")
DEFAULT_TIMEOUT = int(os.environ.get("FFUF_TIMEOUT", "180"))
FFUF_THREADS = os.environ.get("FFUF_THREADS", "40")
FFUF_REQ_TIMEOUT = os.environ.get("FFUF_REQ_TIMEOUT", "10")

TECHNIQUES = ("T1190", "T1595.002")

_METHOD_ALLOWLIST = {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}

# Target must be an http(s) URL. Disallow whitespace and control chars entirely.
_URL_RE = re.compile(r"^https?://[^\s\x00-\x1f\x7f]{1,2048}$", re.IGNORECASE)
# Match codes: comma-separated 3-digit HTTP status codes (also allow ffuf "all").
_MATCH_CODES_RE = re.compile(r"^(?:all|\d{3}(?:,\d{3})*)$")
# Strip userinfo (user:pass@) from a URL authority for safe echoing. Scheme-agnostic and
# scheme-optional so credentials are redacted even from a malformed/rejected target (e.g.
# "ftp://admin:pw@h" or a bare "admin:pw@h") — fail safe, never leak a secret into a fact.
_URL_USERINFO_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.\-]*://)?[^/@\s]+@")
# POST-body payload for api_fuzz_params: printable text, control chars other than
# tab/newline/CR rejected (mirrors the target/url control-char posture above).
_DATA_RE = re.compile(r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f]{1,8192}$")

_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_GRAPHQL_MAX_BODY_BYTES = 65536

# Lightweight (non-recursive) GraphQL introspection query — lists type/field names without
# the full recursive TypeRef fragments a client-schema-generation IntrospectionQuery needs.
# The full recursive form is deliberately avoided to keep the request minimal and bounded.
GRAPHQL_INTROSPECTION_QUERY = json.dumps(
    {
        "query": (
            "{ __schema { queryType { name } mutationType { name } "
            "subscriptionType { name } types { name kind fields { name } } } }"
        )
    }
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fact(trait: str, value: Any, confidence: int = 80) -> dict[str, Any]:
    return {"trait": trait, "value": value, "confidence": confidence}


def _facts(*items: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {"facts": list(items)}


def _redact_url(url: str) -> str:
    """Mask any credentials embedded in a URL (http://user:pass@host → http://***@host)
    before the value is echoed into a fact or log line."""
    return _URL_USERINFO_RE.sub(lambda m: (m.group(1) or "") + "***@", url)


def _error_facts(target: str, error: str) -> dict[str, list[dict[str, Any]]]:
    return _facts(
        _fact("scan.target", _redact_url(target), confidence=100),
        _fact("api_fuzz.status", f"error: {error}", confidence=100),
    )


def _params_error_facts(target: str, error: str) -> dict[str, list[dict[str, Any]]]:
    return _facts(
        _fact("scan.target", _redact_url(target), confidence=100),
        _fact("api_fuzz_params.status", f"error: {error}", confidence=100),
    )


def _graphql_error_facts(target: str, error: str) -> dict[str, list[dict[str, Any]]]:
    return _facts(
        _fact("scan.target", _redact_url(target), confidence=100),
        _fact("graphql_introspect.status", f"error: {error}", confidence=100),
    )


def _build_fuzz_url(target: str) -> str:
    """Ensure the target contains the FUZZ keyword; append it as a path segment if absent."""
    if "FUZZ" in target:
        return target
    if target.endswith("/"):
        return target + "FUZZ"
    return target + "/FUZZ"


async def _run_argv(argv: list[str], timeout: int) -> tuple[int | None, str]:
    """Run a command as an argv list (no shell). Returns (returncode, combined output).
    Never raises; on timeout returns (None, "timeout")."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return (127, f"{argv[0]} not found in container")
    except Exception as exc:  # noqa: BLE001
        return (1, f"failed to launch {argv[0]}: {exc}")

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (proc.returncode, (stdout + stderr).decode(errors="replace"))
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return (None, "timeout")


async def _run_ffuf_json(argv: list[str], out_path: str, timeout: int) -> tuple[int | None, str, str]:
    """Run ffuf via _run_argv, then read+cleanup the `-o <out_path>` JSON result file it wrote.
    Shared by api_fuzz and api_fuzz_params. Returns (returncode, combined_output, raw_json);
    raw_json is "" when ffuf did not produce (or finish writing) a result file — callers should
    treat output == "timeout" or rc == 127 as an early-exit case before looking at raw_json."""
    rc, output = await _run_argv(argv, timeout=timeout)

    if output == "timeout" or rc == 127:
        _cleanup(out_path)
        return rc, output, ""

    raw_json = ""
    try:
        if os.path.isfile(out_path):
            with open(out_path, "r", errors="replace") as fh:
                raw_json = fh.read()
    except OSError:
        raw_json = ""
    finally:
        _cleanup(out_path)

    return rc, output, raw_json


def _parse_ffuf_json(raw: str) -> list[dict]:
    """Parse an ffuf `-of json` result file into endpoint facts. Defensive against
    truncated / malformed output — returns whatever it can extract."""
    facts: list[dict] = []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return facts

    if not isinstance(data, dict):
        return facts

    results = data.get("results") or []
    if not isinstance(results, list):
        return facts

    count = 0
    for entry in results:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url", "")
        if not url:
            continue
        count += 1
        status = entry.get("status", "")
        length = entry.get("length", "")
        words = entry.get("words", "")
        redirect = entry.get("redirectlocation", "") or ""
        ctype = entry.get("content-type", "") or ""

        safe_url = _redact_url(str(url))
        facts.append(_fact("http.endpoint", safe_url, confidence=85))
        if status != "":
            facts.append(_fact("http.status", f"{safe_url} -> {status}", confidence=85))
        # Extra context traits (best-effort, capped values)
        if ctype:
            facts.append(_fact("http.content_type", f"{safe_url} -> {str(ctype)[:120]}", confidence=70))
        if redirect:
            facts.append(_fact("http.redirect", f"{safe_url} -> {_redact_url(str(redirect))[:512]}", confidence=75))
        if length != "" or words != "":
            facts.append(_fact("http.response_size", f"{safe_url} -> len={length} words={words}", confidence=60))

    facts.append(_fact("api_fuzz.status", f"{count} endpoint(s) discovered", confidence=100))
    return facts


def _parse_ffuf_params_json(raw: str) -> list[dict]:
    """Parse an ffuf `-of json` result file from a parameter-fuzzing run (api_fuzz_params) into
    facts keyed on the substituted FUZZ value rather than the (constant) target URL: `input.FUZZ`
    is used instead of `url` as the fact key because the URL is constant across a param-fuzz run."""
    facts: list[dict] = []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return facts

    if not isinstance(data, dict):
        return facts

    results = data.get("results") or []
    if not isinstance(results, list):
        return facts

    count = 0
    for entry in results:
        if not isinstance(entry, dict):
            continue
        fuzz_input = entry.get("input") or {}
        value = fuzz_input.get("FUZZ", "") if isinstance(fuzz_input, dict) else ""
        if value == "":
            continue
        count += 1
        status = entry.get("status", "")
        length = entry.get("length", "")
        words = entry.get("words", "")
        ctype = entry.get("content-type", "") or ""

        safe_value = _redact_url(str(value))[:256]
        facts.append(_fact("api_fuzz_params.hit", safe_value, confidence=85))
        if status != "":
            facts.append(_fact("http.status", f"{safe_value} -> {status}", confidence=85))
        if ctype:
            facts.append(_fact("http.content_type", f"{safe_value} -> {str(ctype)[:120]}", confidence=70))
        if length != "" or words != "":
            facts.append(_fact("http.response_size", f"{safe_value} -> len={length} words={words}", confidence=60))

    facts.append(_fact("api_fuzz_params.status", f"{count} hit(s) discovered", confidence=100))
    return facts


def _graphql_post_blocking(url: str, body: str, timeout: int) -> tuple[int | None, str]:
    """Blocking GraphQL POST via urllib. Runs inside asyncio.to_thread (see graphql_introspect).
    Never raises; returns (status_code_or_None, response_text_or_error_message)."""
    try:
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(_GRAPHQL_MAX_BODY_BYTES)
            return resp.status, raw.decode(errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(_GRAPHQL_MAX_BODY_BYTES)
            text = raw.decode(errors="replace")
        except Exception:  # noqa: BLE001
            text = str(exc)
        return exc.code, text
    except urllib.error.URLError as exc:
        return None, f"connection error: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return None, f"request failed: {exc}"


def _parse_graphql_introspection(raw: str) -> list[dict]:
    """Parse a GraphQL introspection response body into facts. Defensive against malformed /
    truncated JSON, missing __schema, non-list types, or a GraphQL `errors` array instead of
    `data`. Bounded to 200 type/field facts to avoid flooding the fact store on huge schemas."""
    facts: list[dict] = []
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return facts

    if not isinstance(payload, dict):
        return facts

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        for err in errors[:10]:
            msg = err.get("message", "") if isinstance(err, dict) else str(err)
            if msg:
                facts.append(_fact("graphql.error", _redact_url(str(msg))[:256], confidence=70))

    schema = (payload.get("data") or {}).get("__schema") if isinstance(payload.get("data"), dict) else None
    if not isinstance(schema, dict):
        return facts

    query_type = (schema.get("queryType") or {}).get("name") if isinstance(schema.get("queryType"), dict) else None
    mutation_type = (schema.get("mutationType") or {}).get("name") if isinstance(schema.get("mutationType"), dict) else None
    subscription_type = (
        (schema.get("subscriptionType") or {}).get("name") if isinstance(schema.get("subscriptionType"), dict) else None
    )
    if query_type:
        facts.append(_fact("graphql.query_type", str(query_type)[:256], confidence=90))
    if mutation_type:
        facts.append(_fact("graphql.mutation_type", str(mutation_type)[:256], confidence=90))
    if subscription_type:
        facts.append(_fact("graphql.subscription_type", str(subscription_type)[:256], confidence=90))

    types = schema.get("types") or []
    count = 0      # user-visible types discovered (excludes __ introspection types)
    emitted = 0    # graphql.type facts actually appended (bounded to avoid flooding)
    if isinstance(types, list):
        for t in types:
            if not isinstance(t, dict):
                continue
            name = str(t.get("name") or "")
            if not name or name.startswith("__"):
                continue
            count += 1
            if emitted >= 200:
                continue
            kind = t.get("kind", "")
            fields = t.get("fields") or []
            field_names = [str(f.get("name")) for f in fields if isinstance(f, dict) and f.get("name")] if isinstance(fields, list) else []
            value = f"{name} ({kind})" if kind else name
            if field_names:
                value += ": " + ", ".join(field_names[:20])
            facts.append(_fact("graphql.type", value[:512], confidence=75))
            emitted += 1

    if count > emitted:
        # do not silently drop: report the true total and how many were listed
        facts.append(_fact(
            "graphql_introspect.status",
            f"{count} type(s) discovered ({emitted} listed, truncated)",
            confidence=100,
        ))
    else:
        facts.append(_fact("graphql_introspect.status", f"{count} type(s) discovered", confidence=100))
    return facts


# ── tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def api_fuzz(
    target: str,
    wordlist: str = DEFAULT_WORDLIST,
    method: str = "GET",
    match_codes: str = "200,204,301,302,307,401,403",
) -> dict:
    """T1190,T1595.002 — Fuzz a target URL for hidden REST/GraphQL API endpoints via ffuf.

    Runs ffuf against the target, substituting each wordlist entry for the FUZZ keyword,
    and returns endpoints whose HTTP status matches `match_codes`. If the target does not
    contain the literal keyword `FUZZ`, `/FUZZ` is appended automatically.

    Args:
        target:      Base URL to fuzz (e.g. "http://target.example/" or "http://h/api/FUZZ").
                     Must be an http(s) URL. Any embedded credentials are redacted from output.
        wordlist:    Path to a wordlist file. Defaults to the bundled /app/wordlist.txt
                     (~40 common API paths).
        method:      HTTP method to use. One of GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH.
        match_codes: Comma-separated HTTP status codes to treat as a hit
                     (default "200,204,301,302,307,401,403"), or "all".

    Returns:
        {"facts": [{"trait": "http.endpoint", "value": "http://.../admin", "confidence": 85},
                   {"trait": "http.status", "value": "http://.../admin -> 200", ...},
                   {"trait": "technique.id", "value": "T1190", ...},
                   {"trait": "api_fuzz.status", "value": "3 endpoint(s) discovered", ...}]}
    """
    # ── validation ──────────────────────────────────────────────────────────
    tgt = target.strip()
    if not _URL_RE.match(tgt):
        return _error_facts(tgt, f"invalid target URL: {_redact_url(tgt)!r} (expected http(s)://...)")

    method_up = method.strip().upper()
    if method_up not in _METHOD_ALLOWLIST:
        return _error_facts(
            tgt, f"invalid method {method!r}; allowed: {', '.join(sorted(_METHOD_ALLOWLIST))}"
        )

    codes = match_codes.strip().replace(" ", "")
    if not _MATCH_CODES_RE.match(codes):
        return _error_facts(tgt, f"invalid match_codes {match_codes!r} (expected e.g. 200,301,403)")

    wl = wordlist.strip() or DEFAULT_WORDLIST
    if not os.path.isfile(wl):
        # Fall back to the bundled wordlist rather than failing outright.
        if os.path.isfile(DEFAULT_WORDLIST):
            wl = DEFAULT_WORDLIST
        else:
            return _error_facts(tgt, f"wordlist not found: {wl!r} (and no bundled default)")

    fuzz_url = _build_fuzz_url(tgt)

    # ── run ffuf ────────────────────────────────────────────────────────────
    out_fd, out_path = tempfile.mkstemp(prefix="ffuf_", suffix=".json")
    os.close(out_fd)

    # maxtime lets ffuf self-terminate a little before our hard wall-clock timeout.
    maxtime = max(10, DEFAULT_TIMEOUT - 15)
    argv = [
        FFUF_BIN,
        "-u", fuzz_url,
        "-w", wl,
        "-X", method_up,
        "-mc", codes,
        "-of", "json",
        "-o", out_path,
        "-s",
        "-t", FFUF_THREADS,
        "-timeout", FFUF_REQ_TIMEOUT,
        "-maxtime", str(maxtime),
    ]

    facts: list[dict] = [
        _fact("scan.target", _redact_url(fuzz_url), confidence=100),
        _fact("scan.tool", "ffuf", confidence=100),
    ]
    for tech in TECHNIQUES:
        facts.append(_fact("technique.id", tech, confidence=100))

    rc, output, raw_json = await _run_ffuf_json(argv, out_path, timeout=DEFAULT_TIMEOUT)

    if output == "timeout":
        facts.append(_fact("api_fuzz.status", f"ffuf timed out after {DEFAULT_TIMEOUT}s", confidence=100))
        return {"facts": facts}

    if rc == 127:
        facts.append(_fact("api_fuzz.status", "ffuf binary not available in container", confidence=100))
        return {"facts": facts}

    parsed = _parse_ffuf_json(raw_json)
    if parsed:
        facts.extend(parsed)
    else:
        # No structured results — surface a bounded, redacted diagnostic instead of raising.
        diag = _redact_url(output).strip()[:512] if output else "no results"
        facts.append(_fact("api_fuzz.status", "0 endpoint(s) discovered", confidence=100))
        if diag and diag != "no results":
            facts.append(_fact("api_fuzz.diagnostic", diag, confidence=40))

    return {"facts": facts}


@mcp.tool()
async def api_fuzz_params(
    target: str,
    data: str,
    wordlist: str = DEFAULT_WORDLIST,
    method: str = "POST",
    match_codes: str = "200,204,301,302,307,401,403",
) -> dict:
    """T1190,T1595.002 — Fuzz a POST-body/query-parameter value against a fixed endpoint via ffuf.

    Unlike api_fuzz (which fuzzes the URL path), this substitutes each wordlist entry for a
    single literal FUZZ keyword inside `data` (the request body), against a constant `target`
    URL. Useful for discovering hidden parameter values (IDs, roles, feature flags) on a known
    endpoint. Only a single FUZZ position is supported, to keep parsing and facts unambiguous.

    Args:
        target:      Fixed endpoint URL to send requests to (e.g. "http://target.example/api/login").
                     Must be an http(s) URL, must NOT itself contain "FUZZ". Any embedded
                     credentials are redacted from output.
        data:        POST body template containing the literal keyword FUZZ exactly once
                     (e.g. "user=admin&role=FUZZ"). Sent as
                     application/x-www-form-urlencoded.
        wordlist:    Path to a wordlist file. Defaults to the bundled /app/wordlist.txt.
        method:      HTTP method to use. One of GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH.
        match_codes: Comma-separated HTTP status codes to treat as a hit
                     (default "200,204,301,302,307,401,403"), or "all".

    Returns:
        {"facts": [{"trait": "api_fuzz_params.hit", "value": "admin", "confidence": 85},
                   {"trait": "http.status", "value": "admin -> 200", ...},
                   {"trait": "technique.id", "value": "T1190", ...},
                   {"trait": "api_fuzz_params.status", "value": "1 hit(s) discovered", ...}]}
    """
    # ── validation ──────────────────────────────────────────────────────────
    tgt = target.strip()
    if not _URL_RE.match(tgt):
        return _params_error_facts(tgt, f"invalid target URL: {_redact_url(tgt)!r} (expected http(s)://...)")

    if "FUZZ" in tgt:
        return _params_error_facts(
            tgt, "target must not itself contain FUZZ; put the FUZZ keyword in `data` instead"
        )

    body = data.strip()
    if not _DATA_RE.match(body):
        return _params_error_facts(tgt, "invalid data: must be 1-8192 printable chars with no control characters")

    if body.count("FUZZ") != 1:
        return _params_error_facts(tgt, "data must contain the literal keyword FUZZ exactly once")

    method_up = method.strip().upper()
    if method_up not in _METHOD_ALLOWLIST:
        return _params_error_facts(
            tgt, f"invalid method {method!r}; allowed: {', '.join(sorted(_METHOD_ALLOWLIST))}"
        )

    codes = match_codes.strip().replace(" ", "")
    if not _MATCH_CODES_RE.match(codes):
        return _params_error_facts(tgt, f"invalid match_codes {match_codes!r} (expected e.g. 200,301,403)")

    wl = wordlist.strip() or DEFAULT_WORDLIST
    if not os.path.isfile(wl):
        if os.path.isfile(DEFAULT_WORDLIST):
            wl = DEFAULT_WORDLIST
        else:
            return _params_error_facts(tgt, f"wordlist not found: {wl!r} (and no bundled default)")

    # ── run ffuf ────────────────────────────────────────────────────────────
    out_fd, out_path = tempfile.mkstemp(prefix="ffuf_", suffix=".json")
    os.close(out_fd)

    maxtime = max(10, DEFAULT_TIMEOUT - 15)
    argv = [
        FFUF_BIN,
        "-u", tgt,
        "-w", wl,
        "-X", method_up,
        "-d", body,
        "-H", f"Content-Type: {_FORM_CONTENT_TYPE}",
        "-mc", codes,
        "-of", "json",
        "-o", out_path,
        "-s",
        "-t", FFUF_THREADS,
        "-timeout", FFUF_REQ_TIMEOUT,
        "-maxtime", str(maxtime),
    ]

    facts: list[dict] = [
        _fact("scan.target", _redact_url(tgt), confidence=100),
        _fact("scan.tool", "ffuf", confidence=100),
    ]
    for tech in TECHNIQUES:
        facts.append(_fact("technique.id", tech, confidence=100))

    rc, output, raw_json = await _run_ffuf_json(argv, out_path, timeout=DEFAULT_TIMEOUT)

    if output == "timeout":
        facts.append(_fact("api_fuzz_params.status", f"ffuf timed out after {DEFAULT_TIMEOUT}s", confidence=100))
        return {"facts": facts}

    if rc == 127:
        facts.append(_fact("api_fuzz_params.status", "ffuf binary not available in container", confidence=100))
        return {"facts": facts}

    parsed = _parse_ffuf_params_json(raw_json)
    if parsed:
        facts.extend(parsed)
    else:
        diag = _redact_url(output).strip()[:512] if output else "no results"
        facts.append(_fact("api_fuzz_params.status", "0 hit(s) discovered", confidence=100))
        if diag and diag != "no results":
            facts.append(_fact("api_fuzz_params.diagnostic", diag, confidence=40))

    return {"facts": facts}


@mcp.tool()
async def graphql_introspect(target: str) -> dict:
    """T1190,T1595.002 — Run a GraphQL `__schema` introspection query against a target endpoint.

    Sends a single fixed, non-recursive introspection query as
    an HTTP POST and parses the response's queryType/mutationType/subscriptionType and type/field
    names into facts. Does not use ffuf or any subprocess — a direct stdlib urllib POST.

    Args:
        target: GraphQL endpoint URL (e.g. "http://target.example/graphql"). Must be an http(s) URL.
                Any embedded credentials are redacted from output.

    Returns:
        {"facts": [{"trait": "graphql.query_type", "value": "Query", "confidence": 90},
                   {"trait": "graphql.type", "value": "User (OBJECT): id, name, email", ...},
                   {"trait": "technique.id", "value": "T1190", ...},
                   {"trait": "graphql_introspect.status", "value": "12 type(s) discovered", ...}]}
    """
    tgt = target.strip()
    if not _URL_RE.match(tgt):
        return _graphql_error_facts(tgt, f"invalid target URL: {_redact_url(tgt)!r} (expected http(s)://...)")

    facts: list[dict] = [
        _fact("scan.target", _redact_url(tgt), confidence=100),
        _fact("scan.tool", "graphql-introspection", confidence=100),
    ]
    for tech in TECHNIQUES:
        facts.append(_fact("technique.id", tech, confidence=100))

    try:
        # urllib's per-socket timeout does not bound total read time against a slow-drip
        # target; an outer wall-clock deadline guarantees the OODA loop never hangs (the
        # worker thread may linger until its own socket timeout fires — accepted for T3).
        status, body = await asyncio.wait_for(
            asyncio.to_thread(_graphql_post_blocking, tgt, GRAPHQL_INTROSPECTION_QUERY, DEFAULT_TIMEOUT),
            timeout=DEFAULT_TIMEOUT + 15,
        )
    except asyncio.TimeoutError:
        facts.append(_fact("graphql_introspect.status", f"introspection timed out after {DEFAULT_TIMEOUT}s", confidence=100))
        return {"facts": facts}

    if status is None:
        # body is urllib's raw exception text, which can echo a user:pass@host target — redact.
        facts.append(_fact("graphql_introspect.status", f"error: {_redact_url(body)}", confidence=100))
        return {"facts": facts}

    facts.append(_fact("http.status", f"{_redact_url(tgt)} -> {status}", confidence=85))

    parsed = _parse_graphql_introspection(body)
    if parsed:
        facts.extend(parsed)
    else:
        diag = _redact_url(body).strip()[:512] if body else "no results"
        facts.append(_fact("graphql_introspect.status", "0 type(s) discovered", confidence=100))
        if diag and diag != "no results":
            facts.append(_fact("graphql_introspect.diagnostic", diag, confidence=40))

    return {"facts": facts}


def _cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    host = "0.0.0.0"
    port = 9105
    transport = "streamable-http"

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
        elif arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
        elif arg == "--transport" and i + 1 < len(args):
            transport = args[i + 1]

    mcp.run(transport=transport, host=host, port=port)

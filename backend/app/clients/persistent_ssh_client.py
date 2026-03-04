# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""PersistentSSHChannelEngine — SSH session pool for multi-step post-exploitation."""

import asyncio
import base64
import logging
from typing import Any
from uuid import uuid4

from app.clients import BaseEngineClient, ExecutionResult
from app.clients._ssh_common import (
    TECHNIQUE_EXECUTORS,
    _parse_credential,
    _parse_stdout_to_facts,
)

logger = logging.getLogger(__name__)

try:
    import asyncssh  # type: ignore[import]
except ImportError:  # pragma: no cover
    asyncssh = None  # type: ignore[assignment]

# Module-level session pool: (operation_id, credential_string) → asyncssh connection
# Using credential_string as key ensures different operations don't share sessions.
_SESSION_POOL: dict[tuple[str, str], Any] = {}

# Per-key locks to prevent TOCTOU races when two coroutines race to open the same connection.
_SESSION_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}


def _parse_key_credential(target: str) -> tuple[str, str, int, str]:
    """Parse 'user@host:port#<base64_private_key>' format.

    Returns (username, host, port, key_content).
    Raises ValueError if the format is invalid or base64 decoding fails.
    """
    try:
        conn_part, key_b64 = target.split("#", 1)
        key_content = base64.b64decode(key_b64).decode()
        user, hostport = conn_part.split("@", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 22
        return user, host, port, key_content
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc
    except Exception as exc:  # binascii.Error from b64decode
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc


class PersistentSSHChannelEngine(BaseEngineClient):
    """SSH engine that maintains persistent connections across technique executions.

    Unlike DirectSSHEngine (new connection per technique), this engine pools
    connections keyed by (operation_id, credential_string). Subsequent techniques
    on the same target reuse the existing connection.

    Use EXECUTION_ENGINE=persistent_ssh to enable.
    """

    def __init__(self, operation_id: str) -> None:
        self._operation_id = operation_id

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        """Execute a technique over a pooled SSH connection."""
        execution_id = str(uuid4())

        command = TECHNIQUE_EXECUTORS.get(ability_id)
        if not command:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=f"No SSH executor defined for technique {ability_id}",
            )

        if "@" not in target and ":" not in target:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=f"No SSH credentials in target string: {target}",
            )

        if "#" in target:
            # Key-based format: user@host:port#<b64key> — extract host for early validation
            conn_part, _ = target.split("#", 1)
            _, hostport = conn_part.split("@", 1)
            host = hostport.rsplit(":", 1)[0] if ":" in hostport else hostport
        else:
            _, _, host, _ = _parse_credential(target)
        if not host:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error="Could not parse host from credential string",
            )

        command = command.replace("{target_ip}", host)
        pool_key = (self._operation_id, target)

        try:
            if pool_key not in _SESSION_LOCKS:
                _SESSION_LOCKS[pool_key] = asyncio.Lock()
            lock = _SESSION_LOCKS[pool_key]

            async with lock:
                conn = _SESSION_POOL.get(pool_key)
                if conn is None:
                    if "#" in target:
                        user, host, port, key_content = _parse_key_credential(target)
                        conn = await asyncssh.connect(
                            host, port=port, username=user,
                            client_keys=[asyncssh.import_private_key(key_content)],
                            known_hosts=None,
                            connect_timeout=15,
                        )
                    else:
                        username, password, host, port = _parse_credential(target)
                        conn = await asyncssh.connect(
                            host, port=port, username=username, password=password,
                            known_hosts=None, connect_timeout=15,
                            keepalive_interval=30, keepalive_count_max=5,
                        )
                    _SESSION_POOL[pool_key] = conn
                    logger.info(
                        "PersistentSSH: new session for %s (pool size=%d)",
                        host, len(_SESSION_POOL),
                    )
                else:
                    logger.debug("PersistentSSH: reusing session for %s", host)

            # conn.run() is OUTSIDE the lock so other coroutines can use the pool concurrently.
            result = await conn.run(command, timeout=30)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            success = result.exit_status == 0

            facts = _parse_stdout_to_facts(ability_id, stdout, source="persistent_ssh", output_parser=output_parser)
            output = stdout if stdout else stderr

            logger.info(
                "PersistentSSH executed %s on %s → exit=%s",
                ability_id, host, result.exit_status,
            )
            return ExecutionResult(
                success=success,
                execution_id=execution_id,
                output=output[:2000],
                facts=facts,
                error=stderr[:500] if not success else None,
            )

        except Exception as exc:  # noqa: BLE001
            # Remove stale session so next call reconnects; close to free transport.
            stale_conn = _SESSION_POOL.pop(pool_key, None)
            if stale_conn is not None:
                try:
                    stale_conn.close()
                except Exception:  # noqa: BLE001
                    pass
            logger.warning("PersistentSSH execution failed for %s: %s", ability_id, exc)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=str(exc)[:500],
            )

    @staticmethod
    async def close_all_sessions(operation_id: str) -> None:
        """Close and remove all pooled sessions for a given operation_id."""
        keys_to_remove = [k for k in _SESSION_POOL if k[0] == operation_id]
        for key in keys_to_remove:
            conn = _SESSION_POOL.pop(key)
            _SESSION_LOCKS.pop(key, None)
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
        if keys_to_remove:
            logger.info(
                "PersistentSSH: closed %d sessions for op %s",
                len(keys_to_remove), operation_id,
            )

    async def get_status(self, execution_id: str) -> dict[str, Any]:
        """PersistentSSH executions are synchronous — always completed."""
        return {"execution_id": execution_id, "status": "completed"}

    async def list_abilities(self) -> list[dict[str, Any]]:
        return [
            {"ability_id": mid, "name": mid, "description": f"Persistent SSH: {mid}"}
            for mid in TECHNIQUE_EXECUTORS
        ]

    async def is_available(self) -> bool:
        return True

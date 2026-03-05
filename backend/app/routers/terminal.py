# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Interactive SSH terminal WebSocket endpoint for compromised targets."""

import asyncio
import json
import logging

import aiosqlite
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import _DB_FILE

logger = logging.getLogger(__name__)

router = APIRouter()

# Commands that could destroy the lab environment — refuse these
_CMD_BLACKLIST = ("rm -rf /", "mkfs", "dd if=/dev/zero", "> /dev/sda", "shred /dev")

MAX_CMD_LEN = 1024


def _is_dangerous(cmd: str) -> bool:
    lower = cmd.lower()
    return any(bad in lower for bad in _CMD_BLACKLIST)


@router.websocket("/ws/{operation_id}/targets/{target_id}/terminal")


async def ssh_terminal(
    operation_id: str,
    target_id: str,
    websocket: WebSocket,
):
    """Interactive SSH terminal for compromised targets.

    Client sends:  {"cmd": "whoami"}
    Server sends:  {"output": "msfadmin\\n", "exit_code": 0}
                or {"error": "..."}
    """
    await websocket.accept()

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        # Verify target exists and is compromised
        cursor = await db.execute(
            "SELECT id, hostname, ip_address, is_compromised FROM targets "
            "WHERE id = ? AND operation_id = ?",
            (target_id, operation_id),
        )
        target = await cursor.fetchone()
        if not target:
            await websocket.send_text(json.dumps({"error": "Target not found"}))
            await websocket.close()
            return

        if not target["is_compromised"]:
            await websocket.send_text(json.dumps({"error": "Target is not compromised"}))
            await websocket.close()
            return

        # Look up SSH credential from facts table
        cursor = await db.execute(
            "SELECT value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait = 'credential.ssh' "
            "ORDER BY collected_at DESC LIMIT 1",
            (operation_id, target_id),
        )
        cred_row = await cursor.fetchone()
        if not cred_row:
            await websocket.send_text(
                json.dumps({"error": "No SSH credential found for this target"})
            )
            await websocket.close()
            return

        cred_value = cred_row["value"]

        # Defence-in-depth: if the stored value doesn't look like a
        # credential (e.g. poisoned by command output), fall back to
        # a properly-formatted credential fact.
        if "@" not in cred_value or ":" not in cred_value.split("@")[0]:
            cursor = await db.execute(
                "SELECT value FROM facts "
                "WHERE operation_id = ? AND source_target_id = ? "
                "AND trait = 'credential.ssh' "
                "AND value LIKE '%:%@%:%' "
                "ORDER BY collected_at DESC LIMIT 1",
                (operation_id, target_id),
            )
            fallback_row = await cursor.fetchone()
            if fallback_row:
                cred_value = fallback_row["value"]
            else:
                await websocket.send_text(json.dumps({
                    "error": "No valid SSH credential found "
                    "(stored value does not match user:pass@host:port format)"
                }))
                await websocket.close()
                return

    # Parse credential: user:pass@host:port
    from app.clients._ssh_common import _parse_credential  # noqa: PLC0415

    try:
        user, password, host, port = _parse_credential(cred_value)
        if not host:
            host = target["ip_address"]
    except Exception as exc:
        await websocket.send_text(json.dumps({"error": f"Invalid credential: {exc}"}))
        await websocket.close()
        return

    # Establish SSH connection (retry up to 3 times with backoff)
    import asyncssh  # noqa: PLC0415

    _MAX_RETRIES = 3
    _RETRY_DELAYS = (1, 3, 5)
    conn = None
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            conn = await asyncssh.connect(
                host,
                port=port,
                username=user,
                password=password,
                known_hosts=None,
                connect_timeout=15,
            )
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "SSH terminal attempt %d/%d failed for %s@%s:%s: %s",
                attempt + 1, _MAX_RETRIES, user, host, port, exc,
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt])

    if conn is None:
        await websocket.send_text(json.dumps({
            "error": f"SSH connection failed after {_MAX_RETRIES} attempts: {last_error}"
        }))
        await websocket.close()
        return

    hostname = target["hostname"] or host
    await websocket.send_text(
        json.dumps({
            "output": f"Connected to {hostname} ({host}) as {user}\r\n",
            "exit_code": 0,
            "prompt": f"{user}@{hostname}:~$ ",
        })
    )

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue

            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({"error": "Command too long (max 1024 chars)"}))
                continue

            if _is_dangerous(cmd):
                await websocket.send_text(
                    json.dumps({"error": f"Command refused: potentially destructive operation"})
                )
                continue

            try:
                result = await conn.run(cmd, timeout=30)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                output = stdout if stdout else stderr
                exit_code = result.exit_status if result.exit_status is not None else 0
                await websocket.send_text(
                    json.dumps({
                        "output": output,
                        "exit_code": exit_code,
                        "prompt": f"{user}@{hostname}:~$ ",
                    })
                )
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": str(exc)}))

    except WebSocketDisconnect:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
        logger.info("Terminal session closed for target %s", target_id)

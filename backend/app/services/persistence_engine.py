# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""PersistenceEngine — 探測目標主機的 Linux 持久化向量。

支援技術：
  T1053.003 — Cron Job（探測 /etc/cron.d 寫入權限）
  T1543.002 — Systemd Service（探測 systemctl 可用性）

設計原則：graceful fallback — 任何失敗都不影響主流程。
PERSISTENCE_ENABLED=false（預設）時直接回傳 False，不建立 SSH 連線。
"""
import logging
import uuid
from datetime import datetime, timezone

import asyncpg

from app.clients._ssh_common import _parse_credential, _parse_key_credential
from app.config import settings

logger = logging.getLogger(__name__)

_PROBE_CRON = (
    "ls -la /etc/cron.d/ 2>/dev/null && "
    "touch /etc/cron.d/.athena_probe 2>/dev/null && "
    "rm -f /etc/cron.d/.athena_probe && echo CRON_WRITABLE || echo CRON_DENIED"
)
_PROBE_SYSTEMD = (
    "systemctl is-system-running 2>/dev/null; "
    "test -d /etc/systemd/system && echo SYSTEMD_AVAILABLE || echo SYSTEMD_UNAVAILABLE"
)


class PersistenceEngine:
    """探測目標主機的持久化向量，寫入 facts 表。"""

    async def probe(
        self,
        db_path: str,
        operation_id: str,
        target_id: str,
        credential_string: str,
    ) -> dict[str, bool]:
        """探測持久化可行性。PERSISTENCE_ENABLED=false 時直接回傳 False。"""
        if not settings.PERSISTENCE_ENABLED:
            return {"cron": False, "systemd": False}

        results: dict[str, bool] = {"cron": False, "systemd": False}

        try:
            import asyncssh  # noqa: PLC0415

            if "#" in credential_string:
                username, host, port, key_content = _parse_key_credential(credential_string)
                conn_kwargs: dict = {
                    "client_keys": [asyncssh.import_private_key(key_content)],
                }
            else:
                username, password, host, port = _parse_credential(credential_string)
                conn_kwargs = {"password": password}

            async with asyncssh.connect(
                host, port=port, username=username,
                known_hosts=None, connect_timeout=10,
                **conn_kwargs,
            ) as conn:
                cron_result = await conn.run(_PROBE_CRON, timeout=10)
                results["cron"] = "CRON_WRITABLE" in (cron_result.stdout or "")

                systemd_result = await conn.run(_PROBE_SYSTEMD, timeout=10)
                results["systemd"] = "SYSTEMD_AVAILABLE" in (systemd_result.stdout or "")

        except Exception as exc:
            logger.debug("PersistenceEngine probe failed for %s: %s", target_id, exc)
            return results

        now = datetime.now(timezone.utc)
        async with asyncpg.create_pool(db_path) as pool:
            async with pool.acquire() as db:
                for key, available in results.items():
                    if available:
                        await db.execute(
                            "INSERT INTO facts "
                            "(id, operation_id, source_target_id, trait, value, category, score, collected_at) "
                            "VALUES ($1, $2, $3, $4, $5, 'host', 1, $6) ON CONFLICT DO NOTHING",
                            str(uuid.uuid4()), operation_id, target_id, "host.persistence", key, now,
                        )
        return results

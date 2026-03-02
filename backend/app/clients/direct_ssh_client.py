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

"""DirectSSHEngine — executes MITRE ATT&CK techniques via SSH without requiring
a pre-deployed C2 agent. Implements BaseEngineClient interface."""

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


class DirectSSHEngine(BaseEngineClient):
    """Executes MITRE ATT&CK techniques directly over SSH.

    No pre-deployed agent required. Looks up SSH credentials from the facts
    table (credential.ssh trait) and executes the corresponding shell command.
    """

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
    ) -> ExecutionResult:
        """Execute a technique identified by MITRE ID over SSH.

        Args:
            ability_id: MITRE technique ID (e.g. "T1592") or internal ID
            target: SSH credential string "user:pass@host:port" OR just host
            params: optional extra params (currently unused)
        """
        execution_id = str(uuid4())

        # Look up command
        command = TECHNIQUE_EXECUTORS.get(ability_id)
        if not command:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=f"No SSH executor defined for technique {ability_id}",
            )

        # Parse credential / host
        if "@" in target or ":" in target:
            user, password, host, port = _parse_credential(target)
        else:
            # target is just a host, no credentials embedded
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=f"No SSH credentials in target string: {target}",
            )

        if not host:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error="Could not parse host from credential string",
            )

        # Replace placeholders
        command = command.replace("{target_ip}", host)

        try:
            import asyncssh  # noqa: PLC0415
            async with asyncssh.connect(
                host,
                port=port,
                username=user,
                password=password,
                known_hosts=None,
                connect_timeout=15,
            ) as conn:
                result = await conn.run(command, timeout=30)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                success = result.exit_status == 0

            facts = _parse_stdout_to_facts(ability_id, stdout)
            output = stdout if stdout else stderr

            logger.info(
                "DirectSSH executed %s on %s → exit=%s",
                ability_id,
                host,
                result.exit_status,
            )

            return ExecutionResult(
                success=success,
                execution_id=execution_id,
                output=output[:2000],
                facts=facts,
                error=stderr[:500] if not success else None,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("DirectSSH execution failed for %s: %s", ability_id, exc)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                output="",
                facts=[],
                error=str(exc)[:500],
            )

    async def get_status(self, execution_id: str) -> dict[str, Any]:
        """DirectSSH executions are synchronous — always completed."""
        return {"execution_id": execution_id, "status": "completed"}

    async def list_abilities(self) -> list[dict[str, Any]]:
        """Return list of supported MITRE technique IDs."""
        return [
            {"ability_id": mid, "name": mid, "description": f"SSH execution of {mid}"}
            for mid in TECHNIQUE_EXECUTORS
        ]

    async def is_available(self) -> bool:
        """DirectSSHEngine is always available (no external dependencies)."""
        return True

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

logger = logging.getLogger(__name__)

# MITRE ID → SSH command mapping (static fallback if DB is unavailable)
# Format: {target_ip} placeholder is replaced at runtime
TECHNIQUE_EXECUTORS: dict[str, str] = {
    "T1592": "uname -a && id && cat /etc/os-release",
    "T1046": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
    "T1059.004": "bash -c 'id && whoami && hostname'",
    "T1003.001": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
    "T1087": "cat /etc/passwd | cut -d: -f1,3,7",
    "T1083": "find / -name '*.conf' -readable 2>/dev/null | head -20",
    "T1190": "curl -sI http://localhost/ 2>/dev/null | head -5",
    "T1595.001": "echo 'NMAP_LOCAL_ONLY'",  # nmap runs locally, not via SSH
    "T1595.002": "echo 'NMAP_LOCAL_ONLY'",
    "T1021.004": "id && hostname",
    "T1078.001": "id && cat /etc/passwd | grep -v nologin | grep -v false",
    "T1110.001": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1110.003": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
}

# Map MITRE ID → expected fact traits
TECHNIQUE_FACT_TRAITS: dict[str, list[str]] = {
    "T1592": ["host.os", "host.user"],
    "T1046": ["service.open_port"],
    "T1059.004": ["host.process"],
    "T1003.001": ["credential.hash"],
    "T1087": ["host.user"],
    "T1083": ["host.file"],
    "T1190": ["service.web"],
    "T1595.001": ["network.host.ip"],
    "T1595.002": ["vuln.cve"],
    "T1021.004": ["host.session"],
    "T1078.001": ["credential.ssh"],
    "T1110.001": ["credential.ssh"],
    "T1110.003": ["credential.ssh"],
}


def _parse_credential(cred_value: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' or 'user:pass' format → (user, pass, host, port)."""
    host = ""
    port = 22
    if "@" in cred_value:
        user_pass, host_port = cred_value.rsplit("@", 1)
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            host = host_port
    else:
        user_pass = cred_value

    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
    else:
        user, password = user_pass, ""

    return user, password, host, port


def _parse_stdout_to_facts(mitre_id: str, stdout: str) -> list[dict[str, Any]]:
    """Extract facts from command stdout based on technique type."""
    facts = []
    traits = TECHNIQUE_FACT_TRAITS.get(mitre_id, [])

    for trait in traits:
        if not stdout.strip():
            continue
        # Generic: store first meaningful line of stdout as fact value
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if lines:
            facts.append({
                "trait": trait,
                "value": lines[0][:500],  # cap at 500 chars
                "score": 1,
                "source": "direct_ssh",
            })

    return facts


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

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

"""Mock Caldera client for development/demo without a real Caldera instance."""

import asyncio
import random
import uuid

from app.clients import BaseEngineClient, ExecutionResult

# Pre-recorded results keyed by MITRE technique ID
_MOCK_RESULTS: dict[str, ExecutionResult] = {
    "T1595.001": ExecutionResult(
        success=True,
        execution_id="",
        output="Active scan completed. Discovered 5 hosts on 10.0.1.0/24.",
        facts=[
            {"trait": "network.host.ip", "value": "10.0.1.5"},
            {"trait": "network.host.ip", "value": "10.0.1.20"},
            {"trait": "network.host.ip", "value": "10.0.1.21"},
            {"trait": "network.host.ip", "value": "10.0.1.30"},
            {"trait": "network.host.ip", "value": "10.0.1.40"},
        ],
    ),
    "T1003.001": ExecutionResult(
        success=True,
        execution_id="",
        output="LSASS memory dump successful. Extracted NTLM hashes.",
        facts=[
            {"trait": "credential.hash", "value": "Administrator:aad3b435b51404eeaad3b435b51404ee:..."},
            {"trait": "credential.hash", "value": "svc_sql:aad3b435b51404eeaad3b435b51404ee:..."},
        ],
    ),
    "T1021.002": ExecutionResult(
        success=True,
        execution_id="",
        output="SMB lateral movement to WS-PC01 via Admin$ share.",
        facts=[
            {"trait": "host.session", "value": "WS-PC01:Admin"},
        ],
    ),
    "T1059.001": ExecutionResult(
        success=True,
        execution_id="",
        output="PowerShell execution completed.",
        facts=[
            {"trait": "host.process", "value": "powershell.exe:pid=4312"},
        ],
    ),
}


class MockCalderaClient(BaseEngineClient):
    """Mock mode: returns pre-recorded results without calling real Caldera."""

    async def execute(
        self, ability_id: str, target: str, params: dict | None = None
    ) -> ExecutionResult:
        # Simulate 2-5 second execution delay
        await asyncio.sleep(random.uniform(2, 5))

        exec_id = str(uuid.uuid4())
        template = _MOCK_RESULTS.get(ability_id)
        if template:
            return ExecutionResult(
                success=template.success,
                execution_id=exec_id,
                output=template.output,
                facts=list(template.facts),
                error=template.error,
            )
        # Unknown technique — still succeed with empty facts
        return ExecutionResult(
            success=True,
            execution_id=exec_id,
            output=f"Mock execution of {ability_id} on {target} completed.",
            facts=[],
            error=None,
        )

    async def get_status(self, execution_id: str) -> str:
        return "finished"

    async def list_abilities(self) -> list[dict]:
        return [
            {"ability_id": k, "name": k, "tactic": "various"}
            for k in _MOCK_RESULTS
        ]

    async def is_available(self) -> bool:
        return True

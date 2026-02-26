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

"""MITRE Caldera REST API v2 client. License: Apache 2.0 (safe)."""

import asyncio
import logging
import uuid

import httpx

from app.clients import BaseEngineClient, ExecutionResult

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 2.0   # seconds between status checks
_POLL_TIMEOUT = 120.0   # max seconds to wait for completion
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
SUPPORTED_CALDERA_VERSIONS = ("4.", "5.")


class CalderaClient(BaseEngineClient):
    """HTTP client wrapping Caldera REST API v2."""

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["KEY"] = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=30.0
        )

    async def execute(
        self, ability_id: str, target: str, params: dict | None = None
    ) -> ExecutionResult:
        exec_id = str(uuid.uuid4())
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await self._execute_once(ability_id, target, exec_id, params)
            except httpx.HTTPError as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Caldera request failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, _MAX_RETRIES, e, delay,
                    )
                    await asyncio.sleep(delay)
        return ExecutionResult(
            success=False,
            execution_id=exec_id,
            output=None,
            facts=[],
            error=f"After {_MAX_RETRIES} retries: {last_error}",
        )

    async def _execute_once(
        self, ability_id: str, target: str, exec_id: str, params: dict | None = None
    ) -> ExecutionResult:
        # Create a Caldera operation with the specified ability
        payload = {
            "name": f"athena-{exec_id[:8]}",
            "adversary": {"adversary_id": "", "name": ""},
            "source": {"id": "basic", "name": ""},
            "planner": {"id": "atomic", "name": ""},
            "auto_close": True,
        }
        resp = await self._client.post("/api/v2/operations", json=payload)
        resp.raise_for_status()
        op_data = resp.json()
        op_id = op_data.get("id", exec_id)

        # Add ability to the operation
        ability_payload = {
            "paw": target,
            "ability_id": ability_id,
        }
        if params:
            ability_payload["facts"] = [
                {"trait": k, "value": v} for k, v in params.items()
            ]
        await self._client.post(
            f"/api/v2/operations/{op_id}/potential-links",
            json=ability_payload,
        )

        # Poll for completion with timeout
        status = await self._poll_status(op_id)

        # Get report
        report_resp = await self._client.post(
            f"/api/v2/operations/{op_id}/report",
            json={"enable_agent_output": True},
        )
        report = report_resp.json() if report_resp.status_code == 200 else {}

        facts = [
            {"trait": f.get("trait", ""), "value": f.get("value", "")}
            for f in report.get("facts", [])
        ]

        return ExecutionResult(
            success=status in ("finished", "cleanup"),
            execution_id=op_id,
            output=str(report.get("steps", {}))[:500],
            facts=facts,
            error=None if status in ("finished", "cleanup") else f"status={status}",
        )

    async def _poll_status(
        self, op_id: str,
        timeout: float = _POLL_TIMEOUT,
        interval: float = _POLL_INTERVAL,
    ) -> str:
        """Poll Caldera operation status until terminal state or timeout."""
        elapsed = 0.0
        while elapsed < timeout:
            status = await self.get_status(op_id)
            if status in ("finished", "cleanup", "failed"):
                return status
            await asyncio.sleep(interval)
            elapsed += interval
        return "timeout"

    async def get_status(self, execution_id: str) -> str:
        try:
            resp = await self._client.get(f"/api/v2/operations/{execution_id}")
            resp.raise_for_status()
            return resp.json().get("state", "unknown")
        except httpx.HTTPError:
            return "unknown"

    async def list_abilities(self) -> list[dict]:
        try:
            resp = await self._client.get("/api/v2/abilities")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return []

    async def is_available(self) -> bool:
        try:
            resp = await self._client.get("/api/v2/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def sync_agents(self, operation_id: str) -> list[dict]:
        """Fetch agents from Caldera and return normalized dicts."""
        try:
            resp = await self._client.get("/api/v2/agents")
            resp.raise_for_status()
            agents = resp.json()
            return [
                {
                    "paw": a.get("paw", ""),
                    "host": a.get("host", ""),
                    "platform": a.get("platform", ""),
                    "privilege": a.get("privilege", "User"),
                    "last_seen": a.get("last_seen", ""),
                    "status": "alive" if a.get("trusted", False) else "untrusted",
                }
                for a in agents
            ]
        except httpx.HTTPError:
            return []

    async def check_version(self) -> str:
        """Check Caldera version compatibility."""
        try:
            resp = await self._client.get("/api/v2/config/main")
            resp.raise_for_status()
            version = resp.json().get("version", "unknown")
            if not any(version.startswith(v) for v in SUPPORTED_CALDERA_VERSIONS):
                logger.warning(
                    "Caldera version %s is untested — supported prefixes: %s",
                    version, SUPPORTED_CALDERA_VERSIONS,
                )
            else:
                logger.info("Caldera version: %s", version)
            return version
        except httpx.HTTPError as e:
            logger.error("Failed to check Caldera version: %s", e)
            return "unknown"

    async def aclose(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

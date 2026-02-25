"""MITRE Caldera REST API v2 client. License: Apache 2.0 (safe)."""

import uuid

import httpx

from app.clients import BaseEngineClient, ExecutionResult


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
        try:
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

            # Poll for status
            status = await self.get_status(op_id)

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
                output=str(report.get("steps", {}))[: 500],
                facts=facts,
                error=None,
            )
        except httpx.HTTPError as e:
            return ExecutionResult(
                success=False,
                execution_id=exec_id,
                output=None,
                facts=[],
                error=str(e),
            )

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

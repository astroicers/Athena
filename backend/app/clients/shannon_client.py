"""Shannon AI engine REST API client. License: AGPL-3.0 — HTTP API only, no code imports."""

import uuid

import httpx

from app.clients import BaseEngineClient, ExecutionResult


class EngineNotAvailableError(Exception):
    """Raised when Shannon engine is not configured or unavailable."""


class ShannonClient(BaseEngineClient):
    """HTTP client for Shannon AI engine. AGPL-3.0 license isolation via API only."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.enabled = bool(self.base_url)
        self._client: httpx.AsyncClient | None = None
        if self.enabled:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

    async def execute(
        self, ability_id: str, target: str, params: dict | None = None
    ) -> ExecutionResult:
        if not self.enabled or not self._client:
            raise EngineNotAvailableError("Shannon engine is not configured")
        exec_id = str(uuid.uuid4())
        try:
            payload = {
                "task_id": exec_id,
                "description": ability_id,
                "target": target,
                "params": params or {},
            }
            resp = await self._client.post("/execute", json=payload)
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id", exec_id)

            # Poll status
            status = await self.get_status(task_id)
            return ExecutionResult(
                success=status == "completed",
                execution_id=task_id,
                output=data.get("output"),
                facts=data.get("facts", []),
                error=None if status == "completed" else f"status={status}",
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
        if not self.enabled or not self._client:
            return "unavailable"
        try:
            resp = await self._client.get(f"/status/{execution_id}")
            resp.raise_for_status()
            return resp.json().get("status", "unknown")
        except httpx.HTTPError:
            return "unknown"

    async def list_abilities(self) -> list[dict]:
        # Shannon does not use fixed abilities
        return []

    async def is_available(self) -> bool:
        if not self.enabled or not self._client:
            return False
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

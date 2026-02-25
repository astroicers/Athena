"""Execution engine client base classes and shared types."""

from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    success: bool
    execution_id: str
    output: str | None = None
    facts: list[dict] = field(default_factory=list)
    error: str | None = None


class BaseEngineClient:
    """Unified engine client interface."""

    async def execute(
        self, ability_id: str, target: str, params: dict | None = None
    ) -> ExecutionResult:
        raise NotImplementedError

    async def get_status(self, execution_id: str) -> str:
        raise NotImplementedError

    async def list_abilities(self) -> list[dict]:
        raise NotImplementedError

    async def is_available(self) -> bool:
        raise NotImplementedError

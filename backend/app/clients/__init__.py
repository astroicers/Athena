# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

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
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        raise NotImplementedError

    async def get_status(self, execution_id: str) -> str:
        raise NotImplementedError

    async def list_abilities(self) -> list[dict]:
        raise NotImplementedError

    async def is_available(self) -> bool:
        raise NotImplementedError

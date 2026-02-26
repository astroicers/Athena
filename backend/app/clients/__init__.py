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

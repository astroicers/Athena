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

"""Tool registry Pydantic models for CRUD operations."""
from __future__ import annotations

from pydantic import BaseModel


class ToolRegistryCreate(BaseModel):
    tool_id: str
    name: str
    description: str | None = None
    kind: str = "tool"
    category: str = "reconnaissance"
    version: str | None = None
    enabled: bool = True
    config_json: dict = {}
    mitre_techniques: list[str] = []
    risk_level: str = "low"
    output_traits: list[str] = []


class ToolRegistryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    version: str | None = None
    config_json: dict | None = None
    mitre_techniques: list[str] | None = None
    risk_level: str | None = None
    output_traits: list[str] | None = None


class ToolRegistryEntry(BaseModel):
    id: str
    tool_id: str
    name: str
    description: str | None
    kind: str
    category: str
    version: str | None
    enabled: bool
    source: str
    config_json: dict
    mitre_techniques: list[str]
    risk_level: str
    output_traits: list[str]
    created_at: str
    updated_at: str

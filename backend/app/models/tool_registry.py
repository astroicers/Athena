# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

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

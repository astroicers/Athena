# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Technique schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import KillChainStage, RiskLevel, TechniqueStatus


class TechniqueCreate(BaseModel):
    mitre_id: str
    name: str
    tactic: str
    tactic_id: str
    description: str | None = None
    kill_chain_stage: str = "exploit"
    risk_level: str = "medium"
    c2_ability_id: str | None = None
    platforms: list[str] = ["linux"]


class TechniqueWithStatus(BaseModel):
    id: str
    mitre_id: str
    name: str
    tactic: str
    tactic_id: str
    description: str | None = None
    kill_chain_stage: KillChainStage
    risk_level: RiskLevel
    c2_ability_id: str | None = None
    platforms: list[str] = []
    latest_status: TechniqueStatus | None = None
    latest_execution_id: str | None = None

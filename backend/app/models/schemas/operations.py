# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Operation schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.c5isr import C5ISRStatus
from app.models.enums import (
    AutomationMode,
    MissionProfile,
    OODAPhase,
    OperationStatus,
    RiskLevel,
)
from app.models.operation import Operation
from app.models.recommendation import OrientRecommendation


class OperationCreate(BaseModel):
    code: str
    name: str
    codename: str
    strategic_intent: str
    mission_profile: MissionProfile = MissionProfile.SP


class OperationUpdate(BaseModel):
    status: OperationStatus | None = None
    current_ooda_phase: OODAPhase | None = None
    threat_level: float | None = None
    success_rate: float | None = None
    techniques_executed: int | None = None
    techniques_total: int | None = None
    active_agents: int | None = None
    data_exfiltrated_bytes: int | None = None
    automation_mode: AutomationMode | None = None
    risk_threshold: RiskLevel | None = None
    mission_profile: MissionProfile | None = None


class OperationSummary(BaseModel):
    operation: Operation
    c5isr: list[C5ISRStatus]
    latest_recommendation: OrientRecommendation | None = None

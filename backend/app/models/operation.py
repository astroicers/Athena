# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

from datetime import datetime

from pydantic import BaseModel

from .enums import AutomationMode, MissionProfile, OODAPhase, OperationStatus, RiskLevel


class Operation(BaseModel):
    id: str
    code: str                           # "OP-2024-017"
    name: str                           # "Obtain Domain Admin"
    codename: str                       # "PHANTOM-EYE"
    strategic_intent: str
    status: OperationStatus
    current_ooda_phase: OODAPhase
    ooda_iteration_count: int = 0
    threat_level: float = 0.0           # 0.0 - 10.0
    success_rate: float = 0.0           # 0 - 100
    techniques_executed: int = 0
    techniques_total: int = 0
    active_agents: int = 0
    data_exfiltrated_bytes: int = 0
    max_iterations: int = 0  # 0 = unlimited
    automation_mode: AutomationMode = AutomationMode.SEMI_AUTO
    risk_threshold: RiskLevel = RiskLevel.MEDIUM
    mission_profile: MissionProfile = MissionProfile.SP
    operator_id: str | None = None
    created_at: datetime
    updated_at: datetime

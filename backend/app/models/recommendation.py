# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

from datetime import datetime

from pydantic import BaseModel

from .enums import ExecutionEngine, RiskLevel


class TacticalOption(BaseModel):
    technique_id: str
    technique_name: str
    reasoning: str
    risk_level: RiskLevel
    recommended_engine: ExecutionEngine
    confidence: float                   # 0.0 - 1.0
    prerequisites: list[str] = []


class OrientRecommendation(BaseModel):
    id: str
    operation_id: str
    ooda_iteration_id: str
    situation_assessment: str
    recommended_technique_id: str
    confidence: float
    options: list[TacticalOption]
    reasoning_text: str
    accepted: bool | None = None
    created_at: datetime

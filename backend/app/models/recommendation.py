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


class PentestGPTRecommendation(BaseModel):
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

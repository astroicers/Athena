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

from .enums import AutomationMode, OODAPhase, OperationStatus, RiskLevel


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
    automation_mode: AutomationMode = AutomationMode.SEMI_AUTO
    risk_threshold: RiskLevel = RiskLevel.MEDIUM
    operator_id: str | None = None
    created_at: datetime
    updated_at: datetime

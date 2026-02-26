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

"""
API-specific request/response schemas.

These complement the domain models in the sibling modules and are used
exclusively by the router layer for input validation and output shaping.
"""

from __future__ import annotations

from pydantic import BaseModel

from .c5isr import C5ISRStatus
from .enums import (
    AutomationMode,
    C5ISRDomainStatus,
    ExecutionEngine,
    KillChainStage,
    MissionStepStatus,
    OODAPhase,
    OperationStatus,
    RiskLevel,
    TechniqueStatus,
)
from .log_entry import LogEntry
from .operation import Operation
from .recommendation import PentestGPTRecommendation

# ---------------------------------------------------------------------------
# Operation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# C5ISR
# ---------------------------------------------------------------------------

class C5ISRUpdate(BaseModel):
    status: C5ISRDomainStatus | None = None
    health_pct: float | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# Operation
# ---------------------------------------------------------------------------

class OperationCreate(BaseModel):
    code: str
    name: str
    codename: str
    strategic_intent: str


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


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------

class MissionStepCreate(BaseModel):
    step_number: int
    technique_id: str
    technique_name: str
    target_id: str
    target_label: str
    engine: ExecutionEngine


class MissionStepUpdate(BaseModel):
    status: MissionStepStatus | None = None


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

class TopologyNode(BaseModel):
    id: str
    label: str
    type: str = "host"  # "host" | "agent"
    x: float | None = None
    y: float | None = None
    data: dict = {}


class TopologyEdge(BaseModel):
    source: str
    target: str
    label: str | None = None


class TopologyData(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]


# ---------------------------------------------------------------------------
# OODA
# ---------------------------------------------------------------------------

class OODATimelineEntry(BaseModel):
    iteration_number: int
    phase: str
    summary: str
    timestamp: str


# ---------------------------------------------------------------------------
# Technique
# ---------------------------------------------------------------------------

class TechniqueWithStatus(BaseModel):
    id: str
    mitre_id: str
    name: str
    tactic: str
    tactic_id: str
    description: str | None = None
    kill_chain_stage: KillChainStage
    risk_level: RiskLevel
    caldera_ability_id: str | None = None
    platforms: list[str] = []
    latest_status: TechniqueStatus | None = None
    latest_execution_id: str | None = None


# ---------------------------------------------------------------------------
# Logs (paginated)
# ---------------------------------------------------------------------------

class PaginatedLogs(BaseModel):
    items: list[LogEntry]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthStatus(BaseModel):
    status: str
    version: str
    services: dict


# ---------------------------------------------------------------------------
# Composite / Summary
# ---------------------------------------------------------------------------

class OperationSummary(BaseModel):
    operation: Operation
    c5isr: list[C5ISRStatus]
    latest_recommendation: PentestGPTRecommendation | None = None

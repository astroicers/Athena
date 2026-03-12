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
from typing import Literal

from pydantic import BaseModel, Field

from .enums import OODAPhase


class OODAIteration(BaseModel):
    id: str
    operation_id: str
    iteration_number: int
    phase: OODAPhase
    observe_summary: str | None = None
    orient_summary: str | None = None
    decide_summary: str | None = None
    act_summary: str | None = None
    recommendation_id: str | None = None
    technique_execution_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class OodaTriggerQueued(BaseModel):
    status: Literal["queued"] = "queued"
    operation_id: str


class OODADirectiveCreate(BaseModel):
    directive: str = Field(..., min_length=1, max_length=2000)
    scope: Literal["next_cycle"] = "next_cycle"


class OodaDashboardResponse(BaseModel):
    current_phase: str
    iteration_count: int
    latest_iteration: OODAIteration | None = None
    recent_iterations: list[OODAIteration] = []


class OODADirective(BaseModel):
    id: str
    operation_id: str
    directive: str
    scope: str
    created_at: datetime
    consumed_at: datetime | None = None

# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Mission and engagement schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import ExecutionEngine, MissionStepStatus


class MissionStepCreate(BaseModel):
    step_number: int
    technique_id: str
    technique_name: str
    target_id: str
    target_label: str
    engine: ExecutionEngine


class MissionStepUpdate(BaseModel):
    status: MissionStepStatus | None = None


class EngagementCreate(BaseModel):
    client_name: str
    contact_email: str
    in_scope: list[str]
    out_of_scope: list[str] = []
    start_time: str | None = None
    end_time: str | None = None
    emergency_contact: str | None = None

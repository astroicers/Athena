# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

from pydantic import BaseModel

from .enums import ExecutionEngine, MissionStepStatus


class MissionStep(BaseModel):
    id: str
    operation_id: str
    step_number: int
    technique_id: str
    technique_name: str
    target_id: str
    target_label: str
    engine: ExecutionEngine
    status: MissionStepStatus = MissionStepStatus.QUEUED

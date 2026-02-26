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

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

from .enums import ExecutionEngine, TechniqueStatus


class TechniqueExecution(BaseModel):
    id: str
    technique_id: str
    target_id: str
    operation_id: str
    ooda_iteration_id: str | None = None
    engine: ExecutionEngine
    status: TechniqueStatus
    result_summary: str | None = None
    facts_collected_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

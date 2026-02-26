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

from .enums import FactCategory


class Fact(BaseModel):
    id: str
    trait: str                          # "host.user.name"
    value: str                          # "CORP\\Administrator"
    category: FactCategory
    source_technique_id: str | None = None
    source_target_id: str | None = None
    operation_id: str
    score: int = 1
    collected_at: datetime

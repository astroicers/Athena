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

from pydantic import BaseModel

from .enums import C5ISRDomain, C5ISRDomainStatus


class C5ISRStatus(BaseModel):
    id: str
    operation_id: str
    domain: C5ISRDomain
    status: C5ISRDomainStatus
    health_pct: float                   # 0-100
    detail: str = ""

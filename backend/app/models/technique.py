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

from .enums import KillChainStage, RiskLevel


class Technique(BaseModel):
    id: str
    mitre_id: str                       # "T1003.001"
    name: str                           # "OS Credential Dumping: LSASS Memory"
    tactic: str                         # "Credential Access"
    tactic_id: str                      # "TA0006"
    description: str | None = None      # Technique description for UI display
    kill_chain_stage: KillChainStage
    risk_level: RiskLevel
    caldera_ability_id: str | None = None
    platforms: list[str] = []

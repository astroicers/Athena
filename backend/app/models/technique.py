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
    c2_ability_id: str | None = None
    platforms: list[str] = []

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

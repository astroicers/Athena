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

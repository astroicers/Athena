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

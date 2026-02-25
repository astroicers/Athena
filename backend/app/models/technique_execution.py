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

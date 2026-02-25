from datetime import datetime

from pydantic import BaseModel

from .enums import LogSeverity


class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    severity: LogSeverity
    source: str
    message: str
    operation_id: str | None = None
    technique_id: str | None = None

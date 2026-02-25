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
    score: int = 0
    collected_at: datetime

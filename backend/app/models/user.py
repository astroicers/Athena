from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: str
    callsign: str
    role: str = "Commander"
    created_at: datetime

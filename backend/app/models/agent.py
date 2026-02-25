from datetime import datetime

from pydantic import BaseModel

from .enums import AgentStatus


class Agent(BaseModel):
    id: str
    paw: str                            # "AGENT-7F3A"
    host_id: str                        # FK -> Target
    status: AgentStatus
    privilege: str                      # "SYSTEM"
    last_beacon: datetime | None = None
    beacon_interval_sec: int = 5
    platform: str                       # "windows"
    operation_id: str
